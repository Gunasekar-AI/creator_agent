
DEMO_USERS = {
    "testuser": "Password123"
}


def authenticate_user(username: str, password: str) -> bool:
    """Validate the demo user's login credentials."""
    expected_password = DEMO_USERS.get(username)

    if expected_password is None:
        return False

    return expected_password == password
