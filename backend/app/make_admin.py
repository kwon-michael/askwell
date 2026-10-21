"""Give a user moderator rights (or take them away).

    python -m app.make_admin <username>
    python -m app.make_admin <username> --revoke
"""

import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import User


def main(argv: list[str]) -> int:
    if len(argv) not in (1, 2) or (len(argv) == 2 and argv[1] != "--revoke"):
        print(__doc__.strip())
        return 2
    username, revoke = argv[0], len(argv) == 2

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            print(f"No user named {username!r}")
            return 1
        user.is_admin = not revoke
        db.commit()
    print(f"{username} is {'no longer' if revoke else 'now'} a moderator")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
