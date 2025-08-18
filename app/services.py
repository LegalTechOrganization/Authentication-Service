from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import User, Organization, OrgMember, ActiveOrgContext
from app.keycloak_client import keycloak_client
from app.schemas import CreateOrgRequest, InviteRequest, AcceptInviteRequest, UpdateRoleRequest
from typing import List, Optional
import uuid
import secrets
import string
from datetime import datetime


class UserService:
    @staticmethod
    async def get_user_info(db: Session, user: User) -> dict:
        """Получить информацию о пользователе с организациями"""
        # Получить все организации пользователя
        memberships = db.query(OrgMember).filter(
            OrgMember.user_id == user.id
        ).all()
        
        orgs = []
        for membership in memberships:
            org = db.query(Organization).filter(
                Organization.id == membership.org_id,
                Organization.is_deleted == False
            ).first()
            if org:
                orgs.append({
                    "org_id": str(org.id),
                    "name": org.name,
                    "role": membership.role,
                    "is_owner": membership.is_owner
                })
        
        # Получить активную организацию
        active_context = db.query(ActiveOrgContext).filter(
            ActiveOrgContext.user_id == user.id
        ).first()
        
        active_org_id = str(active_context.org_id) if active_context else None
        
        return {
            "sub": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "orgs": orgs,
            "active_org_id": active_org_id
        }

    @staticmethod
    async def switch_organization(db: Session, user: User, org_id: str) -> dict:
        """Переключить активную организацию пользователя"""
        # Проверить, что пользователь является членом организации
        membership = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == user.id,
                OrgMember.org_id == uuid.UUID(org_id)
            )
        ).first()
        
        if not membership:
            raise ValueError("User is not a member of this organization")
        
        # Обновить или создать активный контекст
        active_context = db.query(ActiveOrgContext).filter(
            ActiveOrgContext.user_id == user.id
        ).first()
        
        if active_context:
            active_context.org_id = uuid.UUID(org_id)
        else:
            active_context = ActiveOrgContext(
                user_id=user.id,
                org_id=uuid.UUID(org_id)
            )
            db.add(active_context)
        
        db.commit()
        
        return {"active_org_id": org_id}


class OrganizationService:
    @staticmethod
    async def create_organization(db: Session, user: User, request: CreateOrgRequest) -> dict:
        """Создать новую организацию"""
        # Создать организацию
        org = Organization(
            name=request.name,
            slug=request.name.lower().replace(" ", "-")
        )
        db.add(org)
        db.flush()  # Получить ID организации
        
        # Добавить пользователя как владельца
        member = OrgMember(
            user_id=user.id,
            org_id=org.id,
            role="owner",
            is_owner=True
        )
        db.add(member)
        
        # Установить как активную организацию
        active_context = ActiveOrgContext(
            user_id=user.id,
            org_id=org.id
        )
        db.add(active_context)
        
        db.commit()
        
        return {"org_id": str(org.id)}

    @staticmethod
    async def get_organization_info(db: Session, org_id: str) -> dict:
        """Получить информацию об организации"""
        org = db.query(Organization).filter(
            and_(
                Organization.id == uuid.UUID(org_id),
                Organization.is_deleted == False
            )
        ).first()
        
        if not org:
            raise ValueError("Organization not found")
        
        # Найти владельца
        owner = db.query(OrgMember).filter(
            and_(
                OrgMember.org_id == org.id,
                OrgMember.is_owner == True
            )
        ).first()
        
        return {
            "org_id": str(org.id),
            "name": org.name,
            "owner_id": str(owner.user_id) if owner else None
        }

    @staticmethod
    async def get_organization_members(db: Session, org_id: str) -> List[dict]:
        """Получить список участников организации"""
        members = db.query(OrgMember).filter(
            OrgMember.org_id == uuid.UUID(org_id)
        ).all()
        
        result = []
        for member in members:
            user = db.query(User).filter(User.id == member.user_id).first()
            if user:
                result.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "role": member.role
                })
        
        return result

    @staticmethod
    async def invite_user(db: Session, user: User, org_id: str, request: InviteRequest) -> dict:
        """Пригласить пользователя в организацию"""
        # Проверить права пользователя
        membership = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == user.id,
                OrgMember.org_id == uuid.UUID(org_id)
            )
        ).first()
        
        if not membership or not membership.is_owner:
            raise ValueError("Insufficient permissions")
        
        # Проверить, что организация существует
        org = db.query(Organization).filter(
            and_(
                Organization.id == uuid.UUID(org_id),
                Organization.is_deleted == False
            )
        ).first()
        
        if not org:
            raise ValueError("Organization not found")
        
        # Генерировать токен приглашения
        invite_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        # В реальной системе здесь нужно сохранить токен в базе данных
        # с временем жизни и информацией о приглашении
        
        return {"invite_token": invite_token}

    @staticmethod
    async def accept_invite(db: Session, user: User, request: AcceptInviteRequest) -> dict:
        """Принять приглашение в организацию"""
        # В реальной системе здесь нужно проверить токен приглашения
        # и получить информацию об организации
        
        # Для демонстрации создадим простую логику
        # В реальности нужно валидировать токен и получать org_id из него
        
        # Проверить, что пользователь еще не является членом
        existing_membership = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == user.id,
                OrgMember.org_id == uuid.UUID("some-org-id")  # В реальности из токена
            )
        ).first()
        
        if existing_membership:
            raise ValueError("User is already a member of this organization")
        
        # Добавить пользователя в организацию
        member = OrgMember(
            user_id=user.id,
            org_id=uuid.UUID("some-org-id"),  # В реальности из токена
            role="member",
            is_owner=False
        )
        db.add(member)
        db.commit()
        
        return {
            "org_id": "some-org-id",
            "user_id": str(user.id),
            "role": "member"
        }

    @staticmethod
    async def remove_member(db: Session, user: User, org_id: str, user_id: str) -> bool:
        """Удалить участника из организации"""
        # Проверить права пользователя
        membership = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == user.id,
                OrgMember.org_id == uuid.UUID(org_id)
            )
        ).first()
        
        if not membership or not membership.is_owner:
            raise ValueError("Insufficient permissions")
        
        # Удалить участника
        member_to_remove = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == uuid.UUID(user_id),
                OrgMember.org_id == uuid.UUID(org_id)
            )
        ).first()
        
        if not member_to_remove:
            raise ValueError("Member not found")
        
        db.delete(member_to_remove)
        db.commit()
        
        return True

    @staticmethod
    async def update_member_role(db: Session, user: User, org_id: str, user_id: str, request: UpdateRoleRequest) -> dict:
        """Обновить роль участника"""
        # Проверить права пользователя
        membership = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == user.id,
                OrgMember.org_id == uuid.UUID(org_id)
            )
        ).first()
        
        if not membership or not membership.is_owner:
            raise ValueError("Insufficient permissions")
        
        # Обновить роль
        member = db.query(OrgMember).filter(
            and_(
                OrgMember.user_id == uuid.UUID(user_id),
                OrgMember.org_id == uuid.UUID(org_id)
            )
        ).first()
        
        if not member:
            raise ValueError("Member not found")
        
        member.role = request.role
        db.commit()
        
        return {
            "user_id": user_id,
            "role": request.role
        } 