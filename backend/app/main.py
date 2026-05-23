import io
import os

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .db import conn, fetch_all
from .etl_incremental import ensure_state, run_incremental
from .forecast import forecast
from .security import create_token, verify_token


app = FastAPI(title="Hotel DWH Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MART_TABLES = {
    "booking": "dm.dm_booking_pipeline",
    "finance": "dm.dm_daily_revenue_performance",
    "operations": "dm.dm_operations_service_execution",
}

MART_FILENAMES = {
    "booking": "dm_booking_pipeline.xlsx",
    "finance": "dm_daily_revenue_performance.xlsx",
    "operations": "dm_operations_service_execution.xlsx",
}


class Login(BaseModel):
    username: str
    password: str


# Выполняет начальную настройку сервиса при запуске приложения
@app.on_event("startup")
def startup():
    ensure_state()


# Проверяет логин и пароль пользователя и возвращает токен доступа
@app.post("/api/login")
def login(data: Login):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    if data.username == admin_username and data.password == admin_password:
        return {"access_token": create_token(data.username)}

    raise HTTPException(
        status_code=401,
        detail="Неверный логин или пароль",
    )


# Возвращает данные выбранной таблицы фактов из центрального хранилища данных
@app.get("/api/facts/{table}")
def facts(table: str, user=Depends(verify_token)):
    allowed_tables = {
        "f_booking",
        "f_stay",
        "f_payment",
        "f_room_operation",
        "f_service_order",
    }

    if table not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail="Недоступная таблица",
        )

    return fetch_all(
        f"SELECT * FROM public.{table} ORDER BY 1 DESC",
        limit=1000,
    )


# Возвращает данные выбранной витрины из схемы dm
@app.get("/api/marts/{name}")
def marts(name: str, user=Depends(verify_token)):
    if name not in MART_TABLES:
        raise HTTPException(
            status_code=400,
            detail="Недоступная витрина",
        )

    return fetch_all(
        f"SELECT * FROM {MART_TABLES[name]} LIMIT 5000",
        limit=5000,
    )


# Формирует Excel-файл с данными выбранной витрины из схемы dm
@app.get("/api/marts/{name}/xlsx")
def mart_xlsx(name: str, user=Depends(verify_token)):
    if name not in MART_TABLES:
        raise HTTPException(
            status_code=400,
            detail="Недоступная витрина",
        )

    with conn() as connection:
        df = pd.read_sql(
            f"SELECT * FROM {MART_TABLES[name]}",
            connection,
        )

    buffer = io.BytesIO()

    df.to_excel(
        buffer,
        index=False,
        engine="openpyxl",
    )

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f"attachment; filename={MART_FILENAMES[name]}"
        },
    )


# Запускает инкрементальную загрузку новых и изменённых данных в хранилище
@app.post("/api/etl/incremental")
def incremental(user=Depends(verify_token)):
    return run_incremental()


# Возвращает текущее состояние последней ETL-загрузки
@app.get("/api/etl/state")
def etl_state(user=Depends(verify_token)):
    return fetch_all(
        "SELECT * FROM etl_sync_state ORDER BY source_name",
        limit=20,
    )


# Возвращает прогноз ключевых показателей гостиницы на следующий месяц
@app.get("/api/forecast")
def forecast_api(user=Depends(verify_token)):
    return forecast()


# Проверяет доступность backend-сервиса
@app.get("/api/health")
def health():
    return {"status": "ok"}
