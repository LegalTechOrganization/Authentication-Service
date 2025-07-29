from jose import jwt, JWTError
from typing import Optional, Dict, Any
from app.config import settings
from app.keycloak_client import keycloak_client
import time


class JWTUtils:
    def __init__(self):
        self.public_keys = None
        self.keys_last_updated = 0
        self.keys_cache_duration = 3600  # 1 час

    async def get_public_keys(self):
        """Получить публичные ключи с кэшированием"""
        current_time = time.time()
        
        if (self.public_keys is None or 
            current_time - self.keys_last_updated > self.keys_cache_duration):
            self.public_keys = await keycloak_client.get_public_keys()
            self.keys_last_updated = current_time
        
        return self.public_keys

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверить JWT токен"""
        try:
            # Получить публичные ключи
            keys = await self.get_public_keys()
            
            # Декодировать токен без проверки подписи для получения kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                return None
            
            # Найти соответствующий ключ
            key = None
            for k in keys.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                return None
            
            # Проверить токен
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.jwt_algorithm],
                audience=settings.keycloak_client_id,
                issuer=settings.jwt_issuer
            )
            
            return payload
            
        except JWTError:
            return None

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Валидировать токен и вернуть результат"""
        payload = await self.verify_token(token)
        
        if payload is None:
            return {
                "valid": False,
                "sub": None,
                "exp": None
            }
        
        return {
            "valid": True,
            "sub": payload.get("sub"),
            "exp": payload.get("exp")
        }

    def extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечь информацию о пользователе из JWT payload"""
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get("realm_access", {}).get("roles", [])
        }


jwt_utils = JWTUtils() 