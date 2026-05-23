# Содержит SQL-скрипт создания аналитических витрин для различных подразделений гостиницы
VIEW_SQL = r"""
CREATE OR REPLACE VIEW mart_booking_department AS
SELECT
    b.booking_id,
    bd.full_date AS booking_date,
    ad.full_date AS planned_arrival_date,
    dd.full_date AS planned_departure_date,

    b.booking_status,

    g.full_name AS guest_name,
    g.phone AS guest_phone,
    g.email AS guest_email,
    g.country AS guest_country,
    g.is_repeated_guest,
    g.loyalty_level,

    r.room_number,
    r.room_type_name,
    r.room_category,

    b.no_of_guests,

    rp.rate_plan_name,
    mp.meal_plan_name,

    ms.booking_channel,
    ms.commission_percent,

    e.full_name AS responsible_employee,

    b.total_nights,
    b.no_of_week_nights,
    b.no_of_weekend_nights,
    b.lead_time,

    b.expected_room_revenue,

    ROUND(
        b.expected_room_revenue
        * COALESCE(ms.commission_percent, 0) / 100,
        2
    ) AS estimated_commission_amount,

    ROUND(
        b.expected_room_revenue
        * (1 - COALESCE(ms.commission_percent, 0) / 100),
        2
    ) AS expected_net_revenue

FROM f_booking b

JOIN d_date bd
    ON bd.date_id = b.booking_date_id

JOIN d_date ad
    ON ad.date_id = b.planned_arrival_date_id

JOIN d_date dd
    ON dd.date_id = b.planned_departure_date_id

JOIN d_guest g
    ON g.guest_id = b.guest_id

JOIN d_room r
    ON r.room_id = b.room_id

JOIN d_market_segment ms
    ON ms.market_segment_id = b.market_segment_id

LEFT JOIN d_rate_plan rp
    ON rp.rate_plan_id = b.rate_plan_id

LEFT JOIN d_meal_plan mp
    ON mp.meal_plan_id = b.meal_plan_id

LEFT JOIN d_employee e
    ON e.employee_id = b.responsible_id;


CREATE OR REPLACE VIEW mart_finance_department AS
SELECT
    *
FROM f_payment;


CREATE OR REPLACE VIEW mart_operations_department AS
SELECT
    *
FROM f_room_operation;
"""