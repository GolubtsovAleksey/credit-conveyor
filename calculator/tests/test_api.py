import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Создаёт тестовый HTTP-клиент FastAPI."""
    return TestClient(app)


@pytest.fixture
def valid_offer_payload() -> dict:
    """Возвращает валидный JSON-пейлоад для прескоринга."""
    return {
        "amount": 200000,
        "term": 12,
        "firstName": "Lexa",
        "lastName": "Golubtsov",
        "middleName": "Sergeevich",
        "email": "lexa@example.com",
        "birthdate": "1995-05-15",
        "passportSeries": "1234",
        "passportNumber": "567890",
    }


@pytest.fixture
def valid_scoring_payload(valid_offer_payload: dict) -> dict:
    """Возвращает валидный JSON-пейлоад для полного скоринга."""
    payload = valid_offer_payload.copy()
    payload.pop("email")
    payload["isInsuranceEnabled"] = True
    payload["isSalaryClient"] = False
    return payload


def test_health_check(client: TestClient):
    """Проверяет, что системный эндпоинт /health отвечает 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_offers_success(client: TestClient, valid_offer_payload: dict):
    """Проверяет успешный расчёт и параметры всех 4 кредитных предложений."""
    response = client.post("/calculator/offers", json=valid_offer_payload)

    assert response.status_code == 200
    offers = response.json()
    assert len(offers) == 4

    statement_ids = {offer["statementId"] for offer in offers}
    assert len(statement_ids) == 1

    expected_offers = [
        {
            "rate": "15.00",
            "totalAmount": "200000.00",
            "monthlyPayment": "18051.66",
            "isInsuranceEnabled": False,
            "isSalaryClient": False,
        },
        {
            "rate": "14.00",
            "totalAmount": "200000.00",
            "monthlyPayment": "17957.42",
            "isInsuranceEnabled": False,
            "isSalaryClient": True,
        },
        {
            "rate": "12.00",
            "totalAmount": "300000.00",
            "monthlyPayment": "26654.64",
            "isInsuranceEnabled": True,
            "isSalaryClient": False,
        },
        {
            "rate": "11.00",
            "totalAmount": "300000.00",
            "monthlyPayment": "26514.50",
            "isInsuranceEnabled": True,
            "isSalaryClient": True,
        },
    ]

    for actual, expected in zip(offers, expected_offers):
        assert actual["requestedAmount"] == "200000.00"
        assert actual["term"] == 12
        assert actual["rate"] == expected["rate"]
        assert actual["totalAmount"] == expected["totalAmount"]
        assert actual["monthlyPayment"] == expected["monthlyPayment"]
        assert actual["isInsuranceEnabled"] is expected["isInsuranceEnabled"]
        assert actual["isSalaryClient"] is expected["isSalaryClient"]


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("birthdate", "2015-05-15"),    # Клиент младше 18 лет
        ("amount", 100000),             # Сумма меньше минимальных 200 000
        ("term", 3),                    # Срок меньше минимальных 6 месяцев
        ("firstName", "Алексей"),       # Имя не на латинице
        ("lastName", "G"),              # Фамилия короче 2 символов
        ("email", "not-an-email"),      # Некорректный формат email
        ("passportSeries", "123"),      # Серия паспорта не из 4 цифр
        ("passportNumber", "abcdef"),   # Номер паспорта не из 6 цифр
    ],
)
def test_post_offers_validation_errors(
        client: TestClient,
        valid_offer_payload: dict,
        field_name: str,
        invalid_value: object,
):
    """Проверяет возврат ошибки 422 при невалидных входных полях."""
    payload = valid_offer_payload.copy()
    payload[field_name] = invalid_value

    response = client.post("/calculator/offers", json=payload)
    assert response.status_code == 422


def test_post_calc_success(client: TestClient, valid_scoring_payload: dict):
    """Проверяет успешный полный расчёт кредита и детали графика платежей."""
    response = client.post("/calculator/calc", json=valid_scoring_payload)

    assert response.status_code == 200
    data = response.json()

    assert data["amount"] == "300000.00"
    assert data["term"] == 12
    assert data["rate"] == "12.00"
    assert data["monthlyPayment"] == "26654.64"
    assert data["psk"] == "6.62"
    assert data["isInsuranceEnabled"] is True
    assert data["isSalaryClient"] is False

    schedule = data["paymentSchedule"]
    assert len(schedule) == 12
    assert schedule[0]["number"] == 1
    assert schedule[-1]["number"] == 12
    assert schedule[-1]["remainingDebt"] == "0.00"
    assert "interestPayment" in schedule[0]
    assert "debtPayment" in schedule[0]

