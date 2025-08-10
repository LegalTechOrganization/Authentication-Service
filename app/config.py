from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/auth_service"
    
    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "auth-service"
    keycloak_client_id: str = "auth-service"
    keycloak_client_secret: str = "GHvWOp4hXOLMNVmkdliARo6ydtIdywtJ"
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: str = "admin"
    
    # JWT
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "http://localhost:8080/realms/auth-service"
    
    # App
    app_name: str = "Authentication Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings() 