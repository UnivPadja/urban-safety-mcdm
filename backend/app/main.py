"""Entrypoint utama aplikasi FastAPI, middleware CORS, dan siklus hidup database."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Pastikan skema tabel dan data awal Supabase siap saat aplikasi dijalankan."""
    init_db()
    seed_database()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.1.0",
    description=(
        "REST API Decision Support System (DSS) Prioritas Perbaikan PJU & "
        "Mitigasi Kriminalitas Dini Hari di Kecamatan Jatinangor.\n\n"
        "Fitur utama:\n"
        "- **AHP Dinamis (1–15 kriteria)** dengan tabel Random Index Saaty penuh & uji konsistensi CR <= 0.10.\n"
        "- **TOPSIS Dinamis (benefit/cost)** & live ranking langsung dari Supabase PostgreSQL.\n"
        "- **Pin Point Map** (dukungan GeoJSON Point/LineString/Polygon, perhitungan arc-length midpoint otomatis, "
        "override pin kustom, dan mode `geometry_mode=pin`).\n"
        "- **Autentikasi JWT + RBAC** (endpoint baca bersifat publik/opsional Bearer token; endpoint tulis wajib JWT sesuai peran)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Cek status hidup layanan dan versi API aktif."""
    return {"status": "ok", "service": settings.APP_NAME, "version": app.version}
