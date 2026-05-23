# Hotel DWH Service

Сервис для разработанного хранилища данных гостиницы: React-интерфейс + FastAPI backend + PostgreSQL

## Запуск backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Запуск frontend

```bash
cd frontend
npm install
npm run dev
```