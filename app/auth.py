from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import User
from app.jwt_utils import jwt_utils
from app.keycloak_client import keycloak_client
import uuid

security = HTTPBearer(auto_error=False)  # Не вызываем ошибку если токена нет


def get_token_from_request(request: Request) -> Optional[str]:
    """Извлекает токен из заголовка Authorization или из cookie"""
    # Сначала пробуем из заголовка Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    
    # Если нет в заголовке, пробуем из cookie
    access_token = request.cookies.get("access_token")
    if access_token:
        return access_token
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Получить текущего пользователя из JWT токена (заголовок или cookie)"""
    # Получаем токен из заголовка или cookie
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = get_token_from_request(request)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid token provided"
        )
    
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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Получить текущего пользователя (опционально)"""
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None 