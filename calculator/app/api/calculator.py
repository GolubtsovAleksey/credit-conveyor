from fastapi import APIRouter

from app.core.logger import logger
from app.schemas.calculator import (
    CreditDto,
    LoanOfferDto,
    LoanStatementRequestDto,
    ScoringDataDto,
)
from app.services.calculator_service import CalculatorService

"""Создаём группу эндпоинтов с общим началом пути /calculator
   prefix="/calculator" означает, что ко всем путям в этом файле автоматически добавится /calculator в начале.
   tags=["Calculator"] — это просто название красивой папки-секции в интерфейсе Swagger UI"""
router = APIRouter(prefix="/calculator", tags=["Calculator"])

"""Создаём один экземпляр нашего сервиса (как @Service бин в Spring)"""
calculator_service = CalculatorService()

"""Декоратор @router.post("/offers") привязывает функцию ниже к HTTP-методу POST по полному адресу /calculator/offers.
   response_model=list[LoanOfferDto] говорит FastAPI:
   «Ответ этой функции должен быть списком объектов LoanOfferDto. 
   Преобразуй все поля в camelCase и покажи эту схему в Swagger»"""

"""• Когда клиент отправляет JSON на этот адрес, FastAPI сам:
	1. Читает JSON.
	2. Проверяет все правила из LoanStatementRequestDto (возраст от 18 лет, сумму от 20 000, серию и номер паспорта).
	3. Если что-то не так — сам возвращает ошибку 422 с описанием проблемы, даже не запуская тело функции.
	4. Если всё верно — передаёт готовый объект request внутрь функции, 
	где мы просто вызываем calculator_service.generate_offers(request)"""


@router.post("/offers", response_model=list[LoanOfferDto])
def get_loan_offers(request: LoanStatementRequestDto) -> list[LoanOfferDto]:
    """Принимает заявку и возвращает 4 кредитных предложения."""
    logger.info("POST /calculator/offers - запрос от %s %s", request.first_name, request.last_name)
    return calculator_service.generate_offers(request)


@router.post("/calc", response_model=CreditDto)
def calculate_credit(request: ScoringDataDto) -> CreditDto:
    """Принимает данные скоринга и возвращает полный расчёт кредита."""
    logger.info("POST /calculator/calc - запрос от %s %s", request.first_name, request.last_name)
    return calculator_service.calculate_credit(request)
