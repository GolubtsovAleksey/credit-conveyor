"""В этом файле 3 функции-помощники вверху и сам класс CalculatorService со всей кредитной логикой
Почему они вынесены за пределы класса? Потому что это простые математические и календарные операции,
которым не нужны настройки банка (self). В Java я бы положил их в MathUtils или DateUtils,
а в Python они просто лежат в начале файла."""
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from app.core.config import settings
from app.core.logger import logger
from app.schemas.calculator import (
    CreditDto,
    LoanOfferDto,
    LoanStatementRequestDto,
    PaymentScheduleElementDto,
    ScoringDataDto,
)
"""В Python нет ключевого слова final или const, поэтому по общему соглашению разработчиков (PEP 8) 
неизменяемые константы пишут ЗАГЛАВНЫМИ_БУКВАМИ в самом верху файла"""
"""Шаблон точности округления до сотых (до 2 знаков после запятой, то есть до копеек)"""
TWO_PLACES = Decimal("0.01")

"""Скидка к годовой процентной ставке (3 процентных пункта), если клиент соглашается оформить страховку"""
INSURANCE_RATE_DISCOUNT = Decimal("3.0")

"""Скидка к процентной ставке (1 процентный пункт), если клиент получает зарплату на карту нашего банка.
Для чего нужно: По ТЗ статус зарплатного клиента снижает ставку на 1 п.п. Если завтра банк решит изменить размер скидки 
(например, на 1.5%), вам нужно будет поменять число только в одном месте вверху файла"""
SALARY_CLIENT_RATE_DISCOUNT = Decimal("1.0")



def round_money(value: Decimal) -> Decimal:
    """Округляет сумму до копеек (2 знака после запятой)."""
    return value.quantize(TWO_PLACES,
                          # .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) округляет число по привычным правилам:
                          # если третья цифра после запятой 5 и больше — округляем вверх
                          rounding=ROUND_HALF_UP)


""" Зачем: Когда мы строим график платежей на 12 месяцев, нам нужно для каждого платежа вычислить дату 
(сегодня + 1 месяц, сегодня + 2 месяца и т.д.). В стандартном Python у date нет готового метода .plusMonths(), как в Java
Как работает: Считаем новый год и новый месяц через целочисленное деление // 12 и остаток % 12"""
def add_months(source_date: date, months: int) -> date:

    """Прибавляет нужное количество месяцев к дате."""
    total_months = source_date.month - 1 + months
    year = source_date.year + total_months // 12
    month = total_months % 12 + 1

    # в Python принято называть ненужную переменную при распаковке символом нижнего подчёркивания _
    # нам нужно только количество дней days_in_month
    # monthrange - узнаёт информацию о феврале 2026 года. Она возвращает пару чисел
    # в Python это называется кортежем — tuple
    _, days_in_month = calendar.monthrange(year, month)

    # защищает от ошибки: если кредит взяли 31 января, то через месяц платёж назначится на 28 (или 29) февраля,
    # а не упадёт с ошибкой «31 февраля не существует»
    day = min(source_date.day,days_in_month)
    return date(year, month, day)

"""Зачем: Эта функция нужна только для сортировки списка предложений. 
Она принимает одно предложение и просто возвращает его процентную ставку (offer.rate)"""
def get_offer_rate(offer: LoanOfferDto) -> Decimal:
    return offer.rate


class CalculatorService:
    """Сервис расчёта кредитных предложений и полного графика платежей."""

    """В Java конструктор называется так же, как класс (public CalculatorService(...)). 
    В Python конструктор всегда называется __init__"""
    def __init__(

            self,  # self — это ссылка на текущий объект (полный аналог this в Java)
            base_rate: Decimal = settings.base_rate,

            # В параметрах мы указали значения по умолчанию (= settings.base_rate).
            # Это значит: когда приложение работает в обычном режиме, мы просто пишем CalculatorService(),
            # и оно само подтягивает 15.0 и 100000 из файла .env. А когда мы будем писать тесты,
            # мы сможем передать туда любые тестовые цифры
            insurance_cost: Decimal = settings.insurance_cost,
    ):
        self.base_rate = base_rate
        self.insurance_cost = insurance_cost

    """Берёт базовую ставку self.base_rate. Если есть страховка (is_insurance_enabled == True), вычитает 3.0. 
    Если зарплатный клиент — вычитает 1.0. Возвращает округлённую ставку"""
    def calculate_rate(self, is_insurance_enabled: bool, is_salary_client: bool) -> Decimal:

        """Считает итоговую годовую ставку с учётом скидок."""
        rate = self.base_rate
        if is_insurance_enabled:
            rate = rate - INSURANCE_RATE_DISCOUNT
        if is_salary_client:
            rate = rate - SALARY_CLIENT_RATE_DISCOUNT
        return round_money(rate)

    """Берёт сумму, которую попросил клиент (requested_amount). Если клиент выбрал страховку, 
    прибавляет её стоимость (100 000) к сумме кредита"""
    def calculate_total_amount(self, requested_amount: Decimal, is_insurance_enabled: bool) -> Decimal:

        """Считает итоговую сумму кредита"""
        total = requested_amount
        if is_insurance_enabled:
            total = total + self.insurance_cost
        return round_money(total)

    """Считает ежемесячный аннуитетный платёж по банковской формуле"""
    def calculate_monthly_payment(self, total_amount: Decimal, rate: Decimal, term: int) -> Decimal:
        monthly_rate = rate / Decimal("12") / Decimal("100")
        factor = (Decimal("1") + monthly_rate) ** term
        annuity_coefficient = (monthly_rate * factor) / (factor - Decimal("1"))
        return round_money(total_amount * annuity_coefficient)

    """ТЗ: нужно вернуть 4 кредитных предложения для всех комбинаций страховки и зарплатного клиента, 
       отсортированные от худшего к лучшему"""
    def _create_offer(

            # Принимает заявку и два булевых флага (True/False). Вызывает три метода выше (считает ставку, сумму и платёж),
            # генерирует случайный uuid4() для statement_id и собирает один готовый объект LoanOfferDto
            self,

            # Нижнее подчёркивание _ в начале имени метода — это правило хорошего тона в Python.
            # Оно заменяет слово private из Java и говорит другим разработчикам: «это внутренний помощник класса»
            request: LoanStatementRequestDto,
            is_insurance_enabled: bool,
            is_salary_client: bool,
    ) -> LoanOfferDto:

        """Создаёт одно кредитное предложение для заданных параметров."""
        rate = self.calculate_rate(is_insurance_enabled, is_salary_client)
        total_amount = self.calculate_total_amount(request.amount, is_insurance_enabled)
        monthly_payment = self.calculate_monthly_payment(total_amount, rate, request.term)

        return LoanOfferDto(
            statement_id=uuid4(),
            requested_amount=round_money(request.amount),
            total_amount=total_amount,
            term=request.term,
            monthly_payment=monthly_payment,
            rate=rate,
            is_insurance_enabled=is_insurance_enabled,
            is_salary_client=is_salary_client,
        )

    def generate_offers(self, request: LoanStatementRequestDto) -> list[LoanOfferDto]:
        """Формирует 4 кредитных предложения и сортирует от худшего к лучшему."""
        logger.info("Начало расчёта предложений: amount=%s, term=%s", request.amount, request.term)

        combinations = [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ]

        offers: list[LoanOfferDto] = []

        # Проходит по ним циклом for is_insurance, is_salary in combinations:,
        # на каждом шаге вызывает _create_offer и добавляет результат в список offers через offers.append(offer)
        # (аналог list.add() в Java)
        for is_insurance, is_salary in combinations:
            offer = self._create_offer(request, is_insurance, is_salary)
            offers.append(offer)

        """Сортируем от большей ставки к меньшей (от худшего предложения к лучшему)"""
        offers.sort(key=get_offer_rate,
                    reverse=True)
        logger.info("Сформировано %d кредитных предложений", len(offers))
        return offers

    """ График платежей и полный расчёт (_build_payment_schedule и calculate_credit)
     Как строится график
     запускаем цикл от 1 до term включительно: for month_num in range(1, term + 1):.
     На каждом месяце делаем 4 шага"""
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
            payment_date = add_months(start_date, month_num)  # Вычисляем дату платежа
            interest_payment = round_money(
                remaining_debt * monthly_rate)  # Считаем проценты банку за этот месяц: умножаем текущий остаток долга (remaining_debt) на месячную ставку

            if month_num == term:  # Важный момент в последнем месяце: Из-за того, что каждый месяц мы округляем цифры до копеек, к последнему месяцу может накопиться разница в 1–2 копейки. Поэтому в последний месяц мы не вычитаем проценты, а просто закрываем весь остаток долга целиком (debt_payment = remaining_debt), чтобы в конце остаток стал строго 0.00
                debt_payment = remaining_debt
                actual_total_payment = round_money(debt_payment + interest_payment)
            else:
                debt_payment = round_money(
                    monthly_payment - interest_payment)  # Считаем погашение основного долга: из общего ежемесячного платежа вычитаем проценты (monthly_payment - interest_payment)
                actual_total_payment = monthly_payment

            remaining_debt = round_money(
                remaining_debt - debt_payment)  # Вычитаем погашенную часть из remaining_debt, создаём объект PaymentScheduleElementDto и кладем его в список schedule

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

    """Этот метод работает как главный сценарий для эндпоинта /calculator/calc:
       1. Вычисляет ставку, итоговую сумму (со страховкой или без) и ежемесячный платёж.
       2. Строит график платежей через _build_payment_schedule.
       3. Обычным циклом for element in schedule: складывает все ежемесячные платежи в переменную total_payout (чтобы узнать, сколько всего денег клиент отдаст банку за весь срок).
       4. Считает ПСК (полную стоимость кредита в % годовых): смотрит, во сколько раз общая сумма выплат больше изначально запрошенной суммы (overpayment_ratio), делит на количество лет кредита (years) и умножает на 100.
       5. Упаковывает все цифры и готовый график в объект CreditDto и возвращает его."""
    def calculate_credit(self, scoring_data: ScoringDataDto) -> CreditDto:
        """Полный расчёт параметров кредита, ПСК и графика платежей."""
        logger.info(
            "Начало полного расчёта: amount=%s, term=%s, insurance=%s, salary=%s",
            scoring_data.amount,
            scoring_data.term,
            scoring_data.is_insurance_enabled,
            scoring_data.is_salary_client,
        )

        rate = self.calculate_rate(scoring_data.is_insurance_enabled, scoring_data.is_salary_client)
        total_amount = self.calculate_total_amount(scoring_data.amount, scoring_data.is_insurance_enabled)
        monthly_payment = self.calculate_monthly_payment(total_amount, rate, scoring_data.term)

        schedule = self._build_payment_schedule(
            total_amount=total_amount,
            rate=rate,
            term=scoring_data.term,
            monthly_payment=monthly_payment,
        )

        # Считаем общую сумму всех выплат по графику
        total_payout = Decimal("0")
        for element in schedule:
            total_payout = total_payout + element.total_payment

        # Считаем полную стоимость кредита (ПСК) в % годовых
        years = Decimal(scoring_data.term) / Decimal("12")
        overpayment_ratio = (total_payout / scoring_data.amount) - Decimal("1")
        psk = round_money((overpayment_ratio / years) * Decimal("100"))

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
