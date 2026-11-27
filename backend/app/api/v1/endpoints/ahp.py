"""Modul 4: Endpoint pembobotan AHP dinamis, uji konsistensi CR, dan manajemen versi."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_optional_user, require_roles
from app.core.database import get_db
from app.models.models import AHPVersionCriterion, AHPWeightVersion, User, UserRole
from app.schemas.schemas import (
    AHPCalculateRequest,
    AHPCalculateResponse,
    AHPCriterionResponse,
    AHPVersionCreateRequest,
    AHPVersionResponse,
    ActiveCriteriaResponse,
)
from app.services.ahp_engine import (
    DEFAULT_CRITERIA,
    calculate_ahp,
    resolve_version_criteria,
)

router = APIRouter(prefix="/ahp", tags=["AHP Weighting"])


def _to_ahp_version_response(version: AHPWeightVersion) -> AHPVersionResponse:
    criteria_dicts = resolve_version_criteria(version)
    criteria_models = [AHPCriterionResponse(**c) for c in criteria_dicts]
    weights_map = {c["code"]: float(c["weight"]) for c in criteria_dicts}
    return AHPVersionResponse(
        id=version.id,
        version_name=version.version_name,
        created_by=version.created_by,
        pairwise_matrix=version.pairwise_matrix,
        criteria=criteria_models,
        weights_map=weights_map,
        w_light_damage=version.w_light_damage,
        w_dawn_crime=version.w_dawn_crime,
        w_boarding_density=version.w_boarding_density,
        lambda_max=version.lambda_max,
        ci=version.ci,
        ri=version.ri,
        cr=version.cr,
        is_consistent=version.is_consistent,
        is_active=version.is_active,
        created_at=version.created_at,
    )


@router.get("/criteria", response_model=ActiveCriteriaResponse)
def get_active_criteria(
    db: Session = Depends(get_db),
    _: User | None = Depends(get_optional_user),
) -> ActiveCriteriaResponse:
    """Ambil daftar kriteria beserta bobot dari versi AHP yang sedang aktif."""
    active_version = db.scalar(
        select(AHPWeightVersion)
        .options(selectinload(AHPWeightVersion.criteria))
        .where(
            AHPWeightVersion.is_active.is_(True),
            AHPWeightVersion.is_consistent.is_(True),
        )
        .order_by(AHPWeightVersion.created_at.desc(), AHPWeightVersion.id.desc())
        .limit(1)
    )
    if active_version is not None:
        criteria_dicts = resolve_version_criteria(active_version)
        return ActiveCriteriaResponse(
            ahp_version_id=active_version.id,
            version_name=active_version.version_name,
            cr=active_version.cr,
            is_consistent=active_version.is_consistent,
            criteria=[AHPCriterionResponse(**c) for c in criteria_dicts],
        )

    fallback_weights = [0.2970, 0.5396, 0.1634]
    return ActiveCriteriaResponse(
        ahp_version_id=None,
        version_name="Default 3 Kriteria Bawaan",
        cr=0.0088,
        is_consistent=True,
        criteria=[
            AHPCriterionResponse(
                id=None,
                code=item["code"],
                label=item["label"],
                direction="max",
                weight=fallback_weights[idx],
                display_order=idx,
            )
            for idx, item in enumerate(DEFAULT_CRITERIA)
        ],
    )


@router.post("/calculate-preview", response_model=AHPCalculateResponse)
def preview_ahp(
    payload: AHPCalculateRequest,
    _: User = Depends(require_roles(UserRole.PENILAI, UserRole.ADMIN)),
) -> AHPCalculateResponse:
    """Hitung pratinjau bobot AHP dan nilai CR untuk matriks NxN tanpa menyimpan ke database."""
    assert payload.pairwise_matrix is not None
    criteria_input = (
        [c.model_dump() for c in payload.criteria] if payload.criteria is not None else None
    )
    try:
        result = calculate_ahp(payload.pairwise_matrix, criteria=criteria_input)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return AHPCalculateResponse(
        pairwise_matrix=result.pairwise_matrix,
        criteria=[
            AHPCriterionResponse(
                id=None,
                code=c.code,
                label=c.label,
                direction=c.direction,
                weight=c.weight,
                display_order=c.display_order,
            )
            for c in result.criteria
        ],
        weights_map=result.weights_map,
        w_light_damage=result.w_light_damage,
        w_dawn_crime=result.w_dawn_crime,
        w_boarding_density=result.w_boarding_density,
        lambda_max=result.lambda_max,
        ci=result.ci,
        ri=result.ri,
        cr=result.cr,
        is_consistent=result.is_consistent,
    )


@router.post(
    "/versions",
    response_model=AHPVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ahp_version(
    payload: AHPVersionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PENILAI, UserRole.ADMIN)),
) -> AHPVersionResponse:
    """Hitung dan simpan versi bobot AHP dinamis (1 sampai 15 kriteria); aktivasi otomatis hanya jika CR <= 0.10."""
    assert payload.pairwise_matrix is not None
    criteria_input = (
        [c.model_dump() for c in payload.criteria] if payload.criteria is not None else None
    )
    try:
        result = calculate_ahp(payload.pairwise_matrix, criteria=criteria_input)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    should_activate = bool(payload.activate_immediately and result.is_consistent)
    if should_activate:
        db.execute(update(AHPWeightVersion).values(is_active=False))

    version = AHPWeightVersion(
        version_name=payload.version_name.strip(),
        created_by=current_user.id,
        pairwise_matrix=result.pairwise_matrix,
        w_light_damage=result.w_light_damage,
        w_dawn_crime=result.w_dawn_crime,
        w_boarding_density=result.w_boarding_density,
        lambda_max=result.lambda_max,
        ci=result.ci,
        ri=result.ri,
        cr=result.cr,
        is_consistent=result.is_consistent,
        is_active=should_activate,
    )
    db.add(version)
    db.flush()

    for c in result.criteria:
        db.add(
            AHPVersionCriterion(
                ahp_version_id=version.id,
                code=c.code,
                label=c.label,
                direction=c.direction,
                weight=c.weight,
                display_order=c.display_order,
            )
        )

    db.commit()
    loaded = db.scalar(
        select(AHPWeightVersion)
        .options(selectinload(AHPWeightVersion.criteria))
        .where(AHPWeightVersion.id == version.id)
    )
    assert loaded is not None
    return _to_ahp_version_response(loaded)


@router.get("/versions", response_model=list[AHPVersionResponse])
def list_ahp_versions(
    db: Session = Depends(get_db),
    _: User | None = Depends(get_optional_user),
) -> list[AHPVersionResponse]:
    """Tampilkan seluruh versi bobot AHP tersimpan dari terbaru ke terlama."""
    versions = db.scalars(
        select(AHPWeightVersion)
        .options(selectinload(AHPWeightVersion.criteria))
        .order_by(AHPWeightVersion.created_at.desc(), AHPWeightVersion.id.desc())
    ).all()
    return [_to_ahp_version_response(v) for v in versions]


@router.patch("/versions/{version_id}/activate", response_model=AHPVersionResponse)
def activate_ahp_version(
    version_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.PENILAI, UserRole.ADMIN)),
) -> AHPVersionResponse:
    """Aktifkan versi bobot AHP yang sudah konsisten (tolak dengan 400 jika CR > 0.10)."""
    version = db.scalar(
        select(AHPWeightVersion)
        .options(selectinload(AHPWeightVersion.criteria))
        .where(AHPWeightVersion.id == version_id)
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Versi bobot AHP dengan ID {version_id} tidak ditemukan.",
        )
    if not version.is_consistent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aktivasi ditolak: Versi bobot '{version.version_name}' tidak konsisten (CR={version.cr:.4f} > 0.10).",
        )

    db.execute(update(AHPWeightVersion).values(is_active=False))
    version.is_active = True
    db.commit()
    db.refresh(version)
    return _to_ahp_version_response(version)
