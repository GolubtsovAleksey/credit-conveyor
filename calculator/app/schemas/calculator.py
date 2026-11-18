"""В Spring Boot вы создаёте DTO-классы с (@NotNull, @Min, @Pattern, @Email).
Когда на контроллер приходит JSON, Spring сам превращает его в объект и проверяет правила.
В FastAPI эту роль выполняет библиотека Pydantic. Файл calculator.py — это описание всех входящих
и исходящих JSON-документов нашего сервиса вместе с правилами их проверки"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

# 1) Настройка имён полей (CamelCaseModel)
# 2) В Python по стандарту принято писать через нижнее подчёркивание: first_name, passport_series (snake_case)
# 3) Как работает: BaseModel — это главный родительский класс из Pydantic (как Object в мире DTO).
# Мы создаём свой базовый класс CamelCaseModel и задаём ему настройку alias_generator=to_camel.
# Теперь любой класс, унаследованный от CamelCaseModel, будет автоматически переводить first_name в firstName
# при отправке JSON и обратно при приёме
class CamelCaseModel(BaseModel):

    """Базовый класс: переводит имена полей между snake_case (Python) и camelCase (JSON)."""
    model_config = ConfigDict(
        alias_generator=to_camel,

        # Разрешает нам в коде и тестах обращаться к полю по-питоновски (dto.first_name), даже если снаружи пришло firstName
        populate_by_name=True,
    )

# Проверка возраста
# Зачем отдельная функция: В Python функции можно писать прямо в файле без создания утильного класса DateUtils.
# Функция принимает дату рождения (birthdate: date) и возвращает её же (-> date), если проверка прошла успешно
def validate_adult_age(birthdate: date) -> date:
    """Проверяет, что клиенту исполнилось 18 лет."""
    today = date.today()     # берём сегодняшнюю дату (как LocalDate.now() в Java)
    age = today.year - birthdate.year  # вычитаем год рождения из текущего года

    # Если день рождения в этом году ещё не наступил, вычитаем 1 год
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age = age - 1

    if age < 18:
        # Выбрасываем исключение, Pydantic поймает эту ошибку и сам вернёт клиенту ответ с HTTP-кодом 422 и текстом ошибки
        raise ValueError("Клиент должен быть старше 18 лет")

    return birthdate

# Общий родитель для заявок
# Нужен чтобы не дублировать 8 одинаковых полей в двух разных классах
class BaseApplicantDto(CamelCaseModel):
    """Общие поля и правила валидации для входящих заявок."""
    amount: Decimal = Field(..., ge=Decimal("20000"))   # имя поля и его тип (аналог private BigDecimal amount; в Java)
                                                        # ge=Decimal("20000") — сокращение от Greater or Equal (больше или равно 20 000)
    term: int = Field(..., ge=6)                        # Field(...) — задаёт правила проверки. Троеточие ... на первом месте означает, что поле обязательное (нельзя прислать пустой JSON без этого поля)
    first_name: str = Field(..., pattern=r"^[a-zA-Z]{2,30}$")  # pattern=r"^[a-zA-Z]{2,30}$" — регулярное выражение: только латинские буквы, от 2 до 30 штук. Буква r перед строкой нужна, чтобы Python не воспринимал обратный слеш \ как спецсимвол
    last_name: str = Field(..., pattern=r"^[a-zA-Z]{2,30}$")
    middle_name: str | None = Field(default=None, pattern=r"^[a-zA-Z]{2,30}$") # middle_name — отчество может быть строкой (str) или отсутствовать (None, аналог null в Java). Если его не передадут в JSON, подставится None
    birthdate: date
    passport_series: str = Field(..., pattern=r"^\d{4}$")
    passport_number: str = Field(..., pattern=r"^\d{6}$")

    # Привязка проверки возраста к полю
    # говорит Pydantic: «После того как ты прочитаешь поле birthdate из JSON, обязательно прогони его через функцию check_age»
    @field_validator("birthdate")

    # @classmethod и cls — требование самого Pydantic: проверка запускается на уровне класса ещё до того,
    # как объект DTO окончательно соберётся в памяти. В value попадает дата рождения, а внутри мы вызываем
    # нашу понятную функцию validate_adult_age(value)
    @classmethod
    def check_age(cls, value: date) -> date:
        return validate_adult_age(value)

# Наследники и классы ответов
# Класс автоматически забирает все 8 полей и проверку возраста, добавляя только поле email
# со встроенной проверкой формата почты (EmailStr)
class LoanStatementRequestDto(BaseApplicantDto):
    """Входящий запрос на расчёт 4 кредитных предложений."""
    email: EmailStr

# Точно так же ScoringDataDto(BaseApplicantDto) добавляет только два булевых поля (is_insurance_enabled и is_salary_client)
class ScoringDataDto(BaseApplicantDto):
    """Входящий запрос на полный расчёт кредита и графика платежей."""
    is_insurance_enabled: bool
    is_salary_client: bool

# Классы ответа (LoanOfferDto, PaymentScheduleElementDto, CreditDto) просто описывают поля, которые наш сервис вернёт наружу.
# Валидация там не нужна, поэтому Field(...) не пишем
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
