#!/usr/bin/env python3
"""
Generate and display per-user Ed25519 key fingerprints for the 4 demo users (B7).

Keys are deterministic (seeded) so the demo is reproducible offline. This script
prints each user's public-key fingerprint; the private keys live only in-process
(derived from the seed in services/auth/users.py).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth.users import DEMO_USERS, public_fingerprint, user_keypair  # noqa: E402


def main() -> None:
    out = {}
    for uid, user in DEMO_USERS.items():
        kp = user_keypair(uid)
        out[uid] = {
            "name": user.name,
            "role": user.role,
            "public_key": kp.public_key_hex,
            "fingerprint": public_fingerprint(uid),
        }
        print(f"{uid:12} {user.role:11} {public_fingerprint(uid)}  {user.name}")

    target = Path(__file__).resolve().parent.parent / "data" / "user_keys.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2))
    print(f"\nWrote public fingerprints to {target}")


if __name__ == "__main__":
    main()
