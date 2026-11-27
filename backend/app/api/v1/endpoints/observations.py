"""Modul 3: Endpoint pendataan observasi lapangan dan impor CSV dua tahap (staging dan konfirmasi)."""

from datetime import date
import csv
import io
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_optional_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.models import (
    AHPWeightVersion,
    AlleySegment,
    BatchStatus,
    CSVImportBatch,
    DataSourceEnum,
    SegmentCriterionValue,
    SegmentObservation,
    User,
    UserRole,
)
from app.schemas.schemas import (
    CSVConfirmRequest,
    CSVConfirmResponse,
    CSVUploadPreviewResponse,
    CSVValidatedRow,
    ObservationBriefResponse,
    ObservationFormRequest,
    ObservationFormResponse,
    ObservationValidationAlertItem,
    ObservationValidationSummaryResponse,
)
from app.services.ahp_engine import CORE_CRITERIA_CODES, resolve_version_criteria
from app.services.csv_validator import validate_csv_observations
from app.services.topsis_engine import build_observation_criteria_map

router = APIRouter(prefix="/observations", tags=["Observations & CSV Import"])


def _get_active_extra_criteria_codes(db: Session) -> list[str]:
    active_ahp = db.scalar(
        select(AHPWeightVersion)
        .options(selectinload(AHPWeightVersion.criteria))
        .where(
            AHPWeightVersion.is_active.is_(True),
            AHPWeightVersion.is_consistent.is_(True),
        )
        .order_by(AHPWeightVersion.created_at.desc(), AHPWeightVersion.id.desc())
        .limit(1)
    )
    if active_ahp is None:
        return []
    criteria = resolve_version_criteria(active_ahp)
    return [c["code"] for c in criteria if c["code"] not in CORE_CRITERIA_CODES]


def _to_observation_brief(obs: SegmentObservation) -> ObservationBriefResponse:
    return ObservationBriefResponse(
        id=obs.id,
        segment_id=obs.segment_id,
        total_lights=obs.total_lights,
        broken_lights=obs.broken_lights,
        dawn_crime_count=obs.dawn_crime_count,
        boarding_house_count=obs.boarding_house_count,
        criteria_values=build_observation_criteria_map(obs),
        inspection_date=obs.inspection_date,
        data_source=obs.data_source,
        updated_by=obs.updated_by,
        updated_at=obs.updated_at,
    )


def _upsert_observation(
    db: Session,
    segment_id: int,
    total_lights: int,
    broken_lights: int,
    dawn_crime_count: int | None,
    boarding_house_count: int,
    inspection_date: date,
    data_source: DataSourceEnum,
    updated_by: int,
    criteria_values: dict[str, float | None] | None = None,
) -> SegmentObservation:
    obs = db.scalar(
        select(SegmentObservation)
        .options(selectinload(SegmentObservation.criterion_values))
        .where(SegmentObservation.segment_id == segment_id)
    )
    if obs is None:
        obs = SegmentObservation(
            segment_id=segment_id,
            total_lights=total_lights,
            broken_lights=broken_lights,
            dawn_crime_count=dawn_crime_count,
            boarding_house_count=boarding_house_count,
            inspection_date=inspection_date,
            data_source=data_source,
            updated_by=updated_by,
        )
        db.add(obs)
        db.flush()
    else:
        obs.total_lights = total_lights
        obs.broken_lights = broken_lights
        obs.dawn_crime_count = dawn_crime_count
        obs.boarding_house_count = boarding_house_count
        obs.inspection_date = inspection_date
        obs.data_source = data_source
        obs.updated_by = updated_by
        db.flush()

    if criteria_values:
        existing_map = {cv.criterion_code: cv for cv in obs.criterion_values}
        for raw_code, val in criteria_values.items():
            code = str(raw_code).strip().lower()
            if not code or code in CORE_CRITERIA_CODES:
                continue
            numeric_val = float(val) if val is not None else None
            if code in existing_map:
                existing_map[code].value = numeric_val
            else:
                db.add(
                    SegmentCriterionValue(
                        observation_id=obs.id,
                        criterion_code=code,
                        value=numeric_val,
                    )
                )

    return obs


@router.post("/form", response_model=ObservationFormResponse)
def submit_observation_form(
    payload: ObservationFormRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> ObservationFormResponse:
    """Simpan atau perbarui observasi segmen beserta nilai kriteria dinamis melalui form manual."""
    segment: AlleySegment | None = None
    if payload.segment_id is not None:
        segment = db.get(AlleySegment, payload.segment_id)
    elif payload.segment_code is not None:
        code = payload.segment_code.strip().upper()
        segment = db.scalar(
            select(AlleySegment).where(AlleySegment.segment_code == code)
        )

    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UNKNOWN_SEGMENT_CODE: Segmen gang tidak ditemukan.",
        )

    warnings: list[str] = []
    age_days = (date.today() - payload.inspection_date).days
    if age_days > settings.INSPECTION_EXPIRY_DAYS:
        warnings.append(
            f"EXPIRED_INSPECTION_DATE: Tanggal inspeksi sudah berusia {age_days} hari (melebihi {settings.INSPECTION_EXPIRY_DAYS} hari)."
        )
    if payload.dawn_crime_count is None:
        warnings.append(
            "INCOMPLETE_CRIME_DATA: Nilai dawn_crime_count kosong; segmen akan tidak layak evaluasi TOPSIS sampai dilengkapi."
        )

    extra_codes = _get_active_extra_criteria_codes(db)
    obs = _upsert_observation(
        db=db,
        segment_id=segment.id,
        total_lights=payload.total_lights,
        broken_lights=payload.broken_lights,
        dawn_crime_count=payload.dawn_crime_count,
        boarding_house_count=payload.boarding_house_count,
        inspection_date=payload.inspection_date,
        data_source=DataSourceEnum.MANUAL_FORM,
        updated_by=current_user.id,
        criteria_values=payload.criteria_values,
    )
    db.commit()

    loaded_obs = db.scalar(
        select(SegmentObservation)
        .options(selectinload(SegmentObservation.criterion_values))
        .where(SegmentObservation.id == obs.id)
    )
    assert loaded_obs is not None

    if extra_codes:
        obs_map = build_observation_criteria_map(loaded_obs)
        missing_extra = [c for c in extra_codes if obs_map.get(c) is None]
        if missing_extra:
            warnings.append(
                f"INCOMPLETE_CRITERION_DATA: Nilai kriteria dinamis belum dilengkapi ({', '.join(missing_extra)})."
            )

    return ObservationFormResponse(
        observation=_to_observation_brief(loaded_obs),
        warnings=warnings,
    )


@router.post(
    "/upload-csv",
    response_model=CSVUploadPreviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_csv_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> CSVUploadPreviewResponse:
    """Unggah file CSV, jalankan validasi awal (termasuk kriteria dinamis aktif), lalu simpan ke staging."""
    filename = file.filename or "uploaded_observations.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File yang diunggah harus berformat .csv.",
        )

    raw_bytes = await file.read()
    known_codes = set(db.scalars(select(AlleySegment.segment_code)).all())
    extra_codes = _get_active_extra_criteria_codes(db)

    try:
        summary = validate_csv_observations(
            csv_bytes=raw_bytes,
            known_segment_codes=known_codes,
            reference_date=date.today(),
            expiry_days=settings.INSPECTION_EXPIRY_DAYS,
            extra_criteria_codes=extra_codes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    batch = CSVImportBatch(
        uploaded_by=current_user.id,
        filename=filename,
        status=BatchStatus.PENDING_CONFIRMATION,
        rows_payload=summary.rows,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return CSVUploadPreviewResponse(
        batch_id=batch.id,
        filename=batch.filename,
        status=batch.status,
        total_rows=summary.total_rows,
        valid_rows=summary.valid_rows,
        warning_rows=summary.warning_rows,
        error_rows=summary.error_rows,
        rows=[CSVValidatedRow.model_validate(r) for r in summary.rows],
        created_at=batch.created_at,
    )


@router.post("/batches/{batch_id}/confirm", response_model=CSVConfirmResponse)
def confirm_csv_batch(
    batch_id: str,
    payload: CSVConfirmRequest = Body(default_factory=CSVConfirmRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> CSVConfirmResponse:
    """Konfirmasi dan simpan baris valid/terkoreksi dari staging ke segment_observations dan segment_criterion_values."""
    batch = db.get(CSVImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch impor CSV '{batch_id}' tidak ditemukan.",
        )
    if batch.status != BatchStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch '{batch_id}' berstatus {batch.status.value} dan tidak dapat dikonfirmasi lagi.",
        )

    segment_map = {
        seg.segment_code: seg for seg in db.scalars(select(AlleySegment)).all()
    }
    corrections_by_row = {corr.row_number: corr for corr in payload.corrections}
    extra_codes = _get_active_extra_criteria_codes(db)

    rows_to_commit: list[dict[str, Any]] = []
    skipped_error_count = 0
    seen_codes: set[str] = set()
    updated_payload: list[dict[str, Any]] = []

    for row in batch.rows_payload:
        row_num = int(row["row_number"])
        if row_num in corrections_by_row:
            corr = corrections_by_row[row_num]
            code = corr.segment_code.strip().upper()
            if code not in segment_map:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Baris {row_num}: segment_code '{code}' tidak terdaftar.",
                )
            issues: list[dict[str, str]] = []
            age_days = (date.today() - corr.inspection_date).days
            if age_days > settings.INSPECTION_EXPIRY_DAYS:
                issues.append(
                    {
                        "code": "EXPIRED_INSPECTION_DATE",
                        "severity": "WARNING",
                        "message": f"Tanggal inspeksi kedaluwarsa ({age_days} hari).",
                    }
                )
            if corr.dawn_crime_count is None:
                issues.append(
                    {
                        "code": "INCOMPLETE_CRIME_DATA",
                        "severity": "WARNING",
                        "message": "Data curanmor kosong.",
                    }
                )
            merged_criteria = dict(row.get("criteria_values") or {})
            merged_criteria.update(corr.criteria_values)
            for ec in extra_codes:
                if merged_criteria.get(ec) is None:
                    issues.append(
                        {
                            "code": "INCOMPLETE_CRITERION_DATA",
                            "severity": "WARNING",
                            "message": f"Nilai kriteria dinamis '{ec}' kosong.",
                        }
                    )

            row_status = "WARNING" if issues else "VALID"
            normalized_row = {
                "row_number": row_num,
                "segment_code": code,
                "total_lights": corr.total_lights,
                "broken_lights": corr.broken_lights,
                "dawn_crime_count": corr.dawn_crime_count,
                "boarding_house_count": corr.boarding_house_count,
                "criteria_values": merged_criteria,
                "inspection_date": corr.inspection_date.isoformat(),
                "status": row_status,
                "issues": issues,
                "messages": [f"[{i['code']}] {i['message']}" for i in issues],
            }
            updated_payload.append(normalized_row)
            candidate = normalized_row
        else:
            updated_payload.append(row)
            candidate = row

        row_status = candidate["status"]
        if row_status == "ERROR":
            skipped_error_count += 1
            continue
        if row_status == "WARNING" and not payload.include_warnings:
            skipped_error_count += 1
            continue

        code = str(candidate["segment_code"]).strip().upper()
        if code in seen_codes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplikat kode segmen '{code}' saat konfirmasi batch.",
            )
        seen_codes.add(code)
        rows_to_commit.append(candidate)

    committed_codes: list[str] = []
    for item in rows_to_commit:
        code = str(item["segment_code"]).strip().upper()
        segment = segment_map.get(code)
        if segment is None:
            skipped_error_count += 1
            continue
        _upsert_observation(
            db=db,
            segment_id=segment.id,
            total_lights=int(item["total_lights"]),
            broken_lights=int(item["broken_lights"]),
            dawn_crime_count=(
                int(item["dawn_crime_count"])
                if item["dawn_crime_count"] is not None
                else None
            ),
            boarding_house_count=int(item["boarding_house_count"]),
            inspection_date=date.fromisoformat(str(item["inspection_date"])),
            data_source=DataSourceEnum.CSV_IMPORT,
            updated_by=current_user.id,
            criteria_values=item.get("criteria_values") or {},
        )
        committed_codes.append(code)

    batch.rows_payload = updated_payload
    batch.status = BatchStatus.CONFIRMED
    db.commit()

    return CSVConfirmResponse(
        batch_id=batch.id,
        status=batch.status,
        committed_count=len(committed_codes),
        skipped_error_count=skipped_error_count,
        committed_segment_codes=committed_codes,
    )


@router.get("/validation-summary", response_model=ObservationValidationSummaryResponse)
def get_observation_validation_summary(
    db: Session = Depends(get_db),
    _: User | None = Depends(get_optional_user),
) -> ObservationValidationSummaryResponse:
    """Tampilkan ringkasan kelengkapan dan kesegaran data observasi pada seluruh segmen aktif."""
    segments = db.scalars(
        select(AlleySegment)
        .options(
            selectinload(AlleySegment.observation).selectinload(
                SegmentObservation.criterion_values
            )
        )
        .where(AlleySegment.is_active.is_(True))
        .order_by(AlleySegment.segment_code.asc())
    ).all()
    extra_codes = _get_active_extra_criteria_codes(db)

    today = date.today()
    expired_items: list[ObservationValidationAlertItem] = []
    incomplete_items: list[ObservationValidationAlertItem] = []
    missing_items: list[ObservationValidationAlertItem] = []
    complete_and_fresh = 0

    for seg in segments:
        obs = seg.observation
        if obs is None:
            missing_items.append(
                ObservationValidationAlertItem(
                    segment_id=seg.id,
                    segment_code=seg.segment_code,
                    segment_name=seg.name,
                    corridor=seg.corridor,
                    inspection_date=None,
                    reason_code="MISSING_OBSERVATION",
                    message="Belum memiliki data observasi lapangan.",
                )
            )
            continue

        has_issue = False
        age_days = (today - obs.inspection_date).days
        if age_days > settings.INSPECTION_EXPIRY_DAYS:
            has_issue = True
            expired_items.append(
                ObservationValidationAlertItem(
                    segment_id=seg.id,
                    segment_code=seg.segment_code,
                    segment_name=seg.name,
                    corridor=seg.corridor,
                    inspection_date=obs.inspection_date,
                    reason_code="EXPIRED_INSPECTION_DATE",
                    message=f"Inspeksi terakhir {age_days} hari yang lalu (batas {settings.INSPECTION_EXPIRY_DAYS} hari).",
                )
            )
        if obs.dawn_crime_count is None:
            has_issue = True
            incomplete_items.append(
                ObservationValidationAlertItem(
                    segment_id=seg.id,
                    segment_code=seg.segment_code,
                    segment_name=seg.name,
                    corridor=seg.corridor,
                    inspection_date=obs.inspection_date,
                    reason_code="INCOMPLETE_CRIME_DATA",
                    message="Rekap curanmor dini hari belum lengkap.",
                )
            )
        if extra_codes:
            obs_map = build_observation_criteria_map(obs)
            missing_extra = [c for c in extra_codes if obs_map.get(c) is None]
            if missing_extra:
                has_issue = True
                incomplete_items.append(
                    ObservationValidationAlertItem(
                        segment_id=seg.id,
                        segment_code=seg.segment_code,
                        segment_name=seg.name,
                        corridor=seg.corridor,
                        inspection_date=obs.inspection_date,
                        reason_code="INCOMPLETE_CRITERION_DATA",
                        message=f"Nilai kriteria dinamis belum lengkap: {', '.join(missing_extra)}.",
                    )
                )
        if not has_issue:
            complete_and_fresh += 1

    return ObservationValidationSummaryResponse(
        total_segments=len(segments),
        complete_and_fresh_count=complete_and_fresh,
        expired_segments=expired_items,
        incomplete_segments=incomplete_items,
        missing_observation_segments=missing_items,
    )


@router.get(
    "/csv-template",
    responses={
        200: {
            "description": "File template CSV siap unduh mengikuti kriteria AHP aktif.",
            "content": {
                "text/csv": {
                    "example": "segment_code,total_lights,broken_lights,dawn_crime_count,boarding_house_count,inspection_date\nGG-CSK-001,12,6,5,18,2026-11-27\n"
                }
            },
        }
    },
)
def download_csv_template(
    db: Session = Depends(get_db),
    _: User | None = Depends(get_optional_user),
) -> StreamingResponse:
    """Unduh templat CSV dengan kolom yang otomatis menyesuaikan kriteria AHP aktif."""
    extra_codes = _get_active_extra_criteria_codes(db)
    headers = [
        "segment_code",
        "total_lights",
        "broken_lights",
        "dawn_crime_count",
        "boarding_house_count",
        "inspection_date",
        *extra_codes,
    ]
    sample_row: list[Any] = [
        "GG-CSK-001",
        12,
        6,
        5,
        18,
        date.today().isoformat(),
        *[2.5 for _ in extra_codes],
    ]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerow(sample_row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="template_observasi_jatinangor.csv"'
        },
    )


@router.get("/batches/{batch_id}", response_model=CSVUploadPreviewResponse)
def get_csv_batch_preview(
    batch_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> CSVUploadPreviewResponse:
    """Ambil pratinjau hasil validasi batch CSV yang tersimpan di staging."""
    batch = db.get(CSVImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch impor CSV '{batch_id}' tidak ditemukan.",
        )
    rows = batch.rows_payload or []
    return CSVUploadPreviewResponse(
        batch_id=batch.id,
        filename=batch.filename,
        status=batch.status,
        total_rows=len(rows),
        valid_rows=sum(1 for r in rows if r.get("status") == "VALID"),
        warning_rows=sum(1 for r in rows if r.get("status") == "WARNING"),
        error_rows=sum(1 for r in rows if r.get("status") == "ERROR"),
        rows=[CSVValidatedRow.model_validate(r) for r in rows],
        created_at=batch.created_at,
    )


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_csv_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> None:
    """Batalkan batch staging CSV yang masih tertunda sebelum dikonfirmasi."""
    batch = db.get(CSVImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch impor CSV '{batch_id}' tidak ditemukan.",
        )
    if batch.status == BatchStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch yang sudah dikonfirmasi tidak dapat dibatalkan.",
        )
    batch.status = BatchStatus.CANCELLED
    db.commit()
