from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    SignUpRequest, SignInRequest, RefreshTokenRequest, LogoutRequest,
    TokenResponse, ValidateResponse
)
from app.keycloak_client import keycloak_client
from app.jwt_utils import jwt_utils
from app.models import User
from sqlalchemy import func
import uuid

router = APIRouter()


@router.post("/sign-up", response_model=TokenResponse, status_code=201)
async def sign_up(
    request: SignUpRequest,
    db: Session = Depends(get_db)
):
    """Регистрация пользователя"""
    try:
        # Создать пользователя в Keycloak
        user_id = await keycloak_client.create_user(
            email=request.email,
            password=request.password
        )
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user in Keycloak"
            )
        
        # Создать пользователя в локальной базе данных
        user = User(
            id=uuid.UUID(user_id),
            email=request.email
        )
        db.add(user)
        db.commit()
        
        # Получить токены
        token_data = await keycloak_client.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/sign-in/password", response_model=TokenResponse)
async def sign_in(
    request: SignInRequest,
    db: Session = Depends(get_db)
):
    """Вход пользователя по паролю"""
    try:
        # Аутентификация через Keycloak
        token_data = await keycloak_client.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Обновить время последнего входа
        user = db.query(User).filter(User.email == request.email).first()
        if user:
            user.last_login_at = db.query(func.now()).scalar()
            db.commit()
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/refresh_token", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Обновление токена"""
    try:
        token_data = await keycloak_client.refresh_token(request.refresh_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout", status_code=204)
async def logout(request: LogoutRequest):
    """Выход пользователя"""
    try:
        success = await keycloak_client.revoke_refresh_token(request.refresh_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke token"
            )
        
        return None
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/validate", response_model=ValidateResponse)
async def validate_token(token: str):
    """Валидация JWT токена"""
    result = await jwt_utils.validate_token(token)
    return ValidateResponse(**result) 