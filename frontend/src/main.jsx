import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Download, RefreshCw, Filter } from "lucide-react";

import "./style.css";

const API = "http://127.0.0.1:8000";

function App() {
    const [token, setToken] = useState(localStorage.getItem("token") || "");
    const [page, setPage] = useState("forecast");
    const [rows, setRows] = useState([]);
    const [msg, setMsg] = useState("");
    const [forecast, setForecast] = useState(null);
    const [loginError, setLoginError] = useState("");

    const [login, setLogin] = useState({
        username: "admin",
        password: "admin123",
    });

    const headers = {
        Authorization: "Bearer " + token,
    };

    // Выполняет авторизацию пользователя
    async function auth() {
        setLoginError("");

        try {
            const response = await fetch(API + "/api/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(login),
            });

            const result = await response.json();

            if (!response.ok) {
                setLoginError(result.detail || "Неверный логин или пароль");
                return;
            }

            if (result.access_token) {
                localStorage.setItem("token", result.access_token);
                setToken(result.access_token);
                return;
            }

            setLoginError("Не удалось получить токен доступа");
        } catch {
            setLoginError("Не удалось подключиться к серверу");
        }
    }

    // Загружает выбранную страницу сервиса
    async function load(p = page) {
        setPage(p);
        setRows([]);
        setMsg("");
        setForecast(null);

        if (p === "forecast") {
            const response = await fetch(API + "/api/forecast", {
                headers,
            });

            setForecast(await response.json());
            return;
        }

        const url = p.startsWith("f_")
            ? "/api/facts/" + p
            : "/api/marts/" + p;

        const response = await fetch(API + url, {
            headers,
        });

        setRows(await response.json());
    }

    // Запускает инкрементальную ETL-загрузку новых данных
    async function etl() {
        if (
            !confirm(
                "Загрузить новые/измененные данные из PMS, amoCRM и YouGile?"
            )
        ) {
            return;
        }

        setMsg("Идет загрузка...");

        const response = await fetch(API + "/api/etl/incremental", {
            method: "POST",
            headers,
        });

        setMsg(JSON.stringify(await response.json(), null, 2));
    }

    // Скачивает выбранную витрину в формате Excel
    async function xlsx(name) {
        const response = await fetch(API + "/api/marts/" + name + "/xlsx", {
            headers,
        });

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const fileNames = {
            booking: "dm_booking_pipeline.xlsx",
            finance: "dm_daily_revenue_performance.xlsx",
            operations: "dm_operations_service_execution.xlsx",
        };

        const link = document.createElement("a");
        link.href = url;
        link.download = fileNames[name] || name + "_mart.xlsx";
        link.click();

        URL.revokeObjectURL(url);
    }

    // Открывает встроенный Power BI дашборд
    function openDashboard(p) {
        setPage(p);
        setRows([]);
        setMsg("");
        setForecast(null);
    }

    useEffect(() => {
        if (token) {
            load("forecast");
        }
    }, [token]);

    if (!token) {
        return (
            <div className="login">
                <h1>Hotel DWH Service</h1>

                <input
                    placeholder="Логин"
                    value={login.username}
                    onChange={(event) =>
                        setLogin({
                            ...login,
                            username: event.target.value,
                        })
                    }
                />

                <input
                    placeholder="Пароль"
                    type="password"
                    value={login.password}
                    onChange={(event) =>
                        setLogin({
                            ...login,
                            password: event.target.value,
                        })
                    }
                />

                <button onClick={auth}>Войти</button>

                {loginError && (
                    <div className="loginError">
                        {loginError}
                    </div>
                )}
            </div>
        );
    }

    const fact = [
        "f_booking",
        "f_stay",
        "f_payment",
        "f_room_operation",
        "f_service_order",
    ];

    const marts = [
        ["booking", "Витрина коммерческой воронки бронирований"],
        ["finance", "Витрина ежедневной доходности и загрузки"],
        ["operations", "Витрина операционного исполнения"],
    ];

    const titles = {
        forecast: "Прогнозы ML",
        booking: "Витрина коммерческой воронки бронирований",
        finance: "Витрина ежедневной доходности и загрузки",
        operations: "Витрина операционного исполнения",
        dash1: "Дашборд: коммерция",
        dash2: "Дашборд: операции",
        f_booking: "Факт бронирований",
        f_stay: "Факт проживаний",
        f_payment: "Факт оплат",
        f_room_operation: "Факт операций по номерам",
        f_service_order: "Факт услуг",
    };

    const forecastLabels = {
        period: "Период прогноза",
        forecast_new_bookings: "Прогноз новых бронирований, шт.",
        forecast_occupancy_percent: "Прогноз загрузки отеля, %",
        already_booked_occupancy_percent: "Уже забронированная загрузка, %",
        forecast_lodging_revenue: "Прогноз выручки от проживаний, руб.",
        already_booked_revenue: "Уже забронированная выручка, руб.",
        model: "Метод расчета",
    };

    return (
        <>
            <aside>
                <h2>Hotel DWH</h2>

                <button onClick={() => load("forecast")}>
                    Прогнозы ML
                </button>

                <button onClick={etl}>
                    <RefreshCw size={16} />
                    Загрузить новые данные
                </button>

                <h3>Факты</h3>

                {fact.map((f) => (
                    <button key={f} onClick={() => load(f)}>
                        {titles[f]}
                    </button>
                ))}

                <h3>Витрины</h3>

                {marts.map((m) => (
                    <button key={m[0]} onClick={() => load(m[0])}>
                        {m[1]}
                    </button>
                ))}

                <h3>Дашборды</h3>

                <button onClick={() => openDashboard("dash1")}>
                    Коммерция
                </button>

                <button onClick={() => openDashboard("dash2")}>
                    Операции
                </button>
            </aside>

            <main>
                <h1>{titles[page] || page}</h1>

                {msg && <pre>{msg}</pre>}

                {page === "forecast" && forecast && (
                    <>
                        <p className="hint">
                            На этой странице показан прогноз на следующий
                            календарный месяц. Новые бронирования измеряются
                            в штуках, загрузка — в процентах от доступного
                            номерного фонда, выручка — в рублях. Прогноз
                            выручки учитывает уже существующие бронирования
                            и ожидаемый вклад будущих новых бронирований.
                        </p>

                        <div className="cards">
                            {Object.entries(forecast).map(([key, value]) => (
                                <div className="card" key={key}>
                                    <b>{forecastLabels[key] || key}</b>
                                    <span>{String(value)}</span>
                                </div>
                            ))}
                        </div>
                    </>
                )}

                {["booking", "finance", "operations"].includes(page) && (
                    <button className="export" onClick={() => xlsx(page)}>
                        <Download size={16} />
                        Скачать XLSX
                    </button>
                )}

                {page === "dash1" && (
                    <iframe
                        title="Коммерция"
                        width="1024"
                        height="804"
                        src="https://app.powerbi.com/view?r=eyJrIjoiMDk3ZmRlOTYtYWUzZS00YWNhLThlYzAtOGJmYTk2OGFiZjYyIiwidCI6IjVmMzQyYTBhLWE0ZDAtNDZhNi1hYjRmLTcxMDcyOTI2YzUxMiJ9&pageName=92908817c575ad360cc5"
                    />
                )}

                {page === "dash2" && (
                    <iframe
                        title="Операции"
                        width="1024"
                        height="804"
                        src="https://app.powerbi.com/view?r=eyJrIjoiMDk3ZmRlOTYtYWUzZS00YWNhLThlYzAtOGJmYTk2OGFiZjYyIiwidCI6IjVmMzQyYTBhLWE0ZDAtNDZhNi1hYjRmLTcxMDcyOTI2YzUxMiJ9&pageName=4392029cba9d732939ee"
                    />
                )}

                {rows.length > 0 && <Table rows={rows} />}
            </main>
        </>
    );
}

function txt(value) {
    return String(value ?? "");
}

function compare(a, b) {
    const av = a ?? "";
    const bv = b ?? "";

    const an = Number(av);
    const bn = Number(bv);

    if (
        av !== "" &&
        bv !== "" &&
        !Number.isNaN(an) &&
        !Number.isNaN(bn)
    ) {
        return an - bn;
    }

    const ad = Date.parse(av);
    const bd = Date.parse(bv);

    if (!Number.isNaN(ad) && !Number.isNaN(bd)) {
        return ad - bd;
    }

    return txt(av).localeCompare(txt(bv), "ru", {
        numeric: true,
        sensitivity: "base",
    });
}

function Table({ rows }) {
    const cols = Object.keys(rows[0] || {});

    const [sort, setSort] = useState({
        col: null,
        dir: "asc",
    });

    const [filters, setFilters] = useState({});
    const [open, setOpen] = useState(null);

    const unique = useMemo(
        () =>
            Object.fromEntries(
                cols.map((col) => [
                    col,
                    [...new Set(rows.map((row) => txt(row[col] ?? "")))]
                        .filter((value) => value !== "")
                        .sort((a, b) =>
                            a.localeCompare(b, "ru", {
                                numeric: true,
                            })
                        ),
                ])
            ),
        [rows, cols]
    );

    function sortBy(col) {
        setSort((current) =>
            current.col === col
                ? {
                      col,
                      dir: current.dir === "asc" ? "desc" : "asc",
                  }
                : {
                      col,
                      dir: "asc",
                  }
        );
    }

    function allowed(col) {
        return unique[col].length > 0 && unique[col].length < 10;
    }

    function chosen(col) {
        return filters[col] || new Set(unique[col]);
    }

    function setAll(col, on) {
        setFilters((current) => ({
            ...current,
            [col]: on ? new Set(unique[col]) : new Set(),
        }));
    }

    function toggle(col, value) {
        setFilters((current) => {
            const selected = new Set(chosen(col));

            if (selected.has(value)) {
                selected.delete(value);
            } else {
                selected.add(value);
            }

            return {
                ...current,
                [col]: selected,
            };
        });
    }

    function openFilter(col, event) {
        const rect = event.currentTarget.getBoundingClientRect();

        setOpen((current) =>
            current && current.col === col
                ? null
                : {
                      col,
                      x: rect.left,
                      y: rect.bottom + 6,
                  }
        );
    }

    const data = useMemo(() => {
        let result = rows.filter((row) =>
            cols.every(
                (col) =>
                    !allowed(col) ||
                    chosen(col).has(txt(row[col] ?? ""))
            )
        );

        if (sort.col) {
            result = [...result].sort(
                (a, b) =>
                    compare(a[sort.col], b[sort.col]) *
                    (sort.dir === "asc" ? 1 : -1)
            );
        }

        return result;
    }, [rows, filters, sort, unique]);

    return (
        <div className="tableBlock">
            <div className="tableTools">
                <span>
                    Показано: {data.length} из {rows.length}
                </span>

                <span>
                    Сортировка: нажмите на название столбца
                </span>
            </div>

            <div className="table">
                <table>
                    <thead>
                        <tr>
                            {cols.map((col) => (
                                <th key={col}>
                                    <div className="thBox">
                                        <button
                                            className="thName"
                                            onClick={() => sortBy(col)}
                                            title="Сортировать"
                                        >
                                            {col}{" "}
                                            <span>
                                                {sort.col === col
                                                    ? sort.dir === "asc"
                                                        ? "▲"
                                                        : "▼"
                                                    : "↕"}
                                            </span>
                                        </button>

                                        {allowed(col) && (
                                            <button
                                                className="filterBtn"
                                                onClick={(event) =>
                                                    openFilter(col, event)
                                                }
                                                title="Фильтр"
                                            >
                                                <Filter size={14} />
                                            </button>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>

                    <tbody>
                        {data.map((row, index) => (
                            <tr key={index}>
                                {cols.map((col) => (
                                    <td key={col}>{txt(row[col])}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {open && (
                <div
                    className="filterBackdrop"
                    onClick={() => setOpen(null)}
                >
                    <div
                        className="filterMenu"
                        style={{
                            left: open.x,
                            top: open.y,
                        }}
                        onClick={(event) => event.stopPropagation()}
                    >
                        <label>
                            <input
                                type="checkbox"
                                checked={
                                    chosen(open.col).size ===
                                    unique[open.col].length
                                }
                                onChange={(event) =>
                                    setAll(open.col, event.target.checked)
                                }
                            />
                            Все
                        </label>

                        {unique[open.col].map((value) => (
                            <label key={value}>
                                <input
                                    type="checkbox"
                                    checked={chosen(open.col).has(value)}
                                    onChange={() =>
                                        toggle(open.col, value)
                                    }
                                />
                                {value}
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

createRoot(document.getElementById("root")).render(<App />);