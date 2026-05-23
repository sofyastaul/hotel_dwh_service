import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


load_dotenv()


# Формирует параметры подключения к базе данных из переменных окружения
def db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "hotel_diplom"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


# Создаёт подключение к базе данных PostgreSQL
def conn():
    return psycopg2.connect(**db_config())


# Выполняет SQL-запрос на чтение данных и возвращает результат в виде списка словарей
def fetch_all(sql, params=None, limit=500):
    with conn() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params or {})
            rows = cursor.fetchmany(limit)

    return [dict(row) for row in rows]


# Выполняет SQL-запрос на изменение данных и сохраняет изменения в базе
def execute(sql, params=None):
    with conn() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or {})
            connection.commit()