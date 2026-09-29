"""Finding or creating the internal user for a validated OIDC identity."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import Identity, User


def get_or_create_user(
    session: Session,
    *,
    issuer: str,
    subject: str,
    display_name: str = "",
    email: str | None = None,
) -> User:
    """Return the user for `(issuer, subject)`, creating both rows on first login.

    Profile fields are only written at creation, so a later login never
    overwrites what the user may have changed here.
    """
    identity = session.scalar(
        select(Identity).where(Identity.issuer == issuer, Identity.subject == subject)
    )
    if identity is not None:
        user = session.get(User, identity.user_id)
        assert user is not None  # foreign key guarantees it
        return user

    user = User(display_name=display_name, email=email)
    session.add(user)
    session.flush()
    session.add(Identity(user_id=user.id, issuer=issuer, subject=subject))
    session.commit()
    return user
