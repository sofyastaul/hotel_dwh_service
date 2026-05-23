from datetime import date, timedelta

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from .db import conn


# Определяет первый и последний день следующего календарного месяца
def next_month_range():
    today = date.today()

    first = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    return first, last


# Формирует ML-прогноз бронирований, загрузки и выручки на следующий месяц
def forecast():
    sql = """
        SELECT
            bd.full_date AS booking_date,
            ad.full_date AS arrival_date,
            dd.full_date AS departure_date,
            b.total_nights,
            b.expected_room_revenue,
            b.booking_status
        FROM f_booking b
        JOIN d_date bd ON bd.date_id = b.booking_date_id
        JOIN d_date ad ON ad.date_id = b.planned_arrival_date_id
        JOIN d_date dd ON dd.date_id = b.planned_departure_date_id
    """

    with conn() as connection:
        df = pd.read_sql(sql, connection)

    if df.empty:
        return {"error": "Недостаточно данных"}

    df["booking_date"] = pd.to_datetime(df["booking_date"])
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    df["departure_date"] = pd.to_datetime(df["departure_date"])

    active = df[df["booking_status"] != "Отменено"].copy()

    monthly = (
        active.groupby(pd.Grouper(key="booking_date", freq="MS"))
        .agg(
            bookings=("booking_date", "size"),
            revenue=("expected_room_revenue", "sum"),
        )
        .reset_index()
    )

    if len(monthly) < 3:
        return {"error": "Для ML-прогноза нужно минимум 3 месяца истории"}

    monthly["month"] = monthly["booking_date"].dt.month
    monthly["t"] = range(len(monthly))

    target_first, target_last = next_month_range()

    next_x = pd.DataFrame(
        {
            "month": [target_first.month],
            "t": [len(monthly)],
        }
    )

    model_bookings = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
    )

    model_revenue = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
    )

    model_bookings.fit(monthly[["month", "t"]], monthly["bookings"])
    model_revenue.fit(monthly[["month", "t"]], monthly["revenue"])

    new_bookings = max(
        0,
        round(float(model_bookings.predict(next_x)[0])),
    )

    possible_revenue = max(
        0,
        float(model_revenue.predict(next_x)[0]),
    )

    future = active[
        (active["arrival_date"].dt.date <= target_last)
        & (active["departure_date"].dt.date > target_first)
    ]

    booked_revenue = float(future["expected_room_revenue"].sum())

    days = (target_last - target_first).days + 1
    capacity = 14 * days
    occupied_room_nights = 0

    for _, row in future.iterrows():
        start = max(row["arrival_date"].date(), target_first)
        end = min(
            row["departure_date"].date(),
            target_last + timedelta(days=1),
        )

        occupied_room_nights += max((end - start).days, 0)

    avg_nights = max(1, round(float(active["total_nights"].mean())))
    available_room_nights = max(capacity - occupied_room_nights, 0)

    predicted_new_room_nights = new_bookings * avg_nights
    realistic_new_room_nights = min(
        predicted_new_room_nights,
        available_room_nights * 0.85,
    )

    occupancy_base = occupied_room_nights / capacity if capacity else 0

    occupancy_forecast = (
        (occupied_room_nights + realistic_new_room_nights) / capacity
        if capacity
        else 0
    )

    occupancy_forecast = min(occupancy_forecast, 0.98)

    return {
        "period": f"{target_first:%Y-%m-%d} - {target_last:%Y-%m-%d}",
        "forecast_new_bookings": int(new_bookings),
        "forecast_occupancy_percent": round(occupancy_forecast * 100, 2),
        "already_booked_occupancy_percent": round(occupancy_base * 100, 2),
        "forecast_lodging_revenue": round(booked_revenue + possible_revenue, 2),
        "already_booked_revenue": round(booked_revenue, 2),
        "model": (
            "RandomForestRegressor по месячной сезонности "
            "и порядковому номеру месяца"
        ),
    }