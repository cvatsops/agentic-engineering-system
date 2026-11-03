
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, Field


DEFAULT_DB = Path("artifacts/url_shortener.db")


class CreateURLRequest(BaseModel):
    original_url: HttpUrl


class CreateURLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int


def create_app(db_path: str | Path = DEFAULT_DB) -> FastAPI:
    app = FastAPI(
        title="Agentic Engineering URL Shortener",
        version="0.1.0",
        description="URL shortening service with basic click analytics.",
    )

    database = str(db_path)

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(database, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database() -> None:
        Path(database).parent.mkdir(parents=True, exist_ok=True)

        with closing(connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    short_code TEXT PRIMARY KEY,
                    original_url TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT
                        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                );

                CREATE TABLE IF NOT EXISTS click_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    short_code TEXT NOT NULL,
                    clicked_at TEXT NOT NULL DEFAULT
                        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (short_code)
                        REFERENCES urls(short_code)
                );

                CREATE INDEX IF NOT EXISTS idx_click_events_code
                ON click_events(short_code);
                """
            )
            conn.commit()

    @app.on_event("startup")
    def startup() -> None:
        initialize_database()

    @app.get("/health")
    def health() -> dict[str, str]:
        try:
            with closing(connect()) as conn:
                conn.execute("SELECT 1").fetchone()
            return {"status": "healthy"}
        except sqlite3.Error as exc:
            raise HTTPException(
                status_code=503,
                detail="Database unavailable",
            ) from exc

    @app.post("/urls", response_model=CreateURLResponse, status_code=201)
    def create_url(request: CreateURLRequest) -> CreateURLResponse:
        original_url = str(request.original_url)

        # Bounded attempts protect against the extremely rare
        # short-code collision.
        for _ in range(5):
            short_code = secrets.token_urlsafe(6)

            try:
                with closing(connect()) as conn:
                    conn.execute(
                        """
                        INSERT INTO urls (short_code, original_url)
                        VALUES (?, ?)
                        """,
                        (short_code, original_url),
                    )
                    conn.commit()

                return CreateURLResponse(
                    short_code=short_code,
                    short_url=f"/{short_code}",
                    original_url=original_url,
                )
            except sqlite3.IntegrityError:
                continue

        raise HTTPException(
            status_code=503,
            detail="Could not allocate a unique short code",
        )

    @app.get("/{short_code}")
    def redirect_url(short_code: str) -> RedirectResponse:
        with closing(connect()) as conn:
            row = conn.execute(
                "SELECT original_url FROM urls WHERE short_code = ?",
                (short_code,),
            ).fetchone()

            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail="Short URL not found",
                )

            # Record the click before redirecting.
            conn.execute(
                "INSERT INTO click_events (short_code) VALUES (?)",
                (short_code,),
            )
            conn.commit()

        return RedirectResponse(
            url=row["original_url"],
            status_code=307,
        )

    @app.get(
        "/urls/{short_code}/analytics",
        response_model=AnalyticsResponse,
    )
    def get_analytics(short_code: str) -> AnalyticsResponse:
        with closing(connect()) as conn:
            row = conn.execute(
                """
                SELECT u.original_url, COUNT(c.id) AS click_count
                FROM urls u
                LEFT JOIN click_events c
                    ON c.short_code = u.short_code
                WHERE u.short_code = ?
                GROUP BY u.short_code, u.original_url
                """,
                (short_code,),
            ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Short URL not found",
            )

        return AnalyticsResponse(
            short_code=short_code,
            original_url=row["original_url"],
            click_count=row["click_count"],
        )

    return app


app = create_app()