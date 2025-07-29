# Authentication Service

Сервис аутентификации на основе FastAPI с интеграцией Keycloak для управления пользователями и организациями.

## Архитектура

Сервис построен на принципах:
- **Keycloak** - внешний Identity Provider для аутентификации
- **Локальная БД** - хранение организаций, участников и контекста
- **JWT токены** - для авторизации и валидации
- **REST API** - для взаимодействия с клиентами

## Установка и запуск

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/auth_service

# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=master
KEYCLOAK_CLIENT_ID=auth-service
KEYCLOAK_CLIENT_SECRET=your-client-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# JWT
JWT_ALGORITHM=RS256
JWT_ISSUER=http://localhost:8080/realms/master

# App
DEBUG=true
```

### 3. Настройка базы данных

```bash
# Создать миграцию
alembic revision --autogenerate -m "Initial migration"

# Применить миграции
alembic upgrade head
```

### 4. Запуск сервиса

```bash
python run.py
```

Сервис будет доступен по адресу: http://localhost:8000

## API Endpoints

### Аутентификация

#### POST `/v1/client/sign-up`
Регистрация нового пользователя
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### POST `/v1/client/sign-in/password`
Вход пользователя
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### POST `/v1/client/refresh_token`
Обновление токена
```json
{
  "refresh_token": "your-refresh-token"
}
```

#### POST `/v1/client/logout`
Выход пользователя
```json
{
  "refresh_token": "your-refresh-token"
}
```

#### GET `/v1/auth/validate`
Валидация JWT токена
```
?token=your-jwt-token
```

### Пользователи

#### GET `/v1/client/me`
Получить информацию о текущем пользователе

#### PATCH `/v1/client/switch-org`
Переключить активную организацию
```json
{
  "org_id": "org-uuid"
}
```

### Организации

#### POST `/v1/org`
Создать новую организацию
```json
{
  "name": "Organization Name"
}
```

#### GET `/v1/org/{org_id}`
Получить информацию об организации

#### GET `/v1/org/{org_id}/members`
Получить список участников организации

#### POST `/v1/org/{org_id}/invite`
Пригласить пользователя в организацию
```json
{
  "email": "user@example.com"
}
```

#### DELETE `/v1/org/{org_id}/member/{user_id}`
Удалить участника из организации

#### PATCH `/v1/org/{org_id}/member/{user_id}/role`
Обновить роль участника
```json
{
  "role": "admin"
}
```

### Приглашения

#### POST `/v1/invite/accept`
Принять приглашение в организацию
```json
{
  "invite_token": "invite-token"
}
```

## Структура базы данных

### Таблица `users`
- `id` (UUID) - уникальный идентификатор
- `email` (TEXT) - email пользователя
- `full_name` (TEXT) - полное имя
- `created_at` (TIMESTAMPTZ) - дата создания
- `last_login_at` (TIMESTAMPTZ) - последний вход
- `is_deleted` (BOOLEAN) - флаг удаления
- `metadata` (JSONB) - дополнительные данные

### Таблица `organizations`
- `id` (UUID) - уникальный идентификатор
- `name` (TEXT) - название организации
- `slug` (TEXT) - URL-friendly название
- `created_at` (TIMESTAMPTZ) - дата создания
- `is_deleted` (BOOLEAN) - флаг удаления
- `metadata` (JSONB) - дополнительные данные

### Таблица `org_members`
- `user_id` (UUID) - ID пользователя
- `org_id` (UUID) - ID организации
- `role` (TEXT) - роль в организации
- `joined_at` (TIMESTAMPTZ) - дата присоединения
- `is_owner` (BOOLEAN) - флаг владельца

### Таблица `active_org_context`
- `user_id` (UUID) - ID пользователя
- `org_id` (UUID) - ID активной организации

## Интеграция с Keycloak

Сервис использует Keycloak Admin API для:
- Создания пользователей
- Аутентификации
- Получения информации о пользователях
- Управления токенами

### Настройка Keycloak

1. Создайте realm для вашего приложения
2. Создайте client с типом "confidential"
3. Настройте client credentials
4. Убедитесь, что Admin API доступен

## Безопасность

- JWT токены подписываются с использованием RS256
- Публичные ключи получаются из Keycloak JWKS endpoint
- Токены проверяются на валидность подписи и срок действия
- Refresh токены могут быть отозваны

## Разработка

### Структура проекта

```
app/
├── __init__.py
├── main.py              # Основное приложение
├── config.py            # Конфигурация
├── database.py          # Настройка БД
├── models.py            # SQLAlchemy модели
├── schemas.py           # Pydantic схемы
├── auth.py              # Аутентификация
├── jwt_utils.py         # Работа с JWT
├── keycloak_client.py   # Клиент Keycloak
├── services.py          # Бизнес-логика
└── routers/             # API роутеры
    ├── __init__.py
    ├── auth.py
    ├── client.py
    ├── organizations.py
    └── invites.py
```

### Добавление новых эндпоинтов

1. Создайте схему в `schemas.py`
2. Добавьте бизнес-логику в `services.py`
3. Создайте роутер или добавьте в существующий
4. Подключите роутер в `main.py`

## Тестирование

```bash
# Запуск тестов (если есть)
pytest

# Проверка API документации
# Откройте http://localhost:8000/docs
```

## Деплой

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run.py"]
```

### Environment Variables

Убедитесь, что все необходимые переменные окружения настроены в продакшене:

- `DATABASE_URL` - строка подключения к PostgreSQL
- `KEYCLOAK_URL` - URL Keycloak сервера
- `KEYCLOAK_CLIENT_SECRET` - секрет клиента Keycloak
- `KEYCLOAK_ADMIN_PASSWORD` - пароль администратора Keycloak

## Мониторинг

- Health check endpoint: `/health`
- API документация: `/docs`
- Альтернативная документация: `/redoc` 