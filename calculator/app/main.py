from fastapi import FastAPI

from app.api.calculator import router as calculator_router

app = FastAPI(title="Calculator Microservice")

"""это точка входа в приложение (как класс с public static void main и @SpringBootApplication). 
Строкой include_router мы регистрируем наш контроллер в приложении (Подключаем наши эндпоинты из app/api/calculator.py к главному приложению)"""
app.include_router(calculator_router)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}
