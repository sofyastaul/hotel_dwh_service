import os
import sys
import importlib.util
from datetime import datetime, timedelta

import pandas as pd

from .db import conn, execute


# Создаёт служебную таблицу для хранения состояния ETL-загрузок
def ensure_state():
    execute(
        """
        CREATE TABLE IF NOT EXISTS etl_sync_state (
            source_name varchar(50) PRIMARY KEY,
            last_success_at timestamp,
            last_loaded_from timestamp,
            last_loaded_to timestamp,
            rows_loaded integer DEFAULT 0,
            status varchar(30),
            message text
        )
        """
    )


# Получает дату окончания последней успешной загрузки по указанному источнику
def get_last(source):
    ensure_state()

    with conn() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT last_loaded_to
                FROM etl_sync_state
                WHERE source_name = %s
                """,
                (source,),
            )

            result = cursor.fetchone()

    return result[0] if result and result[0] else None


# Сохраняет информацию о результате последней ETL-загрузки
def set_state(source, start, end, rows, status="success", message=""):
    execute(
        """
        INSERT INTO etl_sync_state (
            source_name,
            last_success_at,
            last_loaded_from,
            last_loaded_to,
            rows_loaded,
            status,
            message
        )
        VALUES (%s, now(), %s, %s, %s, %s, %s)
        ON CONFLICT (source_name)
        DO UPDATE SET
            last_success_at = excluded.last_success_at,
            last_loaded_from = excluded.last_loaded_from,
            last_loaded_to = excluded.last_loaded_to,
            rows_loaded = excluded.rows_loaded,
            status = excluded.status,
            message = excluded.message
        """,
        (source, start, end, rows, status, message),
    )


# Загружает внешний ETL-скрипт практика.py и передаёт в него параметры окружения
def load_practice():
    path = os.getenv("PRACTICE_PY_PATH", "../практика.py")

    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(os.getcwd(), path))

    if not os.path.exists(path):
        raise RuntimeError(f"Файл практика.py не найден: {path}")

    spec = importlib.util.spec_from_file_location("practice_loader", path)
    module = importlib.util.module_from_spec(spec)

    sys.modules["practice_loader"] = module
    spec.loader.exec_module(module)

    module.RECREATE_TABLES = False

    module.DB_CONFIG.update(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "hotel_diplom"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )

    for name in [
        "PMS_TOKEN",
        "AMO_BASE_URL",
        "AMO_LONG_LIVED_TOKEN",
        "YOUGILE_TOKEN",
    ]:
        if os.getenv(name):
            setattr(module, name, os.getenv(name))

    module.CURRENT_DATE = module.get_current_datetime()

    return module


# Выполняет инкрементальную загрузку данных из PMS, amoCRM и YouGile в хранилище
def run_incremental():
    practice = load_practice()

    start = get_last("all_sources") or (datetime.now() - timedelta(days=14))
    start = start - timedelta(days=2)
    end = datetime.now()

    practice.PMS_DATE_FROM = start.strftime("%Y-%m-%dT00:00:00.000Z")
    practice.PMS_DATE_TO = end.strftime("%Y-%m-%dT23:59:59.000Z")
    practice.PMS_SKIP_FIRST = 0

    bookings_df, finance_df = practice.load_pms_data()
    contacts_df = practice.load_amo_contacts()

    cleaning_df, maintenance_df, food_df = practice.load_yougile_tasks()

    connection = practice.get_conn()

    try:
        practice.create_schema(connection)
        practice.upsert_static_dimensions(connection)

        all_dates = practice.build_dates_from_sources(
            bookings_df,
            finance_df,
            cleaning_df,
            maintenance_df,
            food_df,
        )

        practice.upsert_dates(connection, all_dates)
        practice.upsert_guests(connection, contacts_df, bookings_df)

        maps = practice.fetch_id_maps(connection)
        practice.load_f_booking(connection, bookings_df, maps)

        practice.load_f_stay(connection, bookings_df)

        maps = practice.fetch_id_maps(connection)
        practice.load_f_payment(connection, finance_df, maps)

        maps = practice.fetch_id_maps(connection)
        practice.load_f_room_operation(
            connection,
            cleaning_df,
            maintenance_df,
            maps,
        )

        maps = practice.fetch_id_maps(connection)
        practice.load_f_service_order(connection, food_df, maps)

    finally:
        connection.close()

    rows = sum(
        len(dataframe)
        for dataframe in [
            bookings_df,
            finance_df,
            contacts_df,
            cleaning_df,
            maintenance_df,
            food_df,
        ]
        if isinstance(dataframe, pd.DataFrame)
    )

    set_state("all_sources", start, end, rows)

    return {
        "loaded_rows": rows,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "algorithm": (
            "инкрементальное окно от последней успешной загрузки минус 2 дня; "
            "в фактах используется upsert по бизнес-ключам"
        ),
    }