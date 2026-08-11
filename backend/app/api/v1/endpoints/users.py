from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.user import UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me", response_model=UserResponse, summary="Update current user profile")
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.company_name is not None:
        current_user.company_name = data.company_name
    if data.role is not None:
        current_user.role = data.role

    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
