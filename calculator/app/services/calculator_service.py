import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from app.core.config import Settings, settings
from app.core.logger import logger
from app.schemas.calculator import (
    CreditDto,
    LoanOfferDto,
    LoanStatementRequestDto,
    PaymentScheduleElementDto,
    ScoringDataDto,
)

TWO_PLACES = Decimal("0.01")  # Точность округления до копеек
INSURANCE_RATE_DISCOUNT = Decimal("3.0")  # Скидка к ставке за страховку (п.п.)
SALARY_CLIENT_RATE_DISCOUNT = Decimal("1.0")  # Скидка к ставке для зарплатного клиента (п.п.)



def get_offer_rate(offer: LoanOfferDto) -> Decimal:
    """Возвращает процентную ставку предложения для сортировки."""
    return offer.rate


class CalculatorService:
    def __init__(self, config: Settings = settings):
        self.config = config

    def generate_offers(self, request: LoanStatementRequestDto) -> list[LoanOfferDto]:
        """Формирует 4 кредитных предложения и сортирует их от худшего к лучшему."""
        logger.info("Начало расчёта предложений: amount=%s, term=%s", request.amount, request.term)

        statement_id = uuid4()
        combinations = [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ]

        offers: list[LoanOfferDto] = []
        for is_insurance, is_salary in combinations:
            offer = self._create_offer(request, statement_id, is_insurance, is_salary)
            offers.append(offer)

        offers.sort(key=get_offer_rate, reverse=True)
        logger.info("Сформировано %d кредитных предложений", len(offers))
        return offers

    def calculate_credit(self, scoring_data: ScoringDataDto) -> CreditDto:
        """Выполняет полный расчёт параметров кредита, ПСК и графика платежей."""
        logger.info(
            "Начало полного расчёта: amount=%s, term=%s, insurance=%s, salary=%s",
            scoring_data.amount,
            scoring_data.term,
            scoring_data.is_insurance_enabled,
            scoring_data.is_salary_client,
        )

        rate = self._calculate_rate(scoring_data.is_insurance_enabled, scoring_data.is_salary_client)
        total_amount = self._calculate_total_amount(scoring_data.amount, scoring_data.is_insurance_enabled)
        monthly_payment = self._calculate_monthly_payment(total_amount, rate, scoring_data.term)

        schedule = self._build_payment_schedule(
            total_amount=total_amount,
            rate=rate,
            term=scoring_data.term,
            monthly_payment=monthly_payment,
        )

        total_payout = Decimal("0")
        for element in schedule:
            total_payout = total_payout + element.total_payment

        years = Decimal(scoring_data.term) / Decimal("12")
        overpayment_ratio = (total_payout / total_amount) - Decimal("1")
        psk = self._round_money((overpayment_ratio / years) * Decimal("100"))

        credit = CreditDto(
            amount=total_amount,
            term=scoring_data.term,
            monthly_payment=monthly_payment,
            rate=rate,
            psk=psk,
            is_insurance_enabled=scoring_data.is_insurance_enabled,
            is_salary_client=scoring_data.is_salary_client,
            payment_schedule=schedule,
        )
        logger.info("Полный расчёт завершён: rate=%s%%, psk=%s%%", rate, psk)
        return credit

    def _create_offer(
            self,
            request: LoanStatementRequestDto,
            statement_id: UUID,
            is_insurance_enabled: bool,
            is_salary_client: bool,
    ) -> LoanOfferDto:
        """Создаёт одно кредитное предложение для заданных параметров."""
        rate = self._calculate_rate(is_insurance_enabled, is_salary_client)
        total_amount = self._calculate_total_amount(request.amount, is_insurance_enabled)
        monthly_payment = self._calculate_monthly_payment(total_amount, rate, request.term)

        return LoanOfferDto(
            statement_id=statement_id,
            requested_amount=self._round_money(request.amount),
            total_amount=total_amount,
            term=request.term,
            monthly_payment=monthly_payment,
            rate=rate,
            is_insurance_enabled=is_insurance_enabled,
            is_salary_client=is_salary_client,
        )

    def _build_payment_schedule(
            self,
            total_amount: Decimal,
            rate: Decimal,
            term: int,
            monthly_payment: Decimal,
    ) -> list[PaymentScheduleElementDto]:
        """Строит список ежемесячных платежей на весь срок кредита."""
        schedule: list[PaymentScheduleElementDto] = []
        remaining_debt = total_amount
        monthly_rate = rate / Decimal("12") / Decimal("100")
        start_date = date.today()

        for month_num in range(1, term + 1):
            payment_date = self._add_months(start_date, month_num)
            interest_payment = self._round_money(remaining_debt * monthly_rate)

            if month_num == term:
                debt_payment = remaining_debt
                actual_total_payment = self._round_money(debt_payment + interest_payment)
            else:
                debt_payment = self._round_money(monthly_payment - interest_payment)
                actual_total_payment = monthly_payment

            remaining_debt = self._round_money(remaining_debt - debt_payment)

            element = PaymentScheduleElementDto(
                number=month_num,
                date=payment_date,
                total_payment=actual_total_payment,
                interest_payment=interest_payment,
                debt_payment=debt_payment,
                remaining_debt=remaining_debt,
            )
            schedule.append(element)

        return schedule

    def _add_months(self, source_date: date, months: int) -> date:
        """Прибавляет заданное количество месяцев к дате."""
        total_months = source_date.month - 1 + months
        year = source_date.year + total_months // 12
        month = total_months % 12 + 1
        _, days_in_month = calendar.monthrange(year, month)
        day = min(source_date.day, days_in_month)
        return date(year, month, day)

    def _calculate_rate(self, is_insurance_enabled: bool, is_salary_client: bool) -> Decimal:
        """Рассчитывает итоговую годовую ставку с учётом скидок."""
        rate = self.config.base_rate
        if is_insurance_enabled:
            rate = rate - INSURANCE_RATE_DISCOUNT
        if is_salary_client:
            rate = rate - SALARY_CLIENT_RATE_DISCOUNT
        return self._round_money(rate)

    def _calculate_total_amount(self, requested_amount: Decimal, is_insurance_enabled: bool) -> Decimal:
        """Рассчитывает итоговую сумму кредита с учётом стоимости страховки."""
        total = requested_amount
        if is_insurance_enabled:
            total = total + self.config.insurance_cost
        return self._round_money(total)

    def _calculate_monthly_payment(self, total_amount: Decimal, rate: Decimal, term: int) -> Decimal:
        """Рассчитывает ежемесячный аннуитетный платёж."""
        monthly_rate = rate / Decimal("12") / Decimal("100")
        factor = (Decimal("1") + monthly_rate) ** term
        annuity_coefficient = (monthly_rate * factor) / (factor - Decimal("1"))
        return self._round_money(total_amount * annuity_coefficient)

    def _round_money(self, value: Decimal) -> Decimal:
        """Округляет сумму до копеек."""
        return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
