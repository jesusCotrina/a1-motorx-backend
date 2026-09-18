from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Con SQLite (desarrollo sin PostgreSQL) creamos el esquema al vuelo.
    if settings.is_sqlite:
        from app.db.bootstrap import init_db_dev

        init_db_dev()
    yield


app = FastAPI(
    title="Gestion de Talleres API",
    version="0.1.0",
    description="API para la gestion de talleres (web, demo y app movil).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, object]:
    return {"status": "ok", "demo_mode": settings.demo_mode}
