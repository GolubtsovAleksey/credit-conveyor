from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.config import Settings
from app.schemas.calculator import LoanStatementRequestDto, ScoringDataDto
from app.services.calculator_service import CalculatorService, get_offer_rate


@pytest.fixture
def service() -> CalculatorService:
    """Создаёт сервис с фиксированными настройками для тестов."""
    test_settings = Settings(
        base_rate=Decimal("15.0"),
        insurance_cost=Decimal("100000"),
    )
    return CalculatorService(config=test_settings)


@pytest.fixture
def valid_request() -> LoanStatementRequestDto:
    """Создаёт базовую валидную заявку на кредит."""
    return LoanStatementRequestDto(
        amount=Decimal("200000"),
        term=12,
        first_name="Lexa",
        last_name="Golubtsov",
        middle_name="Sergeevich",
        email="lexa@example.com",
        birthdate=date(1995, 5, 15),
        passport_series="1234",
        passport_number="567890",
    )

@pytest.fixture
def valid_request() -> LoanStatementRequestDto:
    """Создаёт базовую валидную заявку на кредит."""
    return LoanStatementRequestDto(
        amount=Decimal("200000"),
        term=12,
        first_name="Lexa",
        last_name="Golubtsov",
        middle_name="Sergeevich",
        email="lexa@example.com",
        birthdate=date(1995, 5, 15),
        passport_series="1234",
        passport_number="567890",
    )

@pytest.fixture
def valid_scoring_data(valid_request: LoanStatementRequestDto) -> ScoringDataDto:
    """Создаёт валидные данные для полного скоринга на основе базовой заявки."""
    request_data = valid_request.model_dump(exclude={"email"})
    return ScoringDataDto(
        **request_data,
        is_insurance_enabled=True,
        is_salary_client=True,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("100.123"), Decimal("100.12")),
        (Decimal("100.125"), Decimal("100.13")),
        (Decimal("100"), Decimal("100.00")),
    ],
)
def test_round_money(service: CalculatorService, value: Decimal, expected: Decimal):
    """Проверяет банковское округление (ROUND_HALF_UP) до двух знаков."""
    assert service._round_money(value) == expected


@pytest.mark.parametrize(
    ("is_insurance_enabled", "is_salary_client", "expected_rate"),
    [
        (False, False, Decimal("15.00")),
        (False, True, Decimal("14.00")),
        (True, False, Decimal("12.00")),
        (True, True, Decimal("11.00")),
    ],
)
def test_calculate_rate(
        service: CalculatorService,
        is_insurance_enabled: bool,
        is_salary_client: bool,
        expected_rate: Decimal,
):
    """Проверяет расчёт процентной ставки для всех комбинаций опций."""
    rate = service._calculate_rate(is_insurance_enabled, is_salary_client)
    assert rate == expected_rate


@pytest.mark.parametrize(
    ("requested_amount", "is_insurance_enabled", "expected_total"),
    [
        (Decimal("200000"), False, Decimal("200000.00")),
        (Decimal("200000"), True, Decimal("300000.00")),
        (Decimal("500000.55"), True, Decimal("600000.55")),
    ],
)
def test_calculate_total_amount(
        service: CalculatorService,
        requested_amount: Decimal,
        is_insurance_enabled: bool,
        expected_total: Decimal,
):
    """Проверяет добавление стоимости страховки к сумме кредита."""
    total = service._calculate_total_amount(requested_amount, is_insurance_enabled)
    assert total == expected_total


@pytest.mark.parametrize(
    ("total_amount", "rate", "term", "expected_payment"),
    [
        (Decimal("200000.00"), Decimal("15.00"), 12, Decimal("18051.66")),
        (Decimal("300000.00"), Decimal("11.00"), 12, Decimal("26514.50")),
        (Decimal("600000.00"), Decimal("12.00"), 24, Decimal("28244.08")),
    ],
)
def test_calculate_monthly_payment(
        service: CalculatorService,
        total_amount: Decimal,
        rate: Decimal,
        term: int,
        expected_payment: Decimal,
):
    """Проверяет расчёт ежемесячного аннуитетного платежа."""
    payment = service._calculate_monthly_payment(total_amount, rate, term)
    assert payment == expected_payment


@pytest.mark.parametrize(
    ("source_date", "months", "expected_date"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),   # Обычный февраль (28 дней)
        (date(2024, 1, 31), 1, date(2024, 2, 29)),   # Високосный год (29 дней)
        (date(2026, 3, 31), 1, date(2026, 4, 30)),   # Переход с 31 на 30 число
        (date(2026, 10, 15), 4, date(2027, 2, 15)),  # Переход через границу года
        (date(2026, 5, 10), 12, date(2027, 5, 10)),  # Ровно 1 год
    ],
)
def test_add_months(
        service: CalculatorService,
        source_date: date,
        months: int,
        expected_date: date,
):
    """Проверяет прибавление месяцев с учётом високосных лет и концов месяца."""
    assert service._add_months(source_date, months) == expected_date


def test_create_offer(service: CalculatorService, valid_request: LoanStatementRequestDto):
    """Проверяет создание одного кредитного предложения с заданными флагами."""
    statement_id = UUID("12345678-1234-5678-1234-567812345678")
    offer = service._create_offer(
        request=valid_request,
        statement_id=statement_id,
        is_insurance_enabled=True,
        is_salary_client=False,
    )

    assert offer.statement_id == statement_id
    assert offer.requested_amount == Decimal("200000.00")
    assert offer.total_amount == Decimal("300000.00")
    assert offer.term == 12
    assert offer.rate == Decimal("12.00")
    assert offer.monthly_payment == Decimal("26654.64")
    assert offer.is_insurance_enabled is True
    assert offer.is_salary_client is False


def test_get_offer_rate(service: CalculatorService, valid_request: LoanStatementRequestDto):
    """Проверяет извлечение процентной ставки из предложения для сортировки."""
    statement_id = UUID("12345678-1234-5678-1234-567812345678")
    offer = service._create_offer(valid_request, statement_id, True, True)
    assert get_offer_rate(offer) == Decimal("11.00")


def test_build_payment_schedule(service: CalculatorService):
    """Проверяет построение графика платежей, уменьшение долга и обнуление в конце."""
    schedule = service._build_payment_schedule(
        total_amount=Decimal("200000.00"),
        rate=Decimal("15.00"),
        term=6,
        monthly_payment=Decimal("34806.76"),
    )

    assert len(schedule) == 6
    assert schedule[0].number == 1
    assert schedule[-1].number == 6
    assert schedule[-1].remaining_debt == Decimal("0.00")  # Полное погашение долга
    for element in schedule:
        assert element.total_payment == element.debt_payment + element.interest_payment


def test_generate_offers_returns_four_offers(
        service: CalculatorService,
        valid_request: LoanStatementRequestDto,
):
    """1. Проверяет, что прескоринг всегда возвращает ровно 4 предложения."""
    offers = service.generate_offers(valid_request)
    assert len(offers) == 4


def test_generate_offers_sorted_from_worst_to_best(
        service: CalculatorService,
        valid_request: LoanStatementRequestDto,
):
    """2. Проверяет сортировку предложений по убыванию ставки (от худшего к лучшему)."""
    offers = service.generate_offers(valid_request)
    rates = [offer.rate for offer in offers]
    assert rates == [
        Decimal("15.00"),
        Decimal("14.00"),
        Decimal("12.00"),
        Decimal("11.00"),
    ]


def test_generate_offers_share_single_statement_id(
        service: CalculatorService,
        valid_request: LoanStatementRequestDto,
):
    """3. Проверяет, что все 4 предложения в рамках одной заявки имеют общий statement_id."""
    offers = service.generate_offers(valid_request)
    statement_ids = {offer.statement_id for offer in offers}
    assert len(statement_ids) == 1


def test_generate_offers_all_combinations_present(
        service: CalculatorService,
        valid_request: LoanStatementRequestDto,
):
    """4. Проверяет наличие всех 4 уникальных комбинаций страховки и зарплатного клиента."""
    offers = service.generate_offers(valid_request)
    combinations = {(offer.is_insurance_enabled, offer.is_salary_client) for offer in offers}
    assert combinations == {
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    }


@pytest.mark.parametrize(
    ("offer_index", "expected_rate", "expected_total", "expected_payment"),
    [
        (0, Decimal("15.00"), Decimal("200000.00"), Decimal("18051.66")),  # Без опций
        (1, Decimal("14.00"), Decimal("200000.00"), Decimal("17957.42")),  # Только зарплатный
        (2, Decimal("12.00"), Decimal("300000.00"), Decimal("26654.64")),  # Только страховка
        (3, Decimal("11.00"), Decimal("300000.00"), Decimal("26514.50")),  # Страховка + зарплатный
    ],
)
def test_generate_offers_parameters_for_each_option(
        service: CalculatorService,
        valid_request: LoanStatementRequestDto,
        offer_index: int,
        expected_rate: Decimal,
        expected_total: Decimal,
        expected_payment: Decimal,
):
    """5-8. Проверяет ставку, итоговую сумму и платёж для каждого из 4 предложений."""
    offers = service.generate_offers(valid_request)
    offer = offers[offer_index]

    assert offer.rate == expected_rate
    assert offer.total_amount == expected_total
    assert offer.monthly_payment == expected_payment
    assert offer.requested_amount == Decimal("200000.00")
    assert offer.term == valid_request.term


def test_generate_offers_without_middle_name(
        service: CalculatorService,
        valid_request: LoanStatementRequestDto,
):
    """9. Проверяет корректный расчёт предложений для клиента без отчества."""
    request_no_middle = valid_request.model_copy(update={"middle_name": None})
    offers = service.generate_offers(request_no_middle)

    assert len(offers) == 4
    assert offers[0].total_amount == Decimal("200000.00")


def test_generate_offers_with_custom_config(valid_request: LoanStatementRequestDto):
    """10. Проверяет, что сервис использует базовую ставку и страховку из переданного конфига."""
    custom_settings = Settings(
        base_rate=Decimal("20.0"),
        insurance_cost=Decimal("50000"),
    )
    custom_service = CalculatorService(config=custom_settings)

    offers = custom_service.generate_offers(valid_request)

    assert offers[0].rate == Decimal("20.00")
    assert offers[0].total_amount == Decimal("200000.00")
    assert offers[-1].rate == Decimal("16.00")
    assert offers[-1].total_amount == Decimal("250000.00")


@pytest.mark.parametrize(
    ("is_insurance", "is_salary", "expected_amount", "expected_rate", "expected_payment"),
    [
        (False, False, Decimal("200000.00"), Decimal("15.00"), Decimal("18051.66")),
        (False, True, Decimal("200000.00"), Decimal("14.00"), Decimal("17957.42")),
        (True, False, Decimal("300000.00"), Decimal("12.00"), Decimal("26654.64")),
        (True, True, Decimal("300000.00"), Decimal("11.00"), Decimal("26514.50")),
    ],
)
def test_calculate_credit_options_combinations(
        service: CalculatorService,
        valid_scoring_data: ScoringDataDto,
        is_insurance: bool,
        is_salary: bool,
        expected_amount: Decimal,
        expected_rate: Decimal,
        expected_payment: Decimal,
):
    """1-4. Проверяет расчёт суммы, ставки и платежа для всех комбинаций опций."""
    data = valid_scoring_data.model_copy(
        update={
            "is_insurance_enabled": is_insurance,
            "is_salary_client": is_salary,
        }
    )
    credit = service.calculate_credit(data)

    assert credit.amount == expected_amount
    assert credit.rate == expected_rate
    assert credit.monthly_payment == expected_payment
    assert credit.is_insurance_enabled is is_insurance
    assert credit.is_salary_client is is_salary


def test_calculate_credit_schedule_length_and_numbering(
        service: CalculatorService,
        valid_scoring_data: ScoringDataDto,
):
    """5. Проверяет количество платежей в графике и их последовательную нумерацию."""
    credit = service.calculate_credit(valid_scoring_data)

    assert len(credit.payment_schedule) == valid_scoring_data.term
    numbers = [item.number for item in credit.payment_schedule]
    assert numbers == list(range(1, valid_scoring_data.term + 1))


def test_calculate_credit_zero_remaining_debt_at_end(
        service: CalculatorService,
        valid_scoring_data: ScoringDataDto,
):
    """6. Проверяет, что после последнего платежа остаток долга равен нулю."""
    credit = service.calculate_credit(valid_scoring_data)
    assert credit.payment_schedule[-1].remaining_debt == Decimal("0.00")


def test_calculate_credit_debt_decreases_every_month(
        service: CalculatorService,
        valid_scoring_data: ScoringDataDto,
):
    """7. Проверяет, что остаток долга строго уменьшается с каждым месяцем."""
    credit = service.calculate_credit(valid_scoring_data)
    debts = [item.remaining_debt for item in credit.payment_schedule]

    for i in range(1, len(debts)):
        assert debts[i] < debts[i - 1]


def test_calculate_credit_schedule_payment_components_sum(
        service: CalculatorService,
        valid_scoring_data: ScoringDataDto,
):
    """8. Проверяет, что в каждом месяце total_payment == debt_payment + interest_payment."""
    credit = service.calculate_credit(valid_scoring_data)

    for item in credit.payment_schedule:
        assert item.total_payment == item.debt_payment + item.interest_payment


def test_calculate_credit_psk_calculation(
        service: CalculatorService,
        valid_scoring_data: ScoringDataDto,
):
    """9. Проверяет точность расчёта полной стоимости кредита (ПСК)."""
    credit = service.calculate_credit(valid_scoring_data)
    assert credit.psk == Decimal("6.06")


def test_calculate_credit_with_custom_term_and_config(valid_scoring_data: ScoringDataDto):
    """10. Проверяет скоринг на другом сроке (6 месяцев) и с кастомными настройками."""
    custom_settings = Settings(
        base_rate=Decimal("18.0"),
        insurance_cost=Decimal("50000"),
    )
    custom_service = CalculatorService(config=custom_settings)
    data = valid_scoring_data.model_copy(
        update={
            "amount": Decimal("300000"),
            "term": 6,
            "is_insurance_enabled": True,
            "is_salary_client": False,
        }
    )

    credit = custom_service.calculate_credit(data)

    assert credit.amount == Decimal("350000.00")
    assert credit.term == 6
    assert credit.rate == Decimal("15.00")
    assert len(credit.payment_schedule) == 6
    assert credit.payment_schedule[-1].remaining_debt == Decimal("0.00")
