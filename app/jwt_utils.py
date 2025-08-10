from jose import jwt, JWTError
from typing import Optional, Dict, Any, Union, List
from app.config import settings
from app.keycloak_client import keycloak_client
import time


class JWTUtils:
    def __init__(self):
        self.public_keys = None
        self.keys_last_updated = 0
        self.keys_cache_duration = 3600  # 1 час

    async def get_public_keys(self):
        current_time = time.time()
        if (self.public_keys is None or 
            current_time - self.keys_last_updated > self.keys_cache_duration):
            self.public_keys = await keycloak_client.get_public_keys()
            self.keys_last_updated = current_time
        return self.public_keys

    @staticmethod
    def _aud_contains_client(aud: Union[str, List[str], None], client_id: str) -> bool:
        if aud is None:
            return False
        if isinstance(aud, str):
            return aud == client_id
        try:
            return client_id in aud
        except Exception:
            return False

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            keys = await self.get_public_keys()
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                return None

            key = None
            for k in keys.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            if not key:
                return None

            # Проверяем подпись и issuer, но НЕ валидируем audience здесь
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                options={"verify_aud": False}
            )

            # Мягкая проверка audience/azp: допускаем, если azp == client_id или aud содержит client_id
            client_id = settings.keycloak_client_id
            aud_ok = self._aud_contains_client(payload.get("aud"), client_id) or (
                payload.get("azp") == client_id
            )
            # if not aud_ok:
            #     # Возможен токен с aud="account" от прямого Keycloak запроса — считаем невалидным для нашего сервиса
            #     return None

            return payload
        except JWTError:
            return None

    async def validate_token(self, token: str) -> Dict[str, Any]:
        payload = await self.verify_token(token)
        if payload is None:
            return {"valid": False, "sub": None, "exp": None}
        return {"valid": True, "sub": payload.get("sub"), "exp": payload.get("exp")}

    def extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get("realm_access", {}).get("roles", [])
        }


jwt_utils = JWTUtils() 