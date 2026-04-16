import os


def load_api_key() -> str | None:
    if os.getenv("DEEPSEEK_API_KEY"):
        return os.getenv("DEEPSEEK_API_KEY")
    try:
        import keyring
        return keyring.get_password("mozhou", "deepseek_api_key")
    except Exception:
        return None


def save_api_key(key: str) -> None:
    try:
        import keyring
        keyring.set_password("mozhou", "deepseek_api_key", key)
    except Exception:
        pass
