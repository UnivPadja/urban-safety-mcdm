"""Generator otomatis API_Documentation_DSS_Jatinangor.pdf dari skema OpenAPI FastAPI."""

from __future__ import annotations

from datetime import date
import html
import inspect
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.params import Depends as FastAPIDepends
from fastapi.routing import APIRoute

from app.api.v1.endpoints import (
    ahp,
    auth,
    history,
    map_view,
    observations,
    segments,
    topsis,
    users,
    worklists,
)
from app.core.config import settings
from app.main import app

OUTPUT_PDF = BACKEND_DIR / "API_Documentation_DSS_Jatinangor.pdf"

TAG_ORDER = [
    "Health",
    "Authentication",
    "Users",
    "Alley Segments",
    "Observations & CSV Import",
    "AHP Weighting",
    "TOPSIS Ranking",
    "Priority Map",
    "Worklists & Override Audit",
    "History & Export",
]

FIELD_EXAMPLES: dict[str, Any] = {
    "id": 1,
    "segment_id": 1,
    "cycle_id": 1,
    "ahp_version_id": 1,
    "executed_by": 4,
    "decided_by": 4,
    "created_by": 3,
    "updated_by": 2,
    "uploaded_by": 2,
    "username": "penilai",
    "executed_by_username": "pju_lead",
    "email": "penilai@jatinangor-dss.id",
    "full_name": "Pakar Penilai AHP",
    "decided_by_name": "Penanggung Jawab PJU",
    "password": "new_secure_password123",
    "role": "PENILAI",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "segment_code": "GG-CSK-001",
    "name": "Gang Ciseke Lama Utara",
    "segment_name": "Gang Ciseke Lama Utara",
    "corridor": "Ciseke",
    "version_name": "Bobot Pakar 4 Kriteria Jatinangor v2.0",
    "ahp_version_name": "Bobot Pakar 4 Kriteria Jatinangor v2.0",
    "cycle_name": "Siklus Evaluasi November 2026",
    "filename": "observasi_jatinangor_nov2026.csv",
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "lat": -6.933572,
    "lon": 107.775454,
    "pin_point": {"lat": -6.933572, "lon": 107.775454},
    "pin_point_source": "computed",
    "geojson_geometry": {
        "type": "LineString",
        "coordinates": [
            [107.775007, -6.932916],
            [107.77543, -6.933538],
            [107.775691, -6.934223],
        ],
    },
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [107.775007, -6.932916],
            [107.77543, -6.933538],
            [107.775691, -6.934223],
        ],
    },
    "properties": {
        "segment_id": 1,
        "segment_code": "GG-CSK-001",
        "name": "Gang Ciseke Lama Utara",
        "corridor": "Ciseke",
        "pin_point": {"lat": -6.933572, "lon": 107.775454},
        "pin_point_source": "computed",
        "rank": 1,
        "preference_score": 0.84215,
        "priority_category": "Tinggi",
        "total_lights": 12,
        "broken_lights": 7,
        "dawn_crime_count": 5,
        "boarding_house_count": 18,
        "criteria_values": {
            "broken_lights": 7.0,
            "dawn_crime_count": 5.0,
            "boarding_house_count": 18.0,
        },
        "inspection_date": "2026-11-25",
        "is_eligible": True,
        "ineligible_reason": None,
        "is_tie_broken": False,
    },
    "total_lights": 12,
    "broken_lights": 7,
    "dawn_crime_count": 5,
    "boarding_house_count": 18,
    "criteria_values": {
        "broken_lights": 7.0,
        "dawn_crime_count": 5.0,
        "boarding_house_count": 18.0,
        "road_width_m": 2.4,
    },
    "weights_map": {
        "broken_lights": 0.2782,
        "dawn_crime_count": 0.4914,
        "boarding_house_count": 0.1497,
        "road_width_m": 0.0807,
    },
    "weights_snapshot": {
        "w_light_damage": 0.2970,
        "w_dawn_crime": 0.5396,
        "w_boarding_density": 0.1634,
        "weights_map": {
            "broken_lights": 0.2970,
            "dawn_crime_count": 0.5396,
            "boarding_house_count": 0.1634,
        },
        "criteria": [
            {"code": "broken_lights", "label": "Kerusakan Lampu PJU", "direction": "max", "weight": 0.2970},
            {"code": "dawn_crime_count", "label": "Curanmor Dini Hari", "direction": "max", "weight": 0.5396},
            {"code": "boarding_house_count", "label": "Kepadatan Indekos", "direction": "max", "weight": 0.1634},
        ],
        "cr": 0.0088,
        "version_name": "Bobot Pakar Awal Jatinangor v1.0",
    },
    "ahp_weights": {
        "w_light_damage": 0.2970,
        "w_dawn_crime": 0.5396,
        "w_boarding_density": 0.1634,
        "weights_map": {
            "broken_lights": 0.2970,
            "dawn_crime_count": 0.5396,
            "boarding_house_count": 0.1634,
        },
    },
    "snapshot_data": {
        "total_lights": 12,
        "broken_lights": 7,
        "dawn_crime_count": 5,
        "boarding_house_count": 18,
        "criteria_values": {
            "broken_lights": 7.0,
            "dawn_crime_count": 5.0,
            "boarding_house_count": 18.0,
        },
        "inspection_date": "2026-11-25",
        "data_source": "MANUAL_FORM",
    },
    "indicators": {
        "total_lights": 12,
        "broken_lights": 7,
        "dawn_crime_count": 5,
        "boarding_house_count": 18,
        "criteria_values": {
            "broken_lights": 7.0,
            "dawn_crime_count": 5.0,
            "boarding_house_count": 18.0,
        },
    },
    "normalized_values": {
        "broken_lights": 0.3912,
        "dawn_crime_count": 0.3780,
        "boarding_house_count": 0.3204,
    },
    "weighted_values": {
        "broken_lights": 0.1162,
        "dawn_crime_count": 0.2040,
        "boarding_house_count": 0.0524,
    },
    "pairwise_matrix": [
        [1.0, 0.5, 2.0, 3.0],
        [2.0, 1.0, 3.0, 5.0],
        [0.5, 0.3333, 1.0, 2.0],
        [0.3333, 0.2, 0.5, 1.0],
    ],
    "w_light_damage": 0.2782,
    "w_dawn_crime": 0.4914,
    "w_boarding_density": 0.1497,
    "lambda_max": 4.0156,
    "ci": 0.0052,
    "ri": 0.90,
    "cr": 0.0058,
    "is_consistent": True,
    "is_active": True,
    "is_eligible": True,
    "ineligible_reason": None,
    "is_tie_broken": False,
    "is_overridden": False,
    "override_reason": None,
    "clear_pin_point": False,
    "norm_c1": 0.3912,
    "norm_c2": 0.3780,
    "norm_c3": 0.3204,
    "weighted_c1": 0.1162,
    "weighted_c2": 0.2040,
    "weighted_c3": 0.0524,
    "d_plus": 0.0412,
    "d_minus": 0.2198,
    "preference_score": 0.8421,
    "rank": 1,
    "priority_category": "Tinggi",
    "code": "broken_lights",
    "label": "Kerusakan Lampu PJU",
    "direction": "max",
    "weight": 0.2970,
    "display_order": 0,
    "inspection_date": "2026-11-25",
    "last_inspection_date": "2026-11-25",
    "data_source": "MANUAL_FORM",
    "capacity_quota": 5,
    "total_segments": 12,
    "total_broken_lights": 57,
    "eligible_count": 11,
    "ineligible_count": 1,
    "complete_and_fresh_count": 12,
    "total_rows": 8,
    "valid_rows": 4,
    "warning_rows": 2,
    "error_rows": 2,
    "committed_count": 6,
    "skipped_error_count": 2,
    "committed_segment_codes": ["GG-CSK-001", "GG-CRG-001", "GG-GHN-001"],
    "system_proposed_segment_ids": [6, 4, 1],
    "final_selected_segment_ids": [6, 4, 1],
    "order_number": 1,
    "choice_status": "USULAN_SISTEM",
    "reason_code": "EXPIRED_INSPECTION_DATE",
    "message": "Inspeksi terakhir melebihi batas 90 hari.",
    "messages": ["[EXPIRED_INSPECTION_DATE] Tanggal inspeksi kedaluwarsa."],
    "warnings": [],
    "severity": "WARNING",
    "row_number": 2,
    "total_eligible": 11,
    "created_at": "2026-11-27T08:00:00Z",
    "updated_at": "2026-11-27T08:00:00Z",
    "finalized_at": "2026-11-27T08:15:00Z",
}


def _collect_route_dependency_calls(route: APIRoute) -> list[Any]:
    calls: list[Any] = []
    # Baca signature endpoint langsung agar tidak bergantung pada internal Dependant FastAPI.
    for param in inspect.signature(route.endpoint).parameters.values():
        default = param.default
        if isinstance(default, FastAPIDepends) and default.dependency is not None:
            calls.append(default.dependency)

    for dep in getattr(route, "dependencies", None) or []:
        if getattr(dep, "dependency", None) is not None:
            calls.append(dep.dependency)

    def _walk(dependant: Any) -> None:
        for d in getattr(dependant, "dependencies", None) or []:
            if getattr(d, "call", None) is not None:
                calls.append(d.call)
            _walk(d)

    if getattr(route, "dependant", None) is not None:
        _walk(route.dependant)
    return calls


def _iter_api_routes() -> list[tuple[str, APIRoute]]:
    found: list[tuple[str, APIRoute]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            found.append((route.path, route))

    v1_prefix = settings.API_V1_PREFIX.rstrip("/")
    module_routers = [
        auth.router,
        users.router,
        segments.router,
        observations.router,
        ahp.router,
        topsis.router,
        map_view.router,
        worklists.router,
        history.router,
    ]
    for router in module_routers:
        for route in router.routes:
            if isinstance(route, APIRoute):
                full_path = f"{v1_prefix}{route.path}"
                found.append((full_path, route))
    return found


def inspect_route_auth() -> dict[tuple[str, str], tuple[str, str]]:
    """Ambil metadata autentikasi dan RBAC aktual dari setiap route FastAPI."""
    auth_map: dict[tuple[str, str], tuple[str, str]] = {}
    for full_path, route in _iter_api_routes():
        calls = _collect_route_dependency_calls(route)
        badge = "Public"
        css_class = "auth-public"

        role_call = next(
            (c for c in calls if getattr(c, "__name__", "") == "_role_checker"), None
        )
        if role_call is not None:
            roles: list[str] = []
            if getattr(role_call, "__closure__", None):
                for cell in role_call.__closure__:
                    val = cell.cell_contents
                    if isinstance(val, tuple):
                        roles = [getattr(r, "value", str(r)) for r in val]
            role_str = ", ".join(roles) if roles else "Authenticated"
            badge = f"JWT · {role_str}"
            css_class = "auth-rbac"
        elif any(getattr(c, "__name__", "") == "get_current_user" for c in calls):
            badge = "Bearer JWT Required"
            css_class = "auth-required"
        elif any(getattr(c, "__name__", "") == "get_optional_user" for c in calls):
            badge = "Optional JWT (Public Read)"
            css_class = "auth-optional"

        for method in route.methods:
            if method not in {"HEAD", "OPTIONS"}:
                auth_map[(method.upper(), full_path)] = (badge, css_class)
    return auth_map


def synthesize_example(
    schema: dict[str, Any],
    components: dict[str, Any],
    field_name: str | None = None,
    depth: int = 0,
) -> Any:
    """Bangun contoh JSON realistis dari skema OpenAPI tanpa placeholder generik."""
    if "const" in schema:
        return schema["const"]

    if "example" in schema:
        return schema["example"]

    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        ref_schema = components.get("schemas", {}).get(ref_name, {})
        if "example" in ref_schema:
            return ref_schema["example"]
        return synthesize_example(
            ref_schema, components, field_name=field_name, depth=depth + 1
        )

    if "anyOf" in schema:
        non_null = [s for s in schema["anyOf"] if s.get("type") != "null"]
        chosen = non_null[0] if non_null else schema["anyOf"][0]
        return synthesize_example(
            chosen, components, field_name=field_name, depth=depth
        )

    if field_name and field_name in FIELD_EXAMPLES:
        return FIELD_EXAMPLES[field_name]

    if depth > 8:
        return None

    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        props = schema.get("properties", {})
        if not props:
            return FIELD_EXAMPLES.get(field_name or "", {})
        out: dict[str, Any] = {}
        for k, v in props.items():
            out[k] = synthesize_example(v, components, field_name=k, depth=depth + 1)
        return out

    if schema_type == "array":
        if field_name == "criteria":
            return [
                {"id": 1, "code": "broken_lights", "label": "Kerusakan Lampu PJU", "direction": "max", "weight": 0.2970, "display_order": 0},
                {"id": 2, "code": "dawn_crime_count", "label": "Curanmor Dini Hari", "direction": "max", "weight": 0.5396, "display_order": 1},
                {"id": 3, "code": "boarding_house_count", "label": "Kepadatan Indekos", "direction": "max", "weight": 0.1634, "display_order": 2},
            ]
        if field_name == "issues":
            return [
                {
                    "code": "EXPIRED_INSPECTION_DATE",
                    "severity": "WARNING",
                    "message": "Tanggal inspeksi kedaluwarsa (95 hari yang lalu, batas maksimal 90 hari).",
                }
            ]
        item_schema = schema.get("items", {})
        return [
            synthesize_example(item_schema, components, field_name=None, depth=depth + 1)
        ]

    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 0.5
    if schema_type == "boolean":
        return True
    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "date":
            return "2026-11-25"
        if fmt == "date-time":
            return "2026-11-27T08:00:00Z"
        if fmt == "email":
            return "operator@jatinangor-dss.id"
        return "value"
    return None


def compact_json(obj: Any) -> str:
    """Format JSON rapi sambil memadatkan array angka/koordinat pendek dalam satu baris."""
    raw = json.dumps(obj, indent=2, ensure_ascii=False)
    pattern = re.compile(r"\[\s*\n\s*((?:-?\d+(?:\.\d+)?(?:\s*,\s*\n\s*-?\d+(?:\.\d+)?)*))\s*\n\s*\]")
    compacted = pattern.sub(
        lambda m: "[" + ", ".join(x.strip() for x in m.group(1).split(",")) + "]",
        raw,
    )
    return compacted


def schema_type_label(schema: dict[str, Any], components: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "anyOf" in schema:
        parts = [schema_type_label(s, components) for s in schema["anyOf"]]
        return " | ".join(dict.fromkeys(parts))
    t = schema.get("type", "any")
    if t == "array":
        inner = schema_type_label(schema.get("items", {}), components)
        return f"array[{inner}]"
    if "enum" in schema:
        vals = ", ".join(str(v) for v in schema["enum"][:5])
        return f"enum({vals})"
    return str(t)


def build_html() -> str:
    spec = app.openapi()
    components = spec.get("components", {})
    auth_map = inspect_route_auth()
    paths = spec.get("paths", {})

    grouped: dict[str, list[dict[str, Any]]] = {tag: [] for tag in TAG_ORDER}
    total_endpoints = 0

    for path, methods_dict in paths.items():
        for method, op in methods_dict.items():
            method_up = method.upper()
            if method_up not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            total_endpoints += 1
            tags = op.get("tags") or ["Other"]
            tag = tags[0]
            grouped.setdefault(tag, []).append(
                {
                    "method": method_up,
                    "path": path,
                    "op": op,
                    "auth": auth_map.get((method_up, path), ("Public", "auth-public")),
                }
            )

    toc_rows = []
    idx = 0
    for tag in list(grouped.keys()):
        items = grouped[tag]
        if not items:
            continue
        for item in items:
            idx += 1
            m = item["method"]
            p = item["path"]
            summary = (
                item["op"].get("description") or item["op"].get("summary") or ""
            ).splitlines()[0]
            auth_label, auth_cls = item["auth"]
            toc_rows.append(
                f"<tr>"
                f"<td class='col-num'>{idx}</td>"
                f"<td><span class='badge method-{m.lower()}'>{m}</span></td>"
                f"<td><code>{html.escape(p)}</code></td>"
                f"<td><span class='auth-pill {auth_cls}'>{html.escape(auth_label)}</span></td>"
                f"<td>{html.escape(summary)}</td>"
                f"</tr>"
            )

    sections_html = []
    for tag in list(grouped.keys()):
        items = grouped[tag]
        if not items:
            continue
        cards = []
        for item in items:
            m = item["method"]
            p = item["path"]
            op = item["op"]
            auth_label, auth_cls = item["auth"]
            summary = op.get("summary") or ""
            description = op.get("description") or ""

            params = op.get("parameters") or []
            params_html = ""
            if params:
                p_rows = []
                for prm in params:
                    p_name = prm.get("name", "")
                    p_in = prm.get("in", "")
                    p_req = "Wajib" if prm.get("required") else "Opsional"
                    p_type = schema_type_label(prm.get("schema", {}), components)
                    p_desc = prm.get("description") or "-"
                    p_rows.append(
                        f"<tr><td><code>{html.escape(p_name)}</code></td>"
                        f"<td>{html.escape(p_in)}</td>"
                        f"<td><code>{html.escape(p_type)}</code></td>"
                        f"<td>{p_req}</td>"
                        f"<td>{html.escape(p_desc)}</td></tr>"
                    )
                params_html = (
                    "<div class='subhead'>Parameters</div>"
                    "<table class='mini-table'><thead><tr>"
                    "<th>Nama</th><th>Lokasi</th><th>Tipe</th><th>Status</th><th>Keterangan</th>"
                    "</tr></thead><tbody>" + "".join(p_rows) + "</tbody></table>"
                )

            req_html = ""
            req_body = op.get("requestBody")
            if req_body:
                content = req_body.get("content", {})
                if "application/json" in content:
                    req_schema = content["application/json"].get("schema", {})
                    example_obj = synthesize_example(req_schema, components)
                    pretty = compact_json(example_obj)
                    req_html = (
                        "<div class='subhead'>Request Body (<code>application/json</code>)</div>"
                        f"<pre class='code-block'>{html.escape(pretty)}</pre>"
                    )
                elif "multipart/form-data" in content:
                    req_html = (
                        "<div class='subhead'>Request Body (<code>multipart/form-data</code>)</div>"
                        "<div class='note-box'>Form field <code>file</code>: berkas <code>.csv</code> UTF-8 "
                        "(kolom wajib: <code>segment_code, total_lights, broken_lights, dawn_crime_count, "
                        "boarding_house_count, inspection_date</code> + kolom kriteria dinamis aktif jika ada).</div>"
                    )

            resp_html = ""
            responses = op.get("responses", {})
            success_code = next(
                (c for c in ("200", "201", "204") if c in responses),
                next(iter(responses.keys()), "200"),
            )
            resp_obj = responses.get(success_code, {})
            resp_desc = resp_obj.get("description", "Success")
            resp_content = resp_obj.get("content", {})
            if success_code == "204":
                resp_html = (
                    f"<div class='subhead'>Response <code>{success_code}</code> ({html.escape(resp_desc)})</div>"
                    "<div class='note-box'>No Content (empty body).</div>"
                )
            elif "text/csv" in resp_content:
                csv_ex = (
                    resp_content["text/csv"].get("example")
                    or "segment_code,total_lights,broken_lights,..."
                )
                resp_html = (
                    f"<div class='subhead'>Response <code>{success_code}</code> (<code>text/csv</code>): {html.escape(resp_desc)}</div>"
                    f"<pre class='code-block'>{html.escape(str(csv_ex).strip())}</pre>"
                )
            elif "application/json" in resp_content:
                r_schema = resp_content["application/json"].get("schema", {})
                if p == "/health":
                    example_resp = {
                        "status": "ok",
                        "service": spec["info"]["title"],
                        "version": spec["info"]["version"],
                    }
                else:
                    example_resp = synthesize_example(r_schema, components)
                pretty_resp = compact_json(example_resp)
                lines = pretty_resp.splitlines()
                if len(lines) > 48:
                    pretty_resp = (
                        "\n".join(lines[:45])
                        + "\n  // ... (field lainnya mengikuti skema OpenAPI)\n}"
                    )
                resp_html = (
                    f"<div class='subhead'>Response <code>{success_code}</code> (<code>application/json</code>): {html.escape(resp_desc)}</div>"
                    f"<pre class='code-block'>{html.escape(pretty_resp)}</pre>"
                )

            cards.append(
                f"<div class='endpoint-card'>"
                f"<div class='ep-header'>"
                f"<div class='ep-title-row'>"
                f"<span class='badge method-{m.lower()}'>{m}</span>"
                f"<code class='ep-path'>{html.escape(p)}</code>"
                f"</div>"
                f"<span class='auth-pill {auth_cls}'>{html.escape(auth_label)}</span>"
                f"</div>"
                f"<div class='ep-desc'><strong>{html.escape(summary)}</strong>"
                f"{': ' + html.escape(description) if description and description != summary else ''}</div>"
                f"{params_html}{req_html}{resp_html}"
                f"</div>"
            )

        sections_html.append(
            f"<section class='module-section'>"
            f"<h2 class='module-title'>{html.escape(tag)}</h2>"
            + "".join(cards)
            + "</section>"
        )

    today_str = date.today().strftime("%d %B %Y")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8" />
<title>API Documentation: DSS PJU Jatinangor</title>
<style>
  @page {{
    size: A4;
    margin: 15mm 13mm 15mm 13mm;
    @bottom-left {{
      content: "DSS Prioritas Perbaikan PJU Jatinangor · API v{html.escape(spec['info']['version'])}";
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 8pt;
      color: #64748b;
    }}
    @bottom-right {{
      content: "Halaman " counter(page) " / " counter(pages);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 8pt;
      color: #64748b;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    font-size: 8.8pt;
    line-height: 1.42;
    color: #0f172a;
    margin: 0;
  }}
  .cover {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    color: #f8fafc;
    padding: 24px 24px;
    border-radius: 10px;
    margin-bottom: 14px;
  }}
  .cover-eyebrow {{
    font-size: 8pt;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #93c5fd;
    font-weight: 600;
    margin-bottom: 5px;
  }}
  .cover h1 {{
    margin: 0 0 7px 0;
    font-size: 18pt;
    line-height: 1.2;
  }}
  .cover p {{
    margin: 0 0 12px 0;
    color: #cbd5e1;
    font-size: 9pt;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 9px;
    margin-top: 10px;
  }}
  .meta-item {{
    background: rgba(255,255,255,0.09);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 6px;
    padding: 7px 10px;
  }}
  .meta-label {{ font-size: 7.2pt; color: #93c5fd; text-transform: uppercase; }}
  .meta-val {{ font-size: 9.8pt; font-weight: 700; color: #ffffff; margin-top: 2px; }}

  .info-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 14px;
  }}
  .info-box {{
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 12px;
    background: #f8fafc;
  }}
  .info-box h3 {{
    margin: 0 0 5px 0;
    font-size: 9.5pt;
    color: #0f172a;
  }}
  .info-box ul {{
    margin: 0;
    padding-left: 15px;
  }}
  .info-box li {{ margin-bottom: 3px; font-size: 8.3pt; }}

  h2.section-heading {{
    font-size: 11.5pt;
    color: #0f172a;
    border-bottom: 2px solid #1d4ed8;
    padding-bottom: 3px;
    margin: 12px 0 8px 0;
  }}
  h2.module-title {{
    font-size: 12.5pt;
    color: #1e3a8a;
    border-bottom: 2px solid #cbd5e1;
    padding-bottom: 3px;
    margin: 16px 0 9px 0;
    break-after: avoid;
  }}

  table.toc-table, table.mini-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 7.8pt;
    margin-bottom: 8px;
  }}
  table.toc-table th, table.mini-table th {{
    background: #f1f5f9;
    color: #334155;
    text-align: left;
    padding: 4px 5px;
    border: 1px solid #cbd5e1;
    font-weight: 600;
  }}
  table.toc-table td, table.mini-table td {{
    padding: 3.5px 5px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
  }}
  .col-num {{ width: 22px; text-align: center; color: #64748b; }}

  .endpoint-card {{
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 9px 11px;
    margin-bottom: 10px;
    background: #ffffff;
    break-inside: avoid;
  }}
  .ep-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 5px;
    margin-bottom: 5px;
  }}
  .ep-title-row {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .ep-path {{
    font-size: 9pt;
    font-weight: 700;
    color: #0f172a;
    background: transparent;
    padding: 0;
  }}
  .ep-desc {{
    font-size: 8.3pt;
    color: #334155;
    margin-bottom: 5px;
  }}
  .subhead {{
    font-size: 7.6pt;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin: 6px 0 3px 0;
  }}

  .badge {{
    display: inline-block;
    padding: 1.5px 6px;
    border-radius: 4px;
    font-size: 7.2pt;
    font-weight: 700;
    color: #ffffff;
    min-width: 44px;
    text-align: center;
  }}
  .method-get {{ background: #2563eb; }}
  .method-post {{ background: #16a34a; }}
  .method-put {{ background: #d97706; }}
  .method-patch {{ background: #7c3aed; }}
  .method-delete {{ background: #dc2626; }}

  .auth-pill {{
    display: inline-block;
    padding: 1.5px 6px;
    border-radius: 999px;
    font-size: 7pt;
    font-weight: 600;
    white-space: nowrap;
  }}
  .auth-public {{ background: #dcfce7; color: #166534; }}
  .auth-optional {{ background: #e0f2fe; color: #075985; }}
  .auth-required {{ background: #fef3c7; color: #92400e; }}
  .auth-rbac {{ background: #fee2e2; color: #991b1b; }}

  code {{
    font-family: "Cascadia Code", Consolas, "Courier New", monospace;
    font-size: 7.7pt;
    background: #f1f5f9;
    padding: 1px 3.5px;
    border-radius: 3px;
  }}
  pre.code-block {{
    font-family: "Cascadia Code", Consolas, "Courier New", monospace;
    font-size: 7.2pt;
    line-height: 1.34;
    background: #0f172a;
    color: #e2e8f0;
    padding: 7px 9px;
    border-radius: 5px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: anywhere;
  }}
  .note-box {{
    background: #f8fafc;
    border-left: 3px solid #3b82f6;
    padding: 5px 9px;
    font-size: 8pt;
    color: #334155;
  }}
  .page-break {{ page-break-before: always; }}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-eyebrow">REST API Reference · FastAPI + Supabase PostgreSQL</div>
  <h1>{html.escape(spec['info']['title'])}</h1>
  <p>Dokumentasi resmi backend Decision Support System (DSS) metode <strong>AHP Dinamis (1–15 kriteria)</strong>, <strong>TOPSIS Dinamis</strong>, dan <strong>Pin Point Map</strong> berbasis data OpenStreetMap Kecamatan Jatinangor.</p>
  <div class="meta-grid">
    <div class="meta-item"><div class="meta-label">Versi API</div><div class="meta-val">v{html.escape(spec['info']['version'])}</div></div>
    <div class="meta-item"><div class="meta-label">Total Endpoint</div><div class="meta-val">{total_endpoints} Routes</div></div>
    <div class="meta-item"><div class="meta-label">Database</div><div class="meta-val">Supabase (10 Tabel)</div></div>
    <div class="meta-item"><div class="meta-label">Diperbarui</div><div class="meta-val">{today_str}</div></div>
  </div>
</div>

<div class="info-grid">
  <div class="info-box">
    <h3>Autentikasi &amp; RBAC</h3>
    <ul>
      <li>Header: <code>Authorization: Bearer &lt;JWT&gt;</code> (juga mendukung <code>mock-jwt-token-&lt;username&gt;-&lt;ts&gt;</code> untuk dev/seeder).</li>
      <li>Endpoint baca utama (<code>GET</code> peta, segmen, AHP, TOPSIS, histori) bersifat <strong>Optional JWT (Public Read)</strong> agar peta &amp; dashboard langsung dapat dimuat.</li>
      <li>Endpoint tulis (<code>POST/PUT/PATCH/DELETE</code>) wajib JWT sesuai peran: <code>ADMIN</code>, <code>OPERATOR</code>, <code>PENILAI</code>, <code>PENANGGUNG_JAWAB_PJU</code>.</li>
    </ul>
  </div>
  <div class="info-box">
    <h3>Pembaruan Utama v1.1.0</h3>
    <ul>
      <li><strong>Kriteria Dinamis (1–15):</strong> Endpoint baru <code>GET /api/v1/ahp/criteria</code>, matriks AHP <code>N×N</code>, arah <code>max/min</code> per kriteria, &amp; template CSV adaptif.</li>
      <li><strong>Pin Point Map:</strong> GeoJSON mendukung <code>Point</code>, <code>LineString</code>, <code>Polygon</code>; field <code>pin_point</code> (<em>arc-length midpoint</em> / custom override); parameter <code>geometry_mode=pin</code>.</li>
      <li><strong>Live Supabase Map:</strong> <code>GET /api/v1/map/priority-layer</code> tanpa <code>cycle_id</code> menghitung ranking TOPSIS dinamis secara <em>real-time</em> dari Supabase.</li>
    </ul>
  </div>
</div>

<h2 class="section-heading">Ringkasan Daftar Endpoint ({total_endpoints} Endpoints)</h2>
<table class="toc-table">
  <thead>
    <tr>
      <th class="col-num">#</th>
      <th>Method</th>
      <th>Path</th>
      <th>Akses / RBAC</th>
      <th>Deskripsi Singkat</th>
    </tr>
  </thead>
  <tbody>
    {''.join(toc_rows)}
  </tbody>
</table>

<div class="page-break"></div>

{''.join(sections_html)}

</body>
</html>
"""


def find_headless_browser() -> str | None:
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return str(path)
    return None


def main() -> int:
    auth_map = inspect_route_auth()
    print(f"[API Docs] Terdeteksi {len(auth_map)} route auth/RBAC metadata.")
    html_content = build_html()
    browser = find_headless_browser()
    if not browser:
        print(
            "[API Docs] Browser headless (Edge/Chrome) tidak ditemukan untuk konversi PDF.",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "api_docs.html"
        html_path.write_text(html_content, encoding="utf-8")
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={OUTPUT_PDF}",
            html_path.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not OUTPUT_PDF.exists():
            print(f"[API Docs] Gagal membuat PDF: {result.stderr}", file=sys.stderr)
            return 1

    size_kb = OUTPUT_PDF.stat().st_size / 1024.0
    print(f"[API Docs] Berhasil membuat {OUTPUT_PDF} ({size_kb:.1f} KB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
