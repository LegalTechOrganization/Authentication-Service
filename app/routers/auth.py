from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    SignUpRequest, SignInRequest, RefreshTokenRequest, LogoutRequest,
    TokenResponse, ValidateResponse, ChangePasswordRequest
)
from app.keycloak_client import keycloak_client
from app.jwt_utils import jwt_utils
from app.models import User
from sqlalchemy import func
import uuid
from app.auth import get_current_user

router = APIRouter()


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, expires_in: int = 300):
    """Устанавливает HTTP-Only cookies для токенов"""
    # Access token cookie - короткое время жизни
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=expires_in,
        httponly=True,
        secure=False,  # False для разработки (HTTP), True для продакшена (HTTPS)
        samesite="lax",  # lax для разработки, strict для продакшена
        path="/"
    )
    
    # Refresh token cookie - длительное время жизни (7 дней)
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token,
        max_age=7 * 24 * 60 * 60,  # 7 дней в секундах
        httponly=True,
        secure=False,  # False для разработки (HTTP), True для продакшена (HTTPS)
        samesite="lax",  # lax для разработки, strict для продакшена
        path="/api/auth/refresh"
    )


def clear_auth_cookies(response: Response):
    """Очищает cookies аутентификации"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh")


@router.post("/sign-up", response_model=TokenResponse, status_code=201)
async def sign_up(
    request: SignUpRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Регистрация пользователя"""
    try:
        # Разбираем полное имя на first/last name для Keycloak
        first_name = ""
        last_name = ""
        if getattr(request, "full_name", None):
            name_parts = [p for p in request.full_name.strip().split(" ") if p]
            if name_parts:
                first_name = name_parts[0]
                if len(name_parts) > 1:
                    last_name = " ".join(name_parts[1:])

        # Пытаемся создать пользователя в Keycloak
        user_id = await keycloak_client.create_user(
            email=request.email,
            password=request.password,
            first_name=first_name,
            last_name=last_name
        )

        if not user_id:
            # если создать не получилось и не вернулся id — пробуем найти по email
            existing = await keycloak_client.find_user_by_email(request.email)
            if existing:
                user_id = existing.get("id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create or resolve user in Keycloak"
                )

        # Создать пользователя в локальной базе данных, если его нет
        local_user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not local_user:
            local_user = User(
                id=uuid.UUID(user_id),
                email=request.email,
                full_name=request.full_name
            )
            db.add(local_user)
            db.commit()
        else:
            if request.full_name and not local_user.full_name:
                local_user.full_name = request.full_name
                db.commit()

        # Получить токены через пароль
        token_data = await keycloak_client.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate user after creation"
            )
        
        # Устанавливаем cookies
        set_auth_cookies(
            response=response,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )

    except HTTPException:
        raise
    except Exception as e:
        # возвращаем текст исключения чтобы не было пустого detail
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Unknown error during sign-up"
        )


@router.post("/sign-in/password", response_model=TokenResponse)
async def sign_in(
    request: SignInRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Вход пользователя по паролю"""
    try:
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

        # Устанавливаем cookies
        set_auth_cookies(
            response=response,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )

        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/refresh_token", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest = None,
    response: Response = None
):
    """Обновление токена"""
    try:
        # Получаем refresh token из тела запроса или из cookie
        refresh_token = None
        if refresh_request and refresh_request.refresh_token:
            refresh_token = refresh_request.refresh_token
        else:
            refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )
        
        token_data = await keycloak_client.refresh_token(refresh_token)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Устанавливаем новые cookies
        set_auth_cookies(
            response=response,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )

        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 300)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid refresh token"
        )


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    logout_request: LogoutRequest = None,
    response: Response = None
):
    """Выход пользователя"""
    try:
        # Получаем refresh token из тела запроса или из cookie
        refresh_token = None
        if logout_request and logout_request.refresh_token:
            refresh_token = logout_request.refresh_token
        else:
            refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token provided"
            )
        
        success = await keycloak_client.revoke_refresh_token(refresh_token)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke token"
            )

        # Очищаем cookies
        clear_auth_cookies(response)

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Failed to logout"
        )


@router.post("/change-password", status_code=200)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сменить пароль пользователя"""
    try:
        # Проверяем старый пароль
        token_data = await keycloak_client.authenticate_user(
            email=current_user.email,
            password=request.old_password
        )
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid old password"
            )
        
        # Меняем пароль в Keycloak
        success = await keycloak_client.change_password(
            str(current_user.id),
            request.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) or "Failed to change password"
        )


@router.get("/validate", response_model=ValidateResponse)
async def validate_token(token: str):
    """Валидация JWT токена"""
    result = await jwt_utils.validate_token(token)
    return ValidateResponse(**result)


@router.get("/cookies")
async def check_cookies(request: Request):
    """Проверить cookies (для отладки)"""
    return {
        "access_token": request.cookies.get("access_token"),
        "refresh_token": request.cookies.get("refresh_token"),
        "all_cookies": dict(request.cookies)
    } 