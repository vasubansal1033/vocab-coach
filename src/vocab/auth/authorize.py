"""Resource access checks for the personal (single-owner) phase."""

from typing import Protocol

from fastapi import HTTPException


class OwnedResource(Protocol):
    user_id: str


def authorize(user_id: str, action: str, resource: OwnedResource) -> None:
    """Allow only the owner; answer 404, not 403, so other users' IDs are not confirmed.

    `action` is unused today. It stays in the signature so route code does not
    need to change if cross-user roles are added later.
    """
    if resource.user_id != user_id:
        raise HTTPException(status_code=404, detail="Not found")
