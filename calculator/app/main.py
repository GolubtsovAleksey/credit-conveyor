from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


from app.api.calculator import router as calculator_router
from app.core.logger import logger

app = FastAPI(title="Calculator Microservice")
app.include_router(calculator_router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Ошибка валидации входных данных клиента: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}
