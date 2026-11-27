"""Skrip CLI untuk cek koneksi Supabase, inisialisasi 10 tabel, seed awal, dan hitung jumlah baris."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal, engine, init_db
from app.models.models import (
    AHPVersionCriterion,
    AHPWeightVersion,
    AlleySegment,
    CSVImportBatch,
    CycleRankingResult,
    EvaluationCycle,
    SegmentCriterionValue,
    SegmentObservation,
    User,
    WorklistDecision,
)
from app.seed import seed_database


def _masked_url(raw_url: str) -> str:
    try:
        return make_url(raw_url).render_as_string(hide_password=True)
    except Exception:
        return raw_url


def setup_and_verify(skip_seed: bool = False) -> int:
    """Uji koneksi PostgreSQL, buat tabel yang belum ada, jalankan seeder, lalu cetak jumlah baris."""
    masked = _masked_url(settings.DATABASE_URL)
    dialect = engine.dialect.name
    print(f"[DB Setup] Target dialect : {dialect}")
    print(f"[DB Setup] Target URL     : {masked}")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        print(f"[DB Setup] GAGAL terhubung ke database Supabase: {exc}", file=sys.stderr)
        print(
            "[DB Setup] Pastikan DATABASE_URL di backend/.env mengarah ke Supabase PostgreSQL yang valid.",
            file=sys.stderr,
        )
        return 1

    init_db()
    print("[DB Setup] Skema 10 tabel berhasil dipastikan ada (init_db).")

    if not skip_seed:
        seed_database()
        print("[DB Setup] Seeder idempotent selesai dijalankan.")

    tables = [
        ("users", User),
        ("alley_segments", AlleySegment),
        ("segment_observations", SegmentObservation),
        ("segment_criterion_values", SegmentCriterionValue),
        ("ahp_weight_versions", AHPWeightVersion),
        ("ahp_version_criteria", AHPVersionCriterion),
        ("csv_import_batches", CSVImportBatch),
        ("evaluation_cycles", EvaluationCycle),
        ("cycle_ranking_results", CycleRankingResult),
        ("worklist_decisions", WorklistDecision),
    ]

    with SessionLocal() as db:
        print("\n[DB Setup] Ringkasan jumlah baris per tabel:")
        for table_name, model in tables:
            count = db.scalar(select(func.count()).select_from(model)) or 0
            print(f"  - {table_name:<24} : {count}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inisialisasi dan verifikasi database DSS PJU Jatinangor."
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Lewati pengisian data awal (seed_database).",
    )
    args = parser.parse_args()
    return setup_and_verify(skip_seed=args.no_seed)


if __name__ == "__main__":
    raise SystemExit(main())
