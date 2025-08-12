from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.schemas import UserInfo, SwitchOrgRequest, SwitchOrgResponse
from app.services import UserService
from app.models import User

router = APIRouter()


@router.get("/me", response_model=UserInfo)
async def get_user_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить информацию о текущем пользователе"""
    try:
        user_info = await UserService.get_user_info(db, current_user)
        return UserInfo(**user_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/switch-org", response_model=SwitchOrgResponse)
async def switch_organization(
    request: Request,
    switch_request: SwitchOrgRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Переключить активную организацию"""
    try:
        result = await UserService.switch_organization(db, current_user, switch_request.org_id)
        return SwitchOrgResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 