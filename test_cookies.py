#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы HTTP-Only cookies
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_cookies():
    """Тестируем работу cookies"""
    
    # 1. Регистрация пользователя
    print("1. Регистрация пользователя...")
    signup_data = {
        "email": "test_cookies@example.com",
        "password": "test123"
    }
    
    response = requests.post(f"{BASE_URL}/v1/auth/sign-up", json=signup_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        print("✅ Регистрация успешна")
        print("Cookies в ответе:")
        for cookie in response.cookies:
            print(f"  {cookie.name}: {cookie.value[:20]}...")
        
        # Проверяем что токены есть и в JSON и в cookies
        json_data = response.json()
        print(f"JSON access_token: {json_data['access_token'][:20]}...")
        print(f"JSON refresh_token: {json_data['refresh_token'][:20]}...")
        
        # 2. Проверяем cookies
        print("\n2. Проверяем cookies...")
        cookies_response = requests.get(f"{BASE_URL}/v1/auth/cookies", cookies=response.cookies)
        print(f"Status: {cookies_response.status_code}")
        print(f"Cookies data: {cookies_response.json()}")
        
        # 3. Тестируем защищенный эндпоинт с cookies
        print("\n3. Тестируем защищенный эндпоинт с cookies...")
        me_response = requests.get(f"{BASE_URL}/v1/client/me", cookies=response.cookies)
        print(f"Status: {me_response.status_code}")
        if me_response.status_code == 200:
            print("✅ Защищенный эндпоинт работает с cookies")
            print(f"User data: {me_response.json()}")
        else:
            print(f"❌ Ошибка: {me_response.text}")
        
        # 4. Тестируем refresh token через cookies
        print("\n4. Тестируем refresh token через cookies...")
        refresh_response = requests.post(f"{BASE_URL}/v1/auth/refresh_token", cookies=response.cookies)
        print(f"Status: {refresh_response.status_code}")
        if refresh_response.status_code == 200:
            print("✅ Refresh token работает с cookies")
            print("Новые cookies:")
            for cookie in refresh_response.cookies:
                print(f"  {cookie.name}: {cookie.value[:20]}...")
        else:
            print(f"❌ Ошибка refresh: {refresh_response.text}")
        
        # 5. Тестируем logout через cookies
        print("\n5. Тестируем logout через cookies...")
        logout_response = requests.post(f"{BASE_URL}/v1/auth/logout", cookies=response.cookies)
        print(f"Status: {logout_response.status_code}")
        if logout_response.status_code == 204:
            print("✅ Logout работает с cookies")
            print("Cookies очищены")
        else:
            print(f"❌ Ошибка logout: {logout_response.text}")
            
    else:
        print(f"❌ Ошибка регистрации: {response.text}")

if __name__ == "__main__":
    test_cookies()
