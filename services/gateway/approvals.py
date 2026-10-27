"""
Approvals router (B7) — JWT login + real per-user Ed25519 maker/checker signing.

/auth/login issues a short JWT for a demo user. /approvals/maker and
/approvals/checker sign the CURRENT bundle hash with the logged-in user's own key.
The Deployment Agent verifies BOTH signatures against the two public keys and
rejects: a single signature, maker == checker, or a bundle changed after signing.

There is no agent-key-as-human shortcut — each signature is the human user's key.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

from services.agents.crypto import AgentKeyPair
from services.auth.users import DEMO_USERS, public_fingerprint, user_keypair, verify_login
from services.config import get_settings

router = APIRouter(prefix="/api/v2", tags=["ARGUS v2 Approvals"])
settings = get_settings()

# In-memory approval state keyed by bundle hash: signatures collected so far.
# {bundle_hash: {"rule_name":..., "maker": {...}, "checker": {...}}}
_APPROVALS: dict[str, dict[str, Any]] = {}


def bundle_hash(rule_bundle: dict[str, Any]) -> str:
    """Canonical SHA-256 of the rule bundle — this is what gets signed."""
    serialized = json.dumps(rule_bundle, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


class LoginRequest(BaseModel):
    user_id: str
    password: str


class SignRequest(BaseModel):
    bundle_hash: str
    rule_name: str = "bundle"
    token: str  # JWT from /auth/login
    case_id: str | None = None  # scopes the approval to a specific case


def _decode(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


@router.post("/auth/login")
def login(req: LoginRequest) -> dict[str, Any]:
    user = verify_login(req.user_id, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = int(time.time())
    claims = {"sub": user.user_id, "role": user.role, "iat": now, "exp": now + 3600}
    token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {
        "token": token,
        "user_id": user.user_id,
        "name": user.name,
        "role": user.role,
        "public_key_fingerprint": public_fingerprint(user.user_id),
    }


@router.get("/auth/users")
def list_users() -> dict[str, Any]:
    return {
        "users": [
            {
                "user_id": u.user_id,
                "name": u.name,
                "role": u.role,
                "public_key_fingerprint": public_fingerprint(u.user_id),
            }
            for u in DEMO_USERS.values()
        ]
    }


def _approval_key(case_id: str | None, bundle_hash_val: str) -> str:
    return f"{case_id or '-'}::{bundle_hash_val}"


def _sign(role_expected: str, req: SignRequest) -> dict[str, Any]:
    claims = _decode(req.token)
    user_id = claims["sub"]
    kp: AgentKeyPair = user_keypair(user_id)
    # The user signs the exact bundle hash with their own private key.
    signature = kp.sign_payload({"bundle_hash": req.bundle_hash, "rule_name": req.rule_name})

    key = _approval_key(req.case_id, req.bundle_hash)
    record = _APPROVALS.setdefault(
        key, {"rule_name": req.rule_name, "maker": None, "checker": None}
    )
    slot = "maker" if role_expected == "maker" else "checker"
    record[slot] = {
        "user_id": user_id,
        "role": claims.get("role"),
        "public_key": kp.public_key_hex,
        "signature": signature,
        "fingerprint": public_fingerprint(user_id),
    }
    return {
        "signed": True,
        "slot": slot,
        "user_id": user_id,
        "fingerprint": public_fingerprint(user_id),
        "bundle_hash": req.bundle_hash,
        "both_signed": bool(record["maker"] and record["checker"]),
    }


@router.post("/approvals/maker")
def sign_maker(req: SignRequest) -> dict[str, Any]:
    return _sign("maker", req)


@router.post("/approvals/checker")
def sign_checker(req: SignRequest) -> dict[str, Any]:
    return _sign("checker", req)


@router.get("/approvals/{bundle_hash}")
def approval_status(bundle_hash: str, case_id: str | None = None) -> dict[str, Any]:
    rec = _APPROVALS.get(_approval_key(case_id, bundle_hash))
    if not rec:
        return {"bundle_hash": bundle_hash, "maker": None, "checker": None, "both_signed": False}
    return {
        "bundle_hash": bundle_hash,
        "maker": rec["maker"],
        "checker": rec["checker"],
        "both_signed": bool(rec["maker"] and rec["checker"]),
    }


def verify_dual_signatures(
    bundle_hash_val: str, rule_name: str, case_id: str | None = None
) -> tuple[bool, str]:
    """Verify both signatures against the two public keys. Enforces:
    both present, distinct users, and both valid over the exact bundle hash."""
    rec = _APPROVALS.get(_approval_key(case_id, bundle_hash_val))
    if not rec or not rec.get("maker") or not rec.get("checker"):
        return False, "Deployment requires BOTH maker and checker signatures."
    maker, checker = rec["maker"], rec["checker"]
    if maker["user_id"] == checker["user_id"]:
        return False, "Maker and checker must be two distinct users."
    payload = {"bundle_hash": bundle_hash_val, "rule_name": rule_name}
    if not AgentKeyPair.verify_signature(maker["public_key"], maker["signature"], payload):
        return False, "Maker signature invalid (bundle may have been tampered after signing)."
    if not AgentKeyPair.verify_signature(checker["public_key"], checker["signature"], payload):
        return False, "Checker signature invalid (bundle may have been tampered after signing)."
    return True, "Both signatures verified."
