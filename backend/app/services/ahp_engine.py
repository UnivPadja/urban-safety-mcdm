"""Engine pembobotan AHP dinamis (1 sampai 15 kriteria) dan uji konsistensi CR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence

import numpy as np

# Tabel Random Index (RI) Saaty untuk ukuran matriks n = 1..15.
RANDOM_INDEX: dict[int, float] = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}

MIN_CRITERIA = 1
MAX_CRITERIA = 15
CR_THRESHOLD: float = 0.10

CORE_CRITERIA_CODES = ("broken_lights", "dawn_crime_count", "boarding_house_count")

DEFAULT_CRITERIA: list[dict[str, str]] = [
    {"code": "broken_lights", "label": "Kerusakan Lampu PJU", "direction": "max"},
    {"code": "dawn_crime_count", "label": "Curanmor Dini Hari", "direction": "max"},
    {"code": "boarding_house_count", "label": "Kepadatan Indekos", "direction": "max"},
]


@dataclass(frozen=True)
class AHPCriterionWeight:
    code: str
    label: str
    direction: Literal["max", "min"]
    weight: float
    display_order: int


@dataclass(frozen=True)
class AHPResult:
    pairwise_matrix: list[list[float]]
    criteria: list[AHPCriterionWeight]
    weights_map: dict[str, float]
    w_light_damage: float
    w_dawn_crime: float
    w_boarding_density: float
    lambda_max: float
    ci: float
    ri: float
    cr: float
    is_consistent: bool


def resolve_version_criteria(ahp_version: Any) -> list[dict[str, Any]]:
    """Ambil daftar kriteria terurut dari versi AHP, dengan fallback 3 kriteria bawaan untuk data lama."""
    stored = getattr(ahp_version, "criteria", None) or []
    if stored:
        ordered = sorted(stored, key=lambda c: (c.display_order, c.id))
        return [
            {
                "id": c.id,
                "code": c.code,
                "label": c.label,
                "direction": c.direction,
                "weight": float(c.weight),
                "display_order": int(c.display_order),
            }
            for c in ordered
        ]

    # Versi AHP lama sebelum tabel ahp_version_criteria dibuat memakai 3 kolom bobot statis.
    legacy_weights = [
        float(getattr(ahp_version, "w_light_damage", 0.2970)),
        float(getattr(ahp_version, "w_dawn_crime", 0.5396)),
        float(getattr(ahp_version, "w_boarding_density", 0.1634)),
    ]
    return [
        {
            "id": None,
            "code": item["code"],
            "label": item["label"],
            "direction": item["direction"],
            "weight": legacy_weights[idx],
            "display_order": idx,
        }
        for idx, item in enumerate(DEFAULT_CRITERIA)
    ]


def calculate_ahp(
    pairwise_matrix: Sequence[Sequence[float]],
    criteria: Sequence[dict[str, Any]] | None = None,
) -> AHPResult:
    """Hitung bobot prioritas AHP dan Consistency Ratio (CR) untuk matriks NxN (1 <= N <= 15)."""
    matrix = np.asarray(pairwise_matrix, dtype=np.float64)

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Matriks perbandingan berpasangan AHP harus berbentuk persegi (NxN).")

    n = int(matrix.shape[0])
    if n < MIN_CRITERIA or n > MAX_CRITERIA:
        raise ValueError(
            f"Jumlah kriteria AHP harus berada pada rentang {MIN_CRITERIA} hingga {MAX_CRITERIA}."
        )

    if not np.all(np.isfinite(matrix)) or np.any(matrix <= 0.0):
        raise ValueError("Seluruh elemen matriks AHP harus bernilai numerik positif (> 0).")

    for i in range(n):
        if abs(matrix[i, i] - 1.0) > 1e-6:
            raise ValueError(
                f"Elemen diagonal matriks AHP pada posisi ({i + 1}, {i + 1}) harus bernilai 1."
            )
        for j in range(i + 1, n):
            product = matrix[i, j] * matrix[j, i]
            if abs(product - 1.0) > 0.02:
                raise ValueError(
                    f"Elemen matriks pada ({i + 1}, {j + 1}) dan ({j + 1}, {i + 1}) "
                    "harus saling berkebalikan (a_ji = 1 / a_ij)."
                )

    if criteria is None:
        if n == 3:
            resolved_defs = list(DEFAULT_CRITERIA)
        else:
            resolved_defs = [
                {"code": f"c{idx + 1}", "label": f"Kriteria C{idx + 1}", "direction": "max"}
                for idx in range(n)
            ]
    else:
        if len(criteria) != n:
            raise ValueError(
                f"Jumlah definisi kriteria ({len(criteria)}) harus sama dengan ukuran matriks ({n}x{n})."
            )
        resolved_defs = []
        seen_codes: set[str] = set()
        for item in criteria:
            code = str(item["code"]).strip().lower()
            label = str(item["label"]).strip()
            direction = str(item.get("direction", "max")).strip().lower()
            if not code:
                raise ValueError("Kode kriteria tidak boleh kosong.")
            if code in seen_codes:
                raise ValueError(f"Kode kriteria duplikat ditemukan: '{code}'.")
            if direction not in ("max", "min"):
                raise ValueError(
                    f"Arah kriteria '{code}' tidak valid: '{direction}' (gunakan 'max' atau 'min')."
                )
            seen_codes.add(code)
            resolved_defs.append(
                {"code": code, "label": label or code, "direction": direction}
            )

    col_sums = np.sum(matrix, axis=0)
    normalized_matrix = matrix / col_sums
    weights = np.mean(normalized_matrix, axis=1)

    if n <= 2:
        lambda_max = float(n)
        ci = 0.0
        ri = 0.0
        cr = 0.0
        is_consistent = True
    else:
        weighted_sum = matrix @ weights
        lambda_max = float(np.mean(weighted_sum / weights))
        ci = float((lambda_max - float(n)) / float(n - 1))
        if -1e-12 <= ci < 0.0:
            ci = 0.0
        ri = float(RANDOM_INDEX[n])
        cr = float(ci / ri) if ri > 0.0 else 0.0
        is_consistent = bool(cr <= CR_THRESHOLD)

    criteria_weights: list[AHPCriterionWeight] = []
    weights_map: dict[str, float] = {}
    for idx, cdef in enumerate(resolved_defs):
        w_val = float(weights[idx])
        weights_map[cdef["code"]] = w_val
        criteria_weights.append(
            AHPCriterionWeight(
                code=cdef["code"],
                label=cdef["label"],
                direction="min" if cdef["direction"] == "min" else "max",
                weight=w_val,
                display_order=idx,
            )
        )

    return AHPResult(
        pairwise_matrix=[[float(val) for val in row] for row in matrix.tolist()],
        criteria=criteria_weights,
        weights_map=weights_map,
        w_light_damage=float(weights_map.get("broken_lights", 0.0)),
        w_dawn_crime=float(weights_map.get("dawn_crime_count", 0.0)),
        w_boarding_density=float(weights_map.get("boarding_house_count", 0.0)),
        lambda_max=lambda_max,
        ci=ci,
        ri=ri,
        cr=cr,
        is_consistent=is_consistent,
    )
