"""Returns the signed-in user's profile."""

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str | None]:
    return user.as_dict()
