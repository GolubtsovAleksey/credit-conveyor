"""Описание DTO и валидация входных данных"""

import re
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from pydantic.alias_generators import to_camel

MIN_AGE = 18
MIN_CREDIT_AMOUNT = Decimal("200000")
MIN_CREDIT_TERM = 6

NAME_PATTERN = re.compile(r"^[a-zA-Z]{2,30}$")
PASSPORT_SERIES_PATTERN = re.compile(r"^\d{4}$")
PASSPORT_NUMBER_PATTERN = re.compile(r"^\d{6}$")


class CamelCaseModel(BaseModel):
    """Базовая модель с преобразованием имён полей между snake_case и camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class BaseApplicantDto(CamelCaseModel):
    """Базовая модель с общими полями и валидацией данных заёмщика."""

    amount: Decimal
    term: int
    first_name: str
    last_name: str
    middle_name: str | None = None
    birthdate: date
    passport_series: str
    passport_number: str

    @field_validator("amount")
    @classmethod
    def check_amount(cls, value: Decimal) -> Decimal:
        if value < MIN_CREDIT_AMOUNT:
            raise ValueError("Сумма кредита должна быть не менее 200 000")
        return value

    @field_validator("term")
    @classmethod
    def check_term(cls, value: int) -> int:
        if value < MIN_CREDIT_TERM:
            raise ValueError("Срок кредита должен быть не менее 6 месяцев")
        return value

    @field_validator("first_name")
    @classmethod
    def check_first_name(cls, value: str) -> str:
        if not NAME_PATTERN.match(value):
            raise ValueError("Имя должно содержать от 2 до 30 латинских букв")
        return value

    @field_validator("last_name")
    @classmethod
    def check_last_name(cls, value: str) -> str:
        if not NAME_PATTERN.match(value):
            raise ValueError("Фамилия должна содержать от 2 до 30 латинских букв")
        return value

    @field_validator("middle_name")
    @classmethod
    def check_middle_name(cls, value: str | None) -> str | None:
        if value is not None and not NAME_PATTERN.match(value):
            raise ValueError("Отчество должно содержать от 2 до 30 латинских букв")
        return value

    @field_validator("passport_series")
    @classmethod
    def check_passport_series(cls, value: str) -> str:
        if not PASSPORT_SERIES_PATTERN.match(value):
            raise ValueError("Серия паспорта должна состоять из 4 цифр")
        return value

    @field_validator("passport_number")
    @classmethod
    def check_passport_number(cls, value: str) -> str:
        if not PASSPORT_NUMBER_PATTERN.match(value):
            raise ValueError("Номер паспорта должен состоять из 6 цифр")
        return value

    @field_validator("birthdate")
    @classmethod
    def check_age(cls, birthdate: date) -> date:
        today = date.today()
        age = today.year - birthdate.year

        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age = age - 1

        if age < MIN_AGE:
            raise ValueError("Клиент должен быть старше 18 лет")

        return birthdate


class LoanStatementRequestDto(BaseApplicantDto):
    """Входящий запрос на расчёт 4 кредитных предложений."""

    email: EmailStr


class ScoringDataDto(BaseApplicantDto):
    """Входящий запрос на полный расчёт кредита и графика платежей."""

    is_insurance_enabled: bool
    is_salary_client: bool


class LoanOfferDto(CamelCaseModel):
    """Одно кредитное предложение из списка."""

    statement_id: UUID
    requested_amount: Decimal
    total_amount: Decimal
    term: int
    monthly_payment: Decimal
    rate: Decimal
    is_insurance_enabled: bool
    is_salary_client: bool


class PaymentScheduleElementDto(CamelCaseModel):
    """Один ежемесячный платёж в графике."""

    number: int
    date: date
    total_payment: Decimal
    interest_payment: Decimal
    debt_payment: Decimal
    remaining_debt: Decimal


class CreditDto(CamelCaseModel):
    """Итоговый расчёт кредита с графиком платежей."""

    amount: Decimal
    term: int
    monthly_payment: Decimal
    rate: Decimal
    psk: Decimal
    is_insurance_enabled: bool
    is_salary_client: bool
    payment_schedule: list[PaymentScheduleElementDto]
