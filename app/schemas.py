from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Auth schemas
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class ValidateResponse(BaseModel):
    valid: bool
    sub: Optional[str] = None
    exp: Optional[int] = None


# User schemas
class UserInfo(BaseModel):
    sub: str
    email: str
    full_name: Optional[str] = None
    orgs: List[dict]
    active_org_id: Optional[str] = None


class UpdateUserRequest(BaseModel):
    full_name: str


class SwitchOrgRequest(BaseModel):
    org_id: str


class SwitchOrgResponse(BaseModel):
    active_org_id: str


# Organization schemas
class CreateOrgRequest(BaseModel):
    name: str


class CreateOrgResponse(BaseModel):
    org_id: str


class InviteRequest(BaseModel):
    email: EmailStr


class InviteResponse(BaseModel):
    invite_token: str


class AcceptInviteRequest(BaseModel):
    invite_token: str


class AcceptInviteResponse(BaseModel):
    org_id: str
    user_id: str
    role: str


class MemberInfo(BaseModel):
    user_id: str
    email: str
    role: str


class UpdateRoleRequest(BaseModel):
    role: str


class UpdateRoleResponse(BaseModel):
    user_id: str
    role: str


class OrganizationInfo(BaseModel):
    org_id: str
    name: str
    owner_id: str


# Database models for responses
class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    is_deleted: bool
    user_metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: Optional[str] = None
    created_at: datetime
    is_deleted: bool
    org_metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class OrgMemberResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    role: str
    joined_at: datetime
    is_owner: bool

    class Config:
        from_attributes = True 