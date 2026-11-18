from datetime import date
from decimal import Decimal

from app.schemas.calculator import LoanStatementRequestDto, ScoringDataDto
from app.services.calculator_service import CalculatorService, add_months


def create_service() -> CalculatorService:
    """Создаёт сервис с фиксированными настройками для теста."""
    return CalculatorService(
        base_rate=Decimal("15.0"),
        insurance_cost=Decimal("100000"),
    )


def create_valid_request() -> LoanStatementRequestDto:
    """Создаёт тестовую заявку на кредит с валидными данными."""
    return LoanStatementRequestDto(
        amount=Decimal("100000"),
        term=12,
        first_name="Lexa",
        last_name="Golubtsov",
        middle_name="Sergeevich",
        email="lexa@example.com",
        birthdate=date(1995, 5, 15),
        passport_series="1234",
        passport_number="567890",
    )


def test_add_months_handles_end_of_month():
    """Проверяет переход с 31 января на последний день февраля
    проверка, что функция дат не сломается, если взять кредит 31 января"""
    january_end = date(2026, 1, 31)
    result = add_months(january_end, 1)
    assert result == date(2026, 2, 28)


def test_calculate_rate_combinations():
    """Проверяет расчёт процентной ставки для всех комбинаций опций."""
    service = create_service()

    assert service.calculate_rate(is_insurance_enabled=False, is_salary_client=False) == Decimal("15.00")
    assert service.calculate_rate(is_insurance_enabled=False, is_salary_client=True) == Decimal("14.00")
    assert service.calculate_rate(is_insurance_enabled=True, is_salary_client=False) == Decimal("12.00")
    assert service.calculate_rate(is_insurance_enabled=True, is_salary_client=True) == Decimal("11.00")


def test_calculate_total_amount():
    """Проверяет добавление стоимости страховки к сумме кредита."""
    service = create_service()

    assert service.calculate_total_amount(Decimal("100000"), is_insurance_enabled=False) == Decimal("100000.00")
    assert service.calculate_total_amount(Decimal("100000"), is_insurance_enabled=True) == Decimal("200000.00")


def test_generate_offers_returns_4_sorted_offers():
    """Проверяет, что создаётся 4 предложения и они отсортированы от худшего к лучшему."""
    service = create_service()
    request = create_valid_request()

    offers = service.generate_offers(request)

    # len(offers) — встроенная функция, которая возвращает длину списка (полный аналог offers.size() в Java)
    assert len(offers) == 4
    # Ставки должны идти по убыванию: 15% -> 14% -> 12% -> 11%
    assert offers[0].rate == Decimal("15.00")
    assert offers[1].rate == Decimal("14.00")
    assert offers[2].rate == Decimal("12.00")
    assert offers[3].rate == Decimal("11.00")


def test_calculate_credit_full_schedule():
    """Проверяет полный расчёт кредита, ПСК и обнуление долга в конце графика
    проверяет главный сценарий: что график содержит ровно 12 платежей и после 12-го платежа остаток долга (remaining_debt) стал равен строго 0.00"""
    service = create_service()
    scoring_data = ScoringDataDto(
        amount=Decimal("100000"),
        term=12,
        first_name="lexa",
        last_name="Golubtsov",
        middle_name="Sergeevich",
        birthdate=date(1995, 5, 15),
        passport_series="1234",
        passport_number="567890",
        is_insurance_enabled=True,
        is_salary_client=True,
    )

    credit = service.calculate_credit(scoring_data)

    assert credit.amount == Decimal("200000.00")
    assert credit.rate == Decimal("11.00")
    assert credit.term == 12
    assert len(credit.payment_schedule) == 12
    # Проверяем первый и последний платежи в графике
    assert credit.payment_schedule[0].number == 1
    # offers[0] и offers[-1] — обращение к элементам списка по индексу. Индекс 0 берёт первый элемент (как offers.get(0) в Java). Индекс -1 — удобная фишка Python, которая берёт последний элемент списка с конца (вместо offers.get(offers.size() - 1))
    assert credit.payment_schedule[-1].number == 12
    assert credit.payment_schedule[-1].remaining_debt == Decimal("0.00")
    assert credit.psk > Decimal("0")
