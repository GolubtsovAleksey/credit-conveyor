from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

# Создаём тестовый HTTP-клиент (аналог MockMvc в Spring)
"""встроенный тестовый HTTP-клиент (полный аналог MockMvc в Spring Boot). 
Он позволяет отправлять виртуальные POST и GET запросы в наше приложение прямо в памяти, 
без запуска реального сервера."""
client = TestClient(app)


def test_health_check():
    """Проверяет, что системный эндпоинт /health отвечает 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_offers_success():
    """Проверяет успешный запрос на получение 4 кредитных предложений."""
    payload = {
        "amount": 100000,
        "term": 12,
        "firstName": "Lexa",
        "lastName": "Golubtsov",
        "middleName": "Sergeevich",
        "email": "lexa@example.com",
        "birthdate": "1995-05-15",
        "passportSeries": "1234",
        "passportNumber": "567890",
    }

    response = client.post("/calculator/offers", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    # Проверяем, что поля в ответе вернулись в camelCase
    assert "monthlyPayment" in data[0]
    assert "totalAmount" in data[0]


def test_post_offers_validation_error_underage():
    """Проверяет, что клиенту младше 18 лет возвращается ошибка валидации 422."""
    payload = {
        "amount": 100000,
        "term": 12,
        "firstName": "Sanya",
        "lastName": "Golubtsov",
        "email": "sanya@example.com",
        "birthdate": "2015-05-15",  # Ребёнок (младше 18 лет)
        "passportSeries": "1234",
        "passportNumber": "567890",
    }

    response = client.post("/calculator/offers", json=payload)

    assert response.status_code == 422


def test_post_calc_success():
    """Проверяет успешный запрос на полный расчёт кредита и графика платежей."""
    payload = {
        "amount": 100000,
        "term": 12,
        "firstName": "Lexa",
        "lastName": "Golubtsov",
        "middleName": "Sergeevich",
        "birthdate": "1995-05-15",
        "passportSeries": "1234",
        "passportNumber": "567890",
        "isInsuranceEnabled": True,
        "isSalaryClient": False,
    }

    response = client.post("/calculator/calc", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["term"] == 12
    assert len(data["paymentSchedule"]) == 12
    assert "psk" in data

""" @patch декоратор из стандартной библиотеки unittest.mock (полный аналог @MockBean в Spring Boot). 
В одном из тестов мы подменяем реальный сервис заглушкой, чтобы убедиться, 
что контроллер действительно вызывает нужный метод сервиса"""
@patch("app.api.calculator.calculator_service.generate_offers")
def test_post_offers_calls_service_mock(mock_generate_offers):
    """Пример теста с моком (аналог @MockBean): проверяем, что контроллер вызывает сервис."""
    mock_generate_offers.return_value = []
    payload = {
        "amount": 100000,
        "term": 12,
        "firstName": "Ivan",
        "lastName": "Ivanov",
        "email": "ivan@example.com",
        "birthdate": "1995-05-15",
        "passportSeries": "1234",
        "passportNumber": "567890",
    }

    response = client.post("/calculator/offers", json=payload)

    assert response.status_code == 200
    assert response.json() == []
    # Проверяем, что метод сервиса был вызван ровно 1 раз
    mock_generate_offers.assert_called_once()
