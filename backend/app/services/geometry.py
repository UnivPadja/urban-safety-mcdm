"""Utilitas geometri GeoJSON dan perhitungan pin point segmen."""

from __future__ import annotations

import math
from typing import Any


def _point_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    # Jarak planar dalam derajat sudah akurat untuk panjang gang mikro di tingkat kecamatan.
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _linestring_midpoint(coords: list[Any]) -> dict[str, float] | None:
    """Cari titik tengah berdasarkan panjang lintasan (arc-length), bukan indeks array."""
    points = [
        (float(pt[0]), float(pt[1]))
        for pt in coords
        if isinstance(pt, (list, tuple)) and len(pt) >= 2
    ]
    if not points:
        return None
    if len(points) == 1:
        return {"lat": round(points[0][1], 6), "lon": round(points[0][0], 6)}

    seg_lengths = [
        _point_distance(points[i], points[i + 1]) for i in range(len(points) - 1)
    ]
    total_length = sum(seg_lengths)
    if total_length <= 0.0:
        return {"lat": round(points[0][1], 6), "lon": round(points[0][0], 6)}

    half = total_length / 2.0
    traversed = 0.0
    for idx, seg_len in enumerate(seg_lengths):
        if traversed + seg_len >= half and seg_len > 0.0:
            ratio = (half - traversed) / seg_len
            lon = points[idx][0] + ratio * (points[idx + 1][0] - points[idx][0])
            lat = points[idx][1] + ratio * (points[idx + 1][1] - points[idx][1])
            return {"lat": round(lat, 6), "lon": round(lon, 6)}
        traversed += seg_len

    return {"lat": round(points[-1][1], 6), "lon": round(points[-1][0], 6)}


def _polygon_centroid(coords: list[Any]) -> dict[str, float] | None:
    """Hitung titik pusat (centroid) ring terluar Polygon."""
    if not coords or not isinstance(coords[0], (list, tuple)):
        return None
    outer_ring = [
        (float(pt[0]), float(pt[1]))
        for pt in coords[0]
        if isinstance(pt, (list, tuple)) and len(pt) >= 2
    ]
    if not outer_ring:
        return None
    if len(outer_ring) > 1 and outer_ring[0] == outer_ring[-1]:
        outer_ring = outer_ring[:-1]
    avg_lon = sum(pt[0] for pt in outer_ring) / len(outer_ring)
    avg_lat = sum(pt[1] for pt in outer_ring) / len(outer_ring)
    return {"lat": round(avg_lat, 6), "lon": round(avg_lon, 6)}


def resolve_pin_point(
    geojson_geometry: dict[str, Any] | None,
    custom_pin_point: dict[str, Any] | None = None,
) -> tuple[dict[str, float] | None, str]:
    """Prioritaskan pin_point kustom jika ada, atau hitung otomatis dari geometri."""
    if (
        isinstance(custom_pin_point, dict)
        and "lat" in custom_pin_point
        and "lon" in custom_pin_point
    ):
        return (
            {
                "lat": round(float(custom_pin_point["lat"]), 6),
                "lon": round(float(custom_pin_point["lon"]), 6),
            },
            "custom",
        )

    if not isinstance(geojson_geometry, dict):
        return None, "computed"

    geom_type = geojson_geometry.get("type")
    coords = geojson_geometry.get("coordinates")

    if geom_type == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        return (
            {"lat": round(float(coords[1]), 6), "lon": round(float(coords[0]), 6)},
            "computed",
        )
    if geom_type == "LineString" and isinstance(coords, list):
        return _linestring_midpoint(coords), "computed"
    if geom_type == "Polygon" and isinstance(coords, list):
        return _polygon_centroid(coords), "computed"

    return None, "computed"
