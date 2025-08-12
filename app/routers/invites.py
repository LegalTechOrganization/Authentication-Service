from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.schemas import AcceptInviteRequest, AcceptInviteResponse
from app.services import OrganizationService
from app.models import User

router = APIRouter()


@router.post("/accept", response_model=AcceptInviteResponse)
async def accept_invite(
    request: Request,
    accept_request: AcceptInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Принять приглашение в организацию"""
    try:
        result = await OrganizationService.accept_invite(db, current_user, accept_request)
        return AcceptInviteResponse(**result)
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