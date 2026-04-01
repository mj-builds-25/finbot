"""
Demo user accounts for FinBot.

Hardcoded for portfolio demonstration.
In production this would be a proper auth service
with hashed passwords and JWT refresh tokens.

Credentials shown in README and login screen.
"""

from dataclasses import dataclass


@dataclass
class DemoUser:
    email:      str
    password:   str
    role:       str
    name:       str
    department: str


DEMO_USERS: dict[str, DemoUser] = {
    "alice@finsolve.com": DemoUser(
        email="alice@finsolve.com",
        password="demo123",
        role="employee",
        name="Alice Johnson",
        department="Operations",
    ),
    "bob@finsolve.com": DemoUser(
        email="bob@finsolve.com",
        password="demo123",
        role="finance",
        name="Bob Mitchell",
        department="Finance",
    ),
    "carol@finsolve.com": DemoUser(
        email="carol@finsolve.com",
        password="demo123",
        role="engineering",
        name="Carol Stevens",
        department="Engineering",
    ),
    "dave@finsolve.com": DemoUser(
        email="dave@finsolve.com",
        password="demo123",
        role="marketing",
        name="Dave Anderson",
        department="Marketing",
    ),
    "eve@finsolve.com": DemoUser(
        email="eve@finsolve.com",
        password="demo123",
        role="c_level",
        name="Eve Martinez",
        department="Executive",
    ),
}


def authenticate(email: str, password: str) -> DemoUser | None:
    """
    Validate credentials and return the user if valid.
    Returns None if email not found or password wrong.
    """
    user = DEMO_USERS.get(email.lower().strip())
    if user and user.password == password:
        return user
    return None