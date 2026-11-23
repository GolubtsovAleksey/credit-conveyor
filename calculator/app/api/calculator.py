from fastapi import APIRouter

from app.core.logger import logger
from app.schemas.calculator import (
    CreditDto,
    LoanOfferDto,
    LoanStatementRequestDto,
    ScoringDataDto,
)
from app.services.calculator_service import CalculatorService

router = APIRouter(prefix="/calculator", tags=["Calculator"])
calculator_service = CalculatorService()


@router.post("/offers", response_model=list[LoanOfferDto])
def get_loan_offers(request: LoanStatementRequestDto) -> list[LoanOfferDto]:
    """Принимает заявку и возвращает 4 кредитных предложения."""
    logger.info(
        "POST /calculator/offers - запрос на прескоринг от %s %s",
        request.first_name,
        request.last_name,
    )
    return calculator_service.generate_offers(request)


@router.post("/calc", response_model=CreditDto)
def calculate_credit(request: ScoringDataDto) -> CreditDto:
    """Принимает данные скоринга и возвращает полный расчёт кредита."""
    logger.info(
        "POST /calculator/calc - запрос на скоринг от %s %s",
        request.first_name,
        request.last_name,
    )
    return calculator_service.calculate_credit(request)
