from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True)
    full_name = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)
    user_metadata = Column(JSON)

    # Relationships
    org_memberships = relationship("OrgMember", back_populates="user")
    active_org_context = relationship("ActiveOrgContext", back_populates="user", uselist=False)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)
    org_metadata = Column(JSON)

    # Relationships
    members = relationship("OrgMember", back_populates="organization")


class OrgMember(Base):
    __tablename__ = "org_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True)
    role = Column(Text, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_owner = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="org_memberships")
    organization = relationship("Organization", back_populates="members")


class ActiveOrgContext(Base):
    __tablename__ = "active_org_context"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="active_org_context")
    organization = relationship("Organization") 