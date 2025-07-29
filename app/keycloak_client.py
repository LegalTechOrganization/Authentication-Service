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
        """Получить токен администратора для работы с Admin API"""
        if self.admin_token:
            return self.admin_token

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
            response.raise_for_status()
            token_data = response.json()
            self.admin_token = token_data["access_token"]
            return self.admin_token

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        token = await self.get_admin_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Найти пользователя по email"""
        token = await self.get_admin_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/admin/realms/{self.realm}/users",
                params={"email": email, "exact": "true"},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            users = response.json()
            return users[0] if users else None

    async def create_user(self, email: str, password: str, first_name: str = "", last_name: str = "") -> str:
        """Создать пользователя в Keycloak"""
        token = await self.get_admin_token()
        
        user_data = {
            "email": email,
            "username": email,
            "enabled": True,
            "emailVerified": True,
            "firstName": first_name,
            "lastName": last_name,
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
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            
            # Получить ID созданного пользователя
            location = response.headers.get("location")
            if location:
                user_id = location.split("/")[-1]
                return user_id
            else:
                # Если location header не доступен, найдем пользователя по email
                user = await self.find_user_by_email(email)
                return user["id"] if user else None

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Отозвать refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/logout",
                data={"refresh_token": refresh_token}
            )
            return response.status_code == 204

    async def get_public_keys(self) -> Dict[str, Any]:
        """Получить публичные ключи для проверки JWT"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/realms/{self.realm}/.well-known/openid-configuration"
            )
            response.raise_for_status()
            config = response.json()
            
            jwks_response = await client.get(config["jwks_uri"])
            jwks_response.raise_for_status()
            return jwks_response.json()

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентификация пользователя через Keycloak"""
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
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Обновить токен"""
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
            response.raise_for_status()
            return response.json()


keycloak_client = KeycloakClient() 