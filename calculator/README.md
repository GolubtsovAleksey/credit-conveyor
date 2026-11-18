# Микросервис Calculator (MVP Level 1)

Микросервис для предварительного расчёта кредитных предложений (`POST /calculator/offers`) и полного расчёта параметров кредита с графиком платежей (`POST /calculator/calc`).

---

## 1. Настройка окружения (`.env`)

Перед первым запуском убедитесь, что в папке `calculator/` есть файл `.env` со следующими параметрами:

```env
BASE_RATE=15.0
INSURANCE_COST=100000
```

---

## 2. Как запустить приложение

## Через терминал (PowerShell)
Откройте вкладку **Terminal** внизу IDEA (убедитесь, что вы находитесь в корневой папке `credit-conveyor`) и выполните команду:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir calculator
```

* Чтобы остановить сервер в терминале, кликните в окно терминала и нажмите **`Ctrl + C`**.

---

## 3. Как проверить работу через Swagger UI (куда тыкать)

1. После запуска сервера откройте в браузере полную ссылку на документацию Swagger UI:  
      **http://127.0.0.1:8000/docs**

2. Выберите нужный эндпоинт (`POST /calculator/offers` или `POST /calculator/calc`) и нажмите на него, чтобы раскрыть.
3. Нажмите серую кнопку **`Try it out`** справа.
4. В окне **Request body** поправьте тестовый JSON (обязательно замените `"birthdate"` на дату старше 18 лет, например `"1995-05-15"`, иначе сработает валидация и вернётся ошибка `422`).
5. Нажмите синюю кнопку **`Execute`**.
6. Прокрутите чуть ниже до блока **Server response** — там появится код **`200`** и готовый JSON-ответ с расчётами.

### Пример валидного JSON для `POST /calculator/offers`:
```json
{
  "amount": 100000,
  "term": 12,
  "firstName": "Ivan",
  "lastName": "Ivanov",
  "middleName": "Ivanovich",
  "email": "ivan@example.com",
  "birthdate": "1995-05-15",
  "passportSeries": "1234",
  "passportNumber": "567890"
}
```

### Пример валидного JSON для `POST /calculator/calc`:
```json
{
  "amount": 100000,
  "term": 12,
  "firstName": "Ivan",
  "lastName": "Ivanov",
  "middleName": "Ivanovich",
  "birthdate": "1995-05-15",
  "passportSeries": "1234",
  "passportNumber": "567890",
  "isInsuranceEnabled": true,
  "isSalaryClient": false
}
```

---

## 4. Запуск тестов (шпаргалка)

Запуск всех unit-тестов с проверкой процента покрытия кода (выполнять из корня `credit-conveyor`):

```powershell
.venv\Scripts\python.exe -m pytest --cov=calculator/app calculator/tests
```
