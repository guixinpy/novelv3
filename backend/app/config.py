import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_api_key() -> str | None:
    if os.getenv("DEEPSEEK_API_KEY"):
        return os.getenv("DEEPSEEK_API_KEY")
    try:
        import keyring
        key = keyring.get_password("mozhou", "deepseek_api_key")
        if key:
            return key
    except Exception:
        pass
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return None


def save_api_key(key: str) -> None:
    try:
        import keyring
        keyring.set_password("mozhou", "deepseek_api_key", key)
    except Exception:
        with open(PROJECT_ROOT / ".env", "w") as f:
            f.write(f"DEEPSEEK_API_KEY={key}\n")
