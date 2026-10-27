"""
Demo users and per-user Ed25519 keys (B7).

Four demo users each own a distinct Ed25519 key pair derived from a seed, so
maker/checker signatures are genuinely different keys and maker == checker is
impossible to pass. A minimal password login backs the JWT (Keycloak optional).

Keys are seeded (deterministic) so the demo is reproducible offline; scripts/
keygen.py writes the public-key fingerprints for display.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.agents.crypto import AgentKeyPair


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    name: str
    role: str  # maker, checker, compliance, admin
    password: str
    key_seed: str


DEMO_USERS: dict[str, DemoUser] = {
    "maker": DemoUser("maker", "Rajesh Sharma", "maker", "maker-demo", "argus.user.maker"),
    "checker": DemoUser("checker", "Sunita Rao", "checker", "checker-demo", "argus.user.checker"),
    "compliance": DemoUser(
        "compliance", "Vikram Malhotra", "compliance", "compliance-demo", "argus.user.compliance"
    ),
    "admin": DemoUser("admin", "Anita Desai", "admin", "admin-demo", "argus.user.admin"),
}

# Cache one keypair per user so the same key is reused across a session.
_KEYPAIRS: dict[str, AgentKeyPair] = {}


def get_user(user_id: str) -> DemoUser | None:
    return DEMO_USERS.get(user_id)


def verify_login(user_id: str, password: str) -> DemoUser | None:
    user = DEMO_USERS.get(user_id)
    if user and password == user.password:
        return user
    return None


def user_keypair(user_id: str) -> AgentKeyPair:
    if user_id not in _KEYPAIRS:
        user = DEMO_USERS[user_id]
        _KEYPAIRS[user_id] = AgentKeyPair(seed=user.key_seed)
    return _KEYPAIRS[user_id]


def public_fingerprint(user_id: str) -> str:
    """Short, human-displayable fingerprint of the user's public key."""
    pk = user_keypair(user_id).public_key_hex
    return f"{pk[:8]}…{pk[-8:]}"
