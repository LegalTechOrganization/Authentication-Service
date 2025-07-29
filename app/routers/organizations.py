from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.schemas import (
    CreateOrgRequest, CreateOrgResponse, InviteRequest, InviteResponse,
    AcceptInviteRequest, AcceptInviteResponse, MemberInfo, UpdateRoleRequest,
    UpdateRoleResponse, OrganizationInfo
)
from app.services import OrganizationService
from app.models import User
from typing import List

router = APIRouter()


@router.post("", response_model=CreateOrgResponse)
async def create_organization(
    request: CreateOrgRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новую организацию"""
    try:
        result = await OrganizationService.create_organization(db, current_user, request)
        return CreateOrgResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{org_id}", response_model=OrganizationInfo)
async def get_organization_info(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить информацию об организации"""
    try:
        result = await OrganizationService.get_organization_info(db, org_id)
        return OrganizationInfo(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{org_id}/members", response_model=List[MemberInfo])
async def get_organization_members(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список участников организации"""
    try:
        result = await OrganizationService.get_organization_members(db, org_id)
        return [MemberInfo(**member) for member in result]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{org_id}/invite", response_model=InviteResponse)
async def invite_user(
    org_id: str,
    request: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Пригласить пользователя в организацию"""
    try:
        result = await OrganizationService.invite_user(db, current_user, org_id, request)
        return InviteResponse(**result)
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


@router.delete("/{org_id}/member/{user_id}", status_code=204)
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить участника из организации"""
    try:
        await OrganizationService.remove_member(db, current_user, org_id, user_id)
        return None
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


@router.patch("/{org_id}/member/{user_id}/role", response_model=UpdateRoleResponse)
async def update_member_role(
    org_id: str,
    user_id: str,
    request: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить роль участника"""
    try:
        result = await OrganizationService.update_member_role(db, current_user, org_id, user_id, request)
        return UpdateRoleResponse(**result)
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