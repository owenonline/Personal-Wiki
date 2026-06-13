import uuid


def new_id(prefix: str) -> str:
    """Return a short unique id like 'evt_3f9a1c2b8d4e'."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
