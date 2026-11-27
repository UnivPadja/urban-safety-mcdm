"""Engine pemeringkatan TOPSIS dinamis dan aturan kelayakan segmen."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Sequence

import numpy as np

from app.models.models import AlleySegment, SegmentObservation
from app.services.ahp_engine import CORE_CRITERIA_CODES


@dataclass(frozen=True)
class TOPSISInputItem:
    segment_id: int
    segment_code: str
    broken_lights: int = 0
    dawn_crime_count: int = 0
    boarding_house_count: int = 0
    criteria_values: dict[str, float] | None = None

    def get_criterion_value(self, code: str) -> float:
        if self.criteria_values is not None and code in self.criteria_values:
            return float(self.criteria_values[code])
        if code == "broken_lights":
            return float(self.broken_lights)
        if code == "dawn_crime_count":
            return float(self.dawn_crime_count)
        if code == "boarding_house_count":
            return float(self.boarding_house_count)
        raise ValueError(
            f"Nilai kriteria '{code}' tidak tersedia untuk segmen '{self.segment_code}'."
        )


@dataclass(frozen=True)
class TOPSISRankedItem:
    segment_id: int
    segment_code: str
    broken_lights: int
    dawn_crime_count: int
    boarding_house_count: int
    norm_c1: float
    norm_c2: float
    norm_c3: float
    weighted_c1: float
    weighted_c2: float
    weighted_c3: float
    d_plus: float
    d_minus: float
    preference_score: float
    rank: int
    is_tie_broken: bool
    normalized_values: dict[str, float] = field(default_factory=dict)
    weighted_values: dict[str, float] = field(default_factory=dict)
    criteria_values: dict[str, float] = field(default_factory=dict)


def build_observation_criteria_map(
    observation: SegmentObservation | None,
) -> dict[str, float | None]:
    """Gabungkan 3 kolom indikator inti dengan nilai kriteria dinamis dari segment_criterion_values."""
    if observation is None:
        return {}
    values: dict[str, float | None] = {
        "broken_lights": float(observation.broken_lights),
        "dawn_crime_count": (
            float(observation.dawn_crime_count)
            if observation.dawn_crime_count is not None
            else None
        ),
        "boarding_house_count": float(observation.boarding_house_count),
    }
    for extra in getattr(observation, "criterion_values", None) or []:
        if extra.criterion_code not in CORE_CRITERIA_CODES:
            values[extra.criterion_code] = (
                float(extra.value) if extra.value is not None else None
            )
    return values


def evaluate_segment_eligibility(
    segment: AlleySegment,
    observation: SegmentObservation | None,
    reference_date: date,
    expiry_days: int,
    required_criteria_codes: Sequence[str] | None = None,
) -> tuple[bool, str | None]:
    """Periksa syarat kelayakan segmen: aktif, observasi belum kedaluwarsa, ada lampu mati, dan kriteria aktif lengkap."""
    if not segment.is_active:
        return False, "Segmen gang berstatus tidak aktif."
    if observation is None:
        return False, "Segmen belum memiliki data observasi lapangan."
    age_days = (reference_date - observation.inspection_date).days
    if age_days > expiry_days:
        return (
            False,
            f"Data observasi kedaluwarsa ({age_days} hari > batas {expiry_days} hari).",
        )
    if observation.dawn_crime_count is None:
        return False, "Data rekap curanmor dini hari belum lengkap (null)."
    if observation.broken_lights <= 0:
        return False, "Tidak ada lampu PJU mati (0 kerusakan)"

    if required_criteria_codes:
        obs_map = build_observation_criteria_map(observation)
        missing_codes = [
            code
            for code in required_criteria_codes
            if code not in CORE_CRITERIA_CODES and obs_map.get(code) is None
        ]
        if missing_codes:
            joined = ", ".join(missing_codes)
            return False, f"Data kriteria dinamis belum lengkap: {joined}."

    return True, None


def get_priority_category(
    is_eligible: bool, preference_score: float | None
) -> str:
    """Petakan skor preferensi TOPSIS ke label kategori prioritas (Tinggi >= 0.66, Sedang >= 0.33, lainnya Rendah)."""
    if not is_eligible or preference_score is None:
        return "Tidak Layak"
    if preference_score >= 0.66:
        return "Tinggi"
    if preference_score >= 0.33:
        return "Sedang"
    return "Rendah"


def _legacy_slot(
    values_by_code: dict[str, float],
    row_array: np.ndarray,
    code: str,
    fallback_idx: int,
) -> float:
    if code in values_by_code:
        return float(values_by_code[code])
    if fallback_idx < len(row_array):
        return float(row_array[fallback_idx])
    return 0.0


def calculate_topsis(
    items: Sequence[TOPSISInputItem],
    weights: Sequence[float],
    criteria_directions: Sequence[Literal["max", "min"]] | None = None,
    criteria_codes: Sequence[str] | None = None,
) -> list[TOPSISRankedItem]:
    """Hitung normalisasi vektor, matriks terbobot, D+, D-, skor preferensi, dan peringkat TOPSIS untuk N kriteria."""
    m = len(items)
    if m == 0:
        return []

    w = np.asarray(weights, dtype=np.float64)
    if w.ndim != 1 or w.shape[0] < 1 or np.any(w < 0.0) or float(np.sum(w)) <= 0.0:
        raise ValueError(
            "Vektor bobot TOPSIS harus terdiri dari minimal 1 nilai non-negatif dengan jumlah > 0."
        )

    k = int(w.shape[0])
    if criteria_codes is None:
        codes = (
            list(CORE_CRITERIA_CODES)
            if k == 3
            else [f"c{idx + 1}" for idx in range(k)]
        )
    else:
        if len(criteria_codes) != k:
            raise ValueError(
                f"Jumlah criteria_codes ({len(criteria_codes)}) harus sama dengan jumlah bobot ({k})."
            )
        codes = list(criteria_codes)

    if criteria_directions is None:
        directions: list[Literal["max", "min"]] = ["max"] * k
    else:
        if len(criteria_directions) != k:
            raise ValueError(
                f"Jumlah criteria_directions ({len(criteria_directions)}) harus sama dengan jumlah bobot ({k})."
            )
        directions = ["min" if d == "min" else "max" for d in criteria_directions]

    X = np.array(
        [[item.get_criterion_value(code) for code in codes] for item in items],
        dtype=np.float64,
    )

    col_norms = np.sqrt(np.sum(X**2, axis=0))
    R = np.zeros_like(X, dtype=np.float64)
    for j in range(k):
        if col_norms[j] > 0.0:
            R[:, j] = X[:, j] / col_norms[j]
        else:
            R[:, j] = 0.0

    V = R * w

    if m == 1:
        item = items[0]
        norm_map = {code: float(R[0, j]) for j, code in enumerate(codes)}
        weight_map = {code: float(V[0, j]) for j, code in enumerate(codes)}
        raw_map = {code: float(X[0, j]) for j, code in enumerate(codes)}
        return [
            TOPSISRankedItem(
                segment_id=item.segment_id,
                segment_code=item.segment_code,
                broken_lights=item.broken_lights,
                dawn_crime_count=item.dawn_crime_count,
                boarding_house_count=item.boarding_house_count,
                norm_c1=_legacy_slot(norm_map, R[0], "broken_lights", 0),
                norm_c2=_legacy_slot(norm_map, R[0], "dawn_crime_count", 1),
                norm_c3=_legacy_slot(norm_map, R[0], "boarding_house_count", 2),
                weighted_c1=_legacy_slot(weight_map, V[0], "broken_lights", 0),
                weighted_c2=_legacy_slot(weight_map, V[0], "dawn_crime_count", 1),
                weighted_c3=_legacy_slot(weight_map, V[0], "boarding_house_count", 2),
                d_plus=0.0,
                d_minus=0.0,
                preference_score=1.0,
                rank=1,
                is_tie_broken=False,
                normalized_values=norm_map,
                weighted_values=weight_map,
                criteria_values=raw_map,
            )
        ]

    a_plus = np.zeros(k, dtype=np.float64)
    a_minus = np.zeros(k, dtype=np.float64)
    for j in range(k):
        if directions[j] == "max":
            a_plus[j] = float(np.max(V[:, j]))
            a_minus[j] = float(np.min(V[:, j]))
        else:
            a_plus[j] = float(np.min(V[:, j]))
            a_minus[j] = float(np.max(V[:, j]))

    d_plus = np.sqrt(np.sum((V - a_plus) ** 2, axis=1))
    d_minus = np.sqrt(np.sum((V - a_minus) ** 2, axis=1))

    denom = d_plus + d_minus
    scores = np.where(denom > 0.0, d_minus / denom, 0.0)

    rounded_counts = Counter(round(float(score), 6) for score in scores)

    preliminary = []
    for idx, item in enumerate(items):
        score_val = float(scores[idx])
        is_tie = rounded_counts[round(score_val, 6)] > 1
        preliminary.append(
            {
                "item": item,
                "raw": X[idx],
                "norm": R[idx],
                "weighted": V[idx],
                "d_plus": float(d_plus[idx]),
                "d_minus": float(d_minus[idx]),
                "score": score_val,
                "is_tie_broken": is_tie,
            }
        )

    # Urutan pemecah seri deterministik: skor preferensi, curanmor, lampu mati, indekos, lalu kode segmen.
    preliminary.sort(
        key=lambda row: (
            -round(row["score"], 6),
            -row["item"].dawn_crime_count,
            -row["item"].broken_lights,
            -row["item"].boarding_house_count,
            row["item"].segment_code,
        )
    )

    ranked_results: list[TOPSISRankedItem] = []
    for rank_idx, row in enumerate(preliminary, start=1):
        item = row["item"]
        norm_map = {code: float(row["norm"][j]) for j, code in enumerate(codes)}
        weight_map = {code: float(row["weighted"][j]) for j, code in enumerate(codes)}
        raw_map = {code: float(row["raw"][j]) for j, code in enumerate(codes)}
        ranked_results.append(
            TOPSISRankedItem(
                segment_id=item.segment_id,
                segment_code=item.segment_code,
                broken_lights=item.broken_lights,
                dawn_crime_count=item.dawn_crime_count,
                boarding_house_count=item.boarding_house_count,
                norm_c1=_legacy_slot(norm_map, row["norm"], "broken_lights", 0),
                norm_c2=_legacy_slot(norm_map, row["norm"], "dawn_crime_count", 1),
                norm_c3=_legacy_slot(norm_map, row["norm"], "boarding_house_count", 2),
                weighted_c1=_legacy_slot(weight_map, row["weighted"], "broken_lights", 0),
                weighted_c2=_legacy_slot(weight_map, row["weighted"], "dawn_crime_count", 1),
                weighted_c3=_legacy_slot(
                    weight_map, row["weighted"], "boarding_house_count", 2
                ),
                d_plus=row["d_plus"],
                d_minus=row["d_minus"],
                preference_score=row["score"],
                rank=rank_idx,
                is_tie_broken=row["is_tie_broken"],
                normalized_values=norm_map,
                weighted_values=weight_map,
                criteria_values=raw_map,
            )
        )
    return ranked_results
