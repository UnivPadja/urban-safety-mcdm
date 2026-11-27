"""Skema validasi request dan response Pydantic v2 untuk seluruh modul DSS."""

from datetime import date, datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.models import (
    BatchStatus,
    CorridorEnum,
    CycleStatus,
    DataSourceEnum,
    UserRole,
)
from app.services.ahp_engine import MAX_CRITERIA, MIN_CRITERIA

_CRITERION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,49}$")


def _validate_position(pos: Any) -> None:
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        raise ValueError(
            "Setiap titik koordinat GeoJSON harus berupa array [longitude, latitude]."
        )
    lon, lat = pos[0], pos[1]
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        raise ValueError("Koordinat longitude dan latitude harus berupa angka.")
    if not (-180.0 <= float(lon) <= 180.0) or not (-90.0 <= float(lat) <= 90.0):
        raise ValueError(
            "Koordinat berada di luar rentang valid bumi (lon: [-180,180], lat: [-90,90])."
        )


class PinPoint(BaseModel):
    """Koordinat titik pin representatif segmen dalam format WGS84 (lat/lon)."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"lat": -6.933572, "lon": 107.775454}}
    )

    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude WGS84")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude WGS84")


class GeoJSONGeometry(BaseModel):
    """Geometri GeoJSON yang menerima tipe Point, LineString, atau Polygon."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "LineString",
                "coordinates": [
                    [107.775007, -6.932916],
                    [107.77543, -6.933538],
                    [107.775691, -6.934223],
                ],
            }
        }
    )

    type: Literal["Point", "LineString", "Polygon"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def validate_coordinates(self) -> "GeoJSONGeometry":
        if self.type == "Point":
            _validate_position(self.coordinates)
        elif self.type == "LineString":
            if len(self.coordinates) < 2:
                raise ValueError(
                    "Geometri LineString wajib memiliki minimal 2 titik koordinat."
                )
            for pt in self.coordinates:
                _validate_position(pt)
        elif self.type == "Polygon":
            if len(self.coordinates) < 1:
                raise ValueError(
                    "Geometri Polygon wajib memiliki minimal 1 ring koordinat."
                )
            for ring in self.coordinates:
                if not isinstance(ring, list) or len(ring) < 4:
                    raise ValueError(
                        "Setiap ring Polygon wajib memiliki minimal 4 titik koordinat."
                    )
                for pt in ring:
                    _validate_position(pt)
                if ring[0][:2] != ring[-1][:2]:
                    raise ValueError(
                        "Ring Polygon wajib tertutup (titik awal sama dengan titik akhir)."
                    )
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "penilai", "password": "penilai123"}}
    )

    username: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    password: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def require_username_or_email(self) -> "LoginRequest":
        if not (self.username and self.username.strip()) and not self.email:
            raise ValueError("Harap isi username atau email untuk login.")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "operator_ciseke",
                "email": "operator.ciseke@jatinangor-dss.id",
                "full_name": "Operator Lapangan Ciseke",
                "password": "password123",
                "role": "OPERATOR",
                "is_active": True,
            }
        }
    )

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class ObservationBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_id: int
    total_lights: int
    broken_lights: int
    dawn_crime_count: int | None
    boarding_house_count: int
    criteria_values: dict[str, float | None] = Field(default_factory=dict)
    inspection_date: date
    data_source: DataSourceEnum
    updated_by: int
    updated_at: datetime


class SegmentCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "segment_code": "GG-CSK-004",
                "name": "Gang Ciseke Masjid Al-Ikhlas",
                "corridor": "Ciseke",
                "geojson_geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [107.7751, -6.9331],
                        [107.7754, -6.9335],
                        [107.7757, -6.9339],
                    ],
                },
                "pin_point": {"lat": -6.9335, "lon": 107.7754},
                "is_active": True,
            }
        }
    )

    segment_code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=200)
    corridor: CorridorEnum
    geojson_geometry: GeoJSONGeometry
    pin_point: PinPoint | None = Field(
        default=None,
        description="Koordinat pin kustom opsional; jika dikosongkan dihitung otomatis dari geojson_geometry.",
    )
    is_active: bool = True

    @field_validator("segment_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class SegmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    corridor: CorridorEnum | None = None
    geojson_geometry: GeoJSONGeometry | None = None
    pin_point: PinPoint | None = Field(
        default=None,
        description="Koordinat pin kustom opsional; set null bersama clear_pin_point=true untuk kembali ke titik tengah otomatis.",
    )
    clear_pin_point: bool = Field(
        default=False,
        description="Jika true, menghapus pin_point kustom dan menghitung ulang dari geometri.",
    )
    is_active: bool | None = None


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_code: str
    name: str
    corridor: CorridorEnum
    geojson_geometry: dict[str, Any]
    pin_point: PinPoint | None = None
    pin_point_source: Literal["custom", "computed"] = "computed"
    is_active: bool
    updated_at: datetime
    has_geometry: bool = True
    last_inspection_date: date | None = None
    observation: ObservationBriefResponse | None = None


class SegmentDetailResponse(SegmentResponse):
    pass


class ObservationValidationAlertItem(BaseModel):
    segment_id: int
    segment_code: str
    segment_name: str
    corridor: CorridorEnum
    inspection_date: date | None = None
    reason_code: str
    message: str


class ObservationValidationSummaryResponse(BaseModel):
    total_segments: int
    complete_and_fresh_count: int
    expired_segments: list[ObservationValidationAlertItem]
    incomplete_segments: list[ObservationValidationAlertItem]
    missing_observation_segments: list[ObservationValidationAlertItem]


class ObservationFormRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "segment_code": "GG-CSK-001",
                "total_lights": 12,
                "broken_lights": 7,
                "dawn_crime_count": 5,
                "boarding_house_count": 18,
                "criteria_values": {"road_width_m": 2.4},
                "inspection_date": "2026-11-25",
            }
        }
    )

    segment_id: int | None = None
    segment_code: str | None = None
    total_lights: int = Field(..., ge=0)
    broken_lights: int = Field(..., ge=0)
    dawn_crime_count: int | None = Field(default=None, ge=0)
    boarding_house_count: int = Field(..., ge=0)
    criteria_values: dict[str, float | None] = Field(
        default_factory=dict,
        description="Nilai kriteria dinamis tambahan (key = kode kriteria, misal road_width_m).",
    )
    inspection_date: date

    @field_validator("criteria_values")
    @classmethod
    def validate_criteria_values(
        cls, values: dict[str, float | None]
    ) -> dict[str, float | None]:
        cleaned: dict[str, float | None] = {}
        for k, v in values.items():
            code = str(k).strip().lower()
            if not code:
                raise ValueError("Kode kriteria pada criteria_values tidak boleh kosong.")
            if v is not None and float(v) < 0.0:
                raise ValueError(f"Nilai kriteria '{code}' tidak boleh negatif.")
            cleaned[code] = float(v) if v is not None else None
        return cleaned

    @model_validator(mode="after")
    def validate_business_rules(self) -> "ObservationFormRequest":
        if self.segment_id is None and not self.segment_code:
            raise ValueError("Harus menyertakan segment_id atau segment_code.")
        if self.broken_lights > self.total_lights:
            raise ValueError(
                "INVALID_LIGHT_LOGIC: Jumlah lampu mati (broken_lights) tidak boleh melebihi total lampu terpasang (total_lights)."
            )
        return self


class ObservationFormResponse(BaseModel):
    observation: ObservationBriefResponse
    warnings: list[str] = Field(default_factory=list)


class CSVValidationIssue(BaseModel):
    code: str
    severity: Literal["WARNING", "ERROR"]
    message: str


class CSVValidatedRow(BaseModel):
    row_number: int
    segment_code: str
    total_lights: int | None = None
    broken_lights: int | None = None
    dawn_crime_count: int | None = None
    boarding_house_count: int | None = None
    criteria_values: dict[str, float | None] = Field(default_factory=dict)
    inspection_date: str | None = None
    status: Literal["VALID", "WARNING", "ERROR"]
    issues: list[CSVValidationIssue] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class CSVUploadPreviewResponse(BaseModel):
    batch_id: str
    filename: str
    status: BatchStatus
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    rows: list[CSVValidatedRow]
    created_at: datetime


class CSVRowCorrection(BaseModel):
    row_number: int = Field(..., ge=1)
    segment_code: str = Field(..., min_length=1)
    total_lights: int = Field(..., ge=0)
    broken_lights: int = Field(..., ge=0)
    dawn_crime_count: int | None = Field(default=None, ge=0)
    boarding_house_count: int = Field(..., ge=0)
    criteria_values: dict[str, float | None] = Field(default_factory=dict)
    inspection_date: date

    @field_validator("criteria_values")
    @classmethod
    def validate_correction_criteria(
        cls, values: dict[str, float | None]
    ) -> dict[str, float | None]:
        cleaned: dict[str, float | None] = {}
        for k, v in values.items():
            code = str(k).strip().lower()
            if v is not None and float(v) < 0.0:
                raise ValueError(f"Nilai kriteria '{code}' tidak boleh negatif.")
            cleaned[code] = float(v) if v is not None else None
        return cleaned

    @model_validator(mode="after")
    def check_lights(self) -> "CSVRowCorrection":
        if self.broken_lights > self.total_lights:
            raise ValueError("broken_lights tidak boleh melebihi total_lights.")
        return self


class CSVConfirmRequest(BaseModel):
    include_warnings: bool = True
    corrections: list[CSVRowCorrection] = Field(default_factory=list)


class CSVConfirmResponse(BaseModel):
    batch_id: str
    status: BatchStatus
    committed_count: int
    skipped_error_count: int
    committed_segment_codes: list[str]


class AHPCriterionInput(BaseModel):
    """Definisi satu kriteria pada perhitungan AHP dinamis."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Kode unik kriteria (huruf kecil, angka, underscore), misal broken_lights atau road_width_m.",
    )
    label: str = Field(..., min_length=1, max_length=150)
    direction: Literal["max", "min"] = Field(
        default="max",
        description="Arah optimasi TOPSIS: 'max' (benefit/semakin besar semakin prioritas) atau 'min' (cost).",
    )

    @field_validator("code")
    @classmethod
    def normalize_criterion_code(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not _CRITERION_CODE_PATTERN.match(cleaned):
            raise ValueError(
                "Kode kriteria harus diawali huruf kecil dan hanya mengandung huruf kecil, angka, atau underscore (_)."
            )
        return cleaned


class AHPCriterionResponse(BaseModel):
    id: int | None = None
    code: str
    label: str
    direction: Literal["max", "min"]
    weight: float
    display_order: int


class ActiveCriteriaResponse(BaseModel):
    ahp_version_id: int | None = None
    version_name: str
    cr: float
    is_consistent: bool
    criteria: list[AHPCriterionResponse]


class AHPSaatyComparisons(BaseModel):
    """Perbandingan berpasangan skala Saaty (1-9 atau resiprokal) untuk 3 kriteria bawaan."""

    c1_vs_c2: float = Field(
        ..., gt=0, description="Kerusakan lampu PJU (C1) dibanding Curanmor dini hari (C2)"
    )
    c1_vs_c3: float = Field(
        ..., gt=0, description="Kerusakan lampu PJU (C1) dibanding Kepadatan indekos (C3)"
    )
    c2_vs_c3: float = Field(
        ..., gt=0, description="Curanmor dini hari (C2) dibanding Kepadatan indekos (C3)"
    )

    def to_matrix(self) -> list[list[float]]:
        return [
            [1.0, float(self.c1_vs_c2), float(self.c1_vs_c3)],
            [1.0 / float(self.c1_vs_c2), 1.0, float(self.c2_vs_c3)],
            [1.0 / float(self.c1_vs_c3), 1.0 / float(self.c2_vs_c3), 1.0],
        ]


class AHPCalculateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "criteria": [
                    {"code": "broken_lights", "label": "Kerusakan Lampu PJU", "direction": "max"},
                    {"code": "dawn_crime_count", "label": "Curanmor Dini Hari", "direction": "max"},
                    {"code": "boarding_house_count", "label": "Kepadatan Indekos", "direction": "max"},
                    {"code": "road_width_m", "label": "Lebar Gang (m)", "direction": "min"},
                ],
                "pairwise_matrix": [
                    [1.0, 0.5, 2.0, 3.0],
                    [2.0, 1.0, 3.0, 5.0],
                    [0.5, 0.3333, 1.0, 2.0],
                    [0.3333, 0.2, 0.5, 1.0],
                ],
            }
        }
    )

    pairwise_matrix: list[list[float]] | None = Field(
        default=None,
        description="Matriks perbandingan berpasangan persegi NxN (1 <= N <= 15).",
    )
    criteria: list[AHPCriterionInput] | None = Field(
        default=None,
        description="Daftar definisi N kriteria sesuai urutan baris/kolom matriks. Opsional untuk 3 kriteria bawaan.",
    )
    saaty_comparisons: AHPSaatyComparisons | None = Field(
        default=None,
        description="Alternatif input 3 perbandingan skala Saaty (khusus 3 kriteria bawaan).",
    )

    @field_validator("pairwise_matrix")
    @classmethod
    def validate_matrix_shape(
        cls, matrix: list[list[float]] | None
    ) -> list[list[float]] | None:
        if matrix is not None:
            n = len(matrix)
            if n < MIN_CRITERIA or n > MAX_CRITERIA:
                raise ValueError(
                    f"Ukuran pairwise_matrix harus antara {MIN_CRITERIA}x{MIN_CRITERIA} hingga {MAX_CRITERIA}x{MAX_CRITERIA}."
                )
            if any(len(row) != n for row in matrix):
                raise ValueError("pairwise_matrix wajib berbentuk matriks persegi NxN.")
        return matrix

    @model_validator(mode="after")
    def resolve_matrix(self) -> "AHPCalculateRequest":
        if self.pairwise_matrix is None and self.saaty_comparisons is None:
            raise ValueError(
                "Harap sertakan pairwise_matrix (NxN) atau saaty_comparisons."
            )
        if self.pairwise_matrix is None and self.saaty_comparisons is not None:
            self.pairwise_matrix = self.saaty_comparisons.to_matrix()
        if (
            self.criteria is not None
            and self.pairwise_matrix is not None
            and len(self.criteria) != len(self.pairwise_matrix)
        ):
            raise ValueError(
                f"Jumlah criteria ({len(self.criteria)}) harus sama dengan dimensi pairwise_matrix ({len(self.pairwise_matrix)})."
            )
        if self.criteria is not None:
            codes = [c.code for c in self.criteria]
            if len(set(codes)) != len(codes):
                raise ValueError("Daftar criteria tidak boleh memiliki kode duplikat.")
        return self


class AHPCalculateResponse(BaseModel):
    pairwise_matrix: list[list[float]]
    criteria: list[AHPCriterionResponse] = Field(default_factory=list)
    weights_map: dict[str, float] = Field(default_factory=dict)
    w_light_damage: float
    w_dawn_crime: float
    w_boarding_density: float
    lambda_max: float
    ci: float
    ri: float
    cr: float
    is_consistent: bool


class AHPVersionCreateRequest(AHPCalculateRequest):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version_name": "Bobot Pakar 4 Kriteria Jatinangor v2.0",
                "activate_immediately": True,
                "criteria": [
                    {"code": "broken_lights", "label": "Kerusakan Lampu PJU", "direction": "max"},
                    {"code": "dawn_crime_count", "label": "Curanmor Dini Hari", "direction": "max"},
                    {"code": "boarding_house_count", "label": "Kepadatan Indekos", "direction": "max"},
                    {"code": "road_width_m", "label": "Lebar Gang (m)", "direction": "min"},
                ],
                "pairwise_matrix": [
                    [1.0, 0.5, 2.0, 3.0],
                    [2.0, 1.0, 3.0, 5.0],
                    [0.5, 0.3333, 1.0, 2.0],
                    [0.3333, 0.2, 0.5, 1.0],
                ],
            }
        }
    )

    version_name: str = Field(..., min_length=2, max_length=150)
    activate_immediately: bool = False


class AHPVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_name: str
    created_by: int
    pairwise_matrix: list[list[float]]
    criteria: list[AHPCriterionResponse] = Field(default_factory=list)
    weights_map: dict[str, float] = Field(default_factory=dict)
    w_light_damage: float
    w_dawn_crime: float
    w_boarding_density: float
    lambda_max: float
    ci: float
    ri: float
    cr: float
    is_consistent: bool
    is_active: bool
    created_at: datetime


class TOPSISCycleCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cycle_name": "Siklus Evaluasi November 2026",
                "criteria_directions": None,
            }
        }
    )

    cycle_name: str = Field(..., min_length=2, max_length=200)
    criteria_directions: list[Literal["max", "min"]] | None = Field(
        default=None,
        description="Opsional override arah tiap kriteria; jika kosong mengikuti definisi arah pada versi AHP aktif.",
    )


class CycleRankingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_id: int
    segment_code: str
    segment_name: str
    corridor: CorridorEnum
    is_eligible: bool
    ineligible_reason: str | None
    snapshot_data: dict[str, Any]
    norm_c1: float | None
    norm_c2: float | None
    norm_c3: float | None
    weighted_c1: float | None
    weighted_c2: float | None
    weighted_c3: float | None
    normalized_values: dict[str, float] | None = None
    weighted_values: dict[str, float] | None = None
    d_plus: float | None
    d_minus: float | None
    preference_score: float | None
    rank: int | None
    priority_category: str
    is_tie_broken: bool


class TOPSISCycleDetailResponse(BaseModel):
    cycle_id: int
    cycle_name: str
    executed_by: int
    ahp_version_id: int
    weights_snapshot: dict[str, Any]
    status: CycleStatus
    created_at: datetime
    eligible_count: int
    ineligible_count: int
    eligible_results: list[CycleRankingItemResponse]
    ineligible_results: list[CycleRankingItemResponse]


class MapSummaryMetrics(BaseModel):
    total_segments: int
    total_broken_lights: int
    eligible_count: int
    ineligible_count: int
    capacity_quota: int | None = None


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    cycle_id: int | None = None
    cycle_name: str | None = None
    summary: MapSummaryMetrics | None = None
    features: list[GeoJSONFeature]


class MapSegmentDetailResponse(BaseModel):
    segment_id: int
    segment_code: str
    name: str
    corridor: CorridorEnum
    is_active: bool
    geojson_geometry: dict[str, Any]
    pin_point: PinPoint | None = None
    pin_point_source: Literal["custom", "computed"] = "computed"
    cycle_id: int | None = None
    cycle_name: str | None = None
    ahp_weights: dict[str, Any] | None = None
    criteria: list[dict[str, Any]] | None = None
    indicators: dict[str, Any] | None = None
    normalized_values: dict[str, float | None] | None = None
    weighted_values: dict[str, float | None] | None = None
    d_plus: float | None = None
    d_minus: float | None = None
    preference_score: float | None = None
    rank: int | None = None
    priority_category: str
    is_eligible: bool | None = None
    ineligible_reason: str | None = None
    is_tie_broken: bool = False
    inspection_date: date | str | None = None
    data_source: str | None = None


class WorklistProposeRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"capacity_quota": 5}})

    capacity_quota: int = Field(..., gt=0, description="Kapasitas jumlah gang K > 0")


class WorklistCandidateItem(BaseModel):
    segment_id: int
    segment_code: str
    segment_name: str
    corridor: CorridorEnum
    rank: int
    preference_score: float
    broken_lights: int
    dawn_crime_count: int
    boarding_house_count: int
    is_tie_broken: bool


class WorklistProposeResponse(BaseModel):
    cycle_id: int
    cycle_name: str
    capacity_quota: int
    total_eligible: int
    system_proposed: list[WorklistCandidateItem]
    reserve_candidates: list[WorklistCandidateItem]


class WorklistFinalizeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "capacity_quota": 3,
                "final_selected_segment_ids": [1, 4, 6],
                "override_reason": "Prioritas akses utama kos mahasiswa yang sedang padam total.",
            }
        }
    )

    capacity_quota: int = Field(..., gt=0)
    final_selected_segment_ids: list[int] = Field(..., min_length=1)
    override_reason: str | None = None

    @field_validator("final_selected_segment_ids")
    @classmethod
    def validate_unique_ids(cls, ids: list[int]) -> list[int]:
        if len(set(ids)) != len(ids):
            raise ValueError(
                "final_selected_segment_ids tidak boleh mengandung ID duplikat."
            )
        return ids

    @model_validator(mode="after")
    def validate_quota_limit(self) -> "WorklistFinalizeRequest":
        if len(self.final_selected_segment_ids) > self.capacity_quota:
            raise ValueError(
                f"Jumlah segmen terpilih ({len(self.final_selected_segment_ids)}) melebihi kuota kapasitas ({self.capacity_quota})."
            )
        return self


class WorklistDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    decided_by: int
    capacity_quota: int
    system_proposed_segment_ids: list[int]
    final_selected_segment_ids: list[int]
    is_overridden: bool
    override_reason: str | None
    finalized_at: datetime


class CycleHistorySummaryResponse(BaseModel):
    cycle_id: int
    cycle_name: str
    created_at: datetime
    executed_by: int
    executed_by_username: str
    ahp_version_id: int
    ahp_version_name: str
    weights_snapshot: dict[str, Any]
    status: CycleStatus
    total_segments: int
    eligible_count: int
    ineligible_count: int
    is_overridden: bool | None = None
    capacity_quota: int | None = None
    finalized_at: datetime | None = None


class WorklistSelectedSegmentDetail(BaseModel):
    order_number: int
    segment_id: int
    segment_code: str
    segment_name: str
    corridor: CorridorEnum
    rank: int
    preference_score: float
    total_lights: int
    broken_lights: int
    dawn_crime_count: int
    boarding_house_count: int
    choice_status: Literal["USULAN_SISTEM", "PILIHAN_OVERRIDE"]


class WorklistDetailResponse(BaseModel):
    decision: WorklistDecisionResponse
    decided_by_name: str
    selected_segments: list[WorklistSelectedSegmentDetail]
    replaced_proposed_segments: list[WorklistCandidateItem]


class CycleHistoryDetailResponse(BaseModel):
    summary: CycleHistorySummaryResponse
    worklist: WorklistDetailResponse | None = None
    eligible_results: list[CycleRankingItemResponse]
    ineligible_results: list[CycleRankingItemResponse]
