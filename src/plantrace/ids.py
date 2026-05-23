import secrets


_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def new_node_id(prefix: str = "n") -> str:
    """Generate a stable, URL-safe PlanNode id like 'n_k3f8x2qj'."""
    body = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"{prefix}_{body}"


def new_plan_id() -> str:
    return new_node_id(prefix="p")
