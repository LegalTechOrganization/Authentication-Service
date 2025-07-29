from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import User
from app.jwt_utils import jwt_utils
from app.keycloak_client import keycloak_client
import uuid

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Получить текущего пользователя из JWT токена"""
    token = credentials.credentials
    
    # Проверить токен
    payload = await jwt_utils.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing sub"
        )
    
    # Найти пользователя в базе данных
    user = db.query(User).filter(
        User.id == uuid.UUID(user_id),
        User.is_deleted == False
    ).first()
    
    if not user:
        # Если пользователь не найден, попробуем создать его из Keycloak
        keycloak_user = await keycloak_client.get_user_by_id(user_id)
        if keycloak_user:
            user = User(
                id=uuid.UUID(user_id),
                email=keycloak_user.get("email"),
                full_name=f"{keycloak_user.get('firstName', '')} {keycloak_user.get('lastName', '')}".strip()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Получить текущего пользователя (опционально)"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None 