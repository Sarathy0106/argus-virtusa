"""
Bootstrap script for ARGUS environment configuration.
Generates cryptographically secure keys (Vault AES-256 key, Tokenizer salt, JWT secret, Ed25519 seed)
and creates a local .env file from deploy/env.example if not present.
"""

import secrets
from pathlib import Path


def generate_secure_hex(num_bytes: int = 32) -> str:
    return secrets.token_hex(num_bytes)


def generate_token_salt(length: int = 24) -> str:
    return secrets.token_urlsafe(length)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    env_example = repo_root / "deploy" / "env.example"
    env_target = repo_root / ".env"

    if env_target.exists():
        print(f"[INFO] .env file already exists at: {env_target}")
        return

    if not env_example.exists():
        raise FileNotFoundError(f"Template not found at: {env_example}")

    print("[INFO] Generating cryptographically secure keys for .env...")
    vault_key = generate_secure_hex(32)
    tokenizer_salt = generate_token_salt(32)
    jwt_secret = generate_secure_hex(32)
    agent_mesh_seed = generate_token_salt(32)

    content = env_example.read_text(encoding="utf-8")
    content = content.replace(
        "ARGUS_VAULT_ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        f"ARGUS_VAULT_ENCRYPTION_KEY={vault_key}",
    )
    content = content.replace(
        "ARGUS_TOKENIZER_SALT=argus-secure-session-salt-change-in-production",
        f"ARGUS_TOKENIZER_SALT={tokenizer_salt}",
    )
    content = content.replace(
        "JWT_SECRET_KEY=argus-super-secret-jwt-key-change-in-production",
        f"JWT_SECRET_KEY={jwt_secret}",
    )
    content = content.replace(
        "AGENT_MESH_SIGNING_SEED=argus-agent-mesh-ed25519-seed-phrase",
        f"AGENT_MESH_SIGNING_SEED={agent_mesh_seed}",
    )

    env_target.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] Created {env_target} with fresh cryptographic credentials.")


if __name__ == "__main__":
    main()
