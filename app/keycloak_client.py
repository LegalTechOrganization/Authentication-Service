import httpx
from typing import Optional, Dict, Any
from app.config import settings
import json


class KeycloakClient:
    def __init__(self):
        self.base_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self.admin_token = None

    async def get_admin_token(self) -> str:
        """Получить НОВЫЙ токен администратора для работы с Admin API (без долгого кэша)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                }
            )
            if response.status_code != 200:
                raise ValueError(
                    f"Keycloak admin token error {response.status_code}: {response.text}"
                )
            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("Keycloak admin token missing in response")
            # не кэшируем надолго: всегда возвращаем свежий
            self.admin_token = access_token
            return access_token

    async def _authorized_headers(self) -> Dict[str, str]:
        token = await self.get_admin_token()
        return {"Authorization": f"Bearer {token}"}

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID (c авто-переполучением admin токена при 401)."""
        headers = await self._authorized_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                headers=headers
            )
            if response.status_code == 401:
                # повторим один раз с новым токеном
                headers = await self._authorized_headers()
                response = await client.get(
                    f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                    headers=headers
                )
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise ValueError(
                    f"Keycloak get user error {response.status_code}: {response.text}"
                )
            return response.json()

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Найти пользователя по email (c авто-переполучением admin токена при 401)."""
        headers = await self._authorized_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/admin/realms/{self.realm}/users",
                params={"email": email, "exact": "true"},
                headers=headers
            )
            if response.status_code == 401:
                headers = await self._authorized_headers()
                response = await client.get(
                    f"{self.base_url}/admin/realms/{self.realm}/users",
                    params={"email": email, "exact": "true"},
                    headers=headers
                )
            if response.status_code != 200:
                raise ValueError(
                    f"Keycloak find user error {response.status_code}: {response.text}"
                )
            users = response.json()
            return users[0] if users else None

    async def update_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        headers = await self._authorized_headers()
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                json=payload,
                headers=headers
            )
            if response.status_code == 401:
                headers = await self._authorized_headers()
                response = await client.put(
                    f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                    json=payload,
                    headers=headers
                )
            if response.status_code not in (204, 200):
                raise ValueError(
                    f"Keycloak update user error {response.status_code}: {response.text}"
                )

    @staticmethod
    def _default_names_from_email(email: str) -> Dict[str, str]:
        local = (email or "user").split("@")[0]
        parts = [p for p in local.replace("_", " ").replace("-", " ").split(" ") if p]
        first = parts[0].capitalize() if parts else "User"
        last = (parts[1].capitalize() if len(parts) > 1 else "Account")
        return {"firstName": first, "lastName": last}

    async def ensure_user_profile_by_email(self, email: str) -> None:
        user = await self.find_user_by_email(email)
        if not user:
            return
        first = user.get("firstName") or ""
        last = user.get("lastName") or ""
        if not first or not last or user.get("requiredActions"):
            names = self._default_names_from_email(email)
            payload = {
                "id": user.get("id"),
                "email": user.get("email") or email,
                "username": user.get("username") or email,
                "enabled": True,
                "emailVerified": True,
                "firstName": names["firstName"] if not first else first,
                "lastName": names["lastName"] if not last else last,
                "requiredActions": []
            }
            await self.update_user(user.get("id"), payload)

    async def create_user(self, email: str, password: str, first_name: str = "", last_name: str = "") -> Optional[str]:
        """Создать пользователя в Keycloak (c авто-переполучением admin токена при 401)."""
        headers = await self._authorized_headers()
        if not first_name or not last_name:
            names = self._default_names_from_email(email)
            first_name = first_name or names["firstName"]
            last_name = last_name or names["lastName"]
        user_data = {
            "email": email,
            "username": email,
            "enabled": True,
            "emailVerified": True,
            "firstName": first_name,
            "lastName": last_name,
            "requiredActions": [],
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": False
                }
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/admin/realms/{self.realm}/users",
                json=user_data,
                headers=headers
            )
            if response.status_code == 401:
                headers = await self._authorized_headers()
                response = await client.post(
                    f"{self.base_url}/admin/realms/{self.realm}/users",
                    json=user_data,
                    headers=headers
                )
            if response.status_code == 201:
                location = response.headers.get("location")
                if location:
                    return location.split("/")[-1]
                user = await self.find_user_by_email(email)
                return user["id"] if user else None
            if response.status_code == 409:
                existing = await self.find_user_by_email(email)
                if existing:
                    return existing.get("id")
                raise ValueError("Keycloak: user already exists but cannot be fetched")
            raise ValueError(
                f"Keycloak create user error {response.status_code}: {response.text}"
            )

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/logout",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                }
            )
            # В разных версиях Keycloak возвращается 204 или 200
            return response.status_code in (200, 204)

    async def get_public_keys(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/realms/{self.realm}/.well-known/openid-configuration"
            )
            if response.status_code != 200:
                raise ValueError(
                    f"Keycloak OIDC config error {response.status_code}: {response.text}"
                )
            config = response.json()
            jwks_response = await client.get(config["jwks_uri"])
            if jwks_response.status_code != 200:
                raise ValueError(
                    f"Keycloak JWKS error {jwks_response.status_code}: {jwks_response.text}"
                )
            return jwks_response.json()

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": email,
                    "password": password,
                }
            )
            if response.status_code == 401:
                return None
            if response.status_code == 400:
                # пробросим текст для диагностики (например, Account is not fully set up)
                raise ValueError(response.text)
            if response.status_code != 200:
                raise ValueError(
                    f"Keycloak token error {response.status_code}: {response.text}"
                )
            return response.json()

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                }
            )
            if response.status_code == 401:
                return None
            if response.status_code != 200:
                raise ValueError(
                    f"Keycloak refresh error {response.status_code}: {response.text}"
                )
            return response.json()


keycloak_client = KeycloakClient() 