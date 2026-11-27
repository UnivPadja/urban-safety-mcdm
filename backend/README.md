# Backend DSS Prioritas Perbaikan PJU & Mitigasi Kriminalitas Dini Hari (Kecamatan Jatinangor)

Backend REST API berbasis **FastAPI (Python 3.11+)** untuk sistem pendukung keputusan (Decision Support System) penentuan prioritas perbaikan Penerangan Jalan Umum (PJU) dan mitigasi kerawanan kriminalitas dini hari pada segmen gang/zona mikro di Kecamatan Jatinangor menggunakan metode **AHP Dinamis (1–15 kriteria) + TOPSIS** dan **Supabase PostgreSQL**.

---

## Fitur Utama (v1.1.0)

- **AHP Dinamis (`1–15` kriteria):** Mendukung matriks perbandingan berpasangan `N×N` dengan tabel Random Index Saaty penuh (`n = 1..15`), arah kriteria `max` (benefit) / `min` (cost), uji konsistensi `CR <= 0.10`, dan kompatibilitas penuh dengan 3 kriteria bawaan (`saaty_comparisons`).
- **TOPSIS Dinamis & Live Ranking Supabase:** Menghitung normalisasi, matriks terbobot, solusi ideal positif/negatif (`D+`, `D-`), skor preferensi, serta *tie-breaker* deterministik untuk jumlah kriteria dinamis baik pada siklus tersimpan maupun kalkulasi *live* peta langsung dari Supabase.
- **Pin Point Map:** Mendukung geometri GeoJSON `Point`, `LineString`, dan `Polygon`, perhitungan koordinat `pin_point` otomatis berbasis *arc-length midpoint* / centroid, dukungan override pin kustom per segmen, serta mode `geometry_mode=pin` pada endpoint peta prioritas.
- **Autentikasi JWT + RBAC Fleksibel:** Endpoint baca (`GET`) bersifat publik / opsional token (`get_optional_user`) untuk mempermudah akses peta dan dashboard, sedangkan seluruh endpoint tulis (`POST`, `PUT`, `PATCH`, `DELETE`) dilindungi JWT + RBAC (`ADMIN`, `OPERATOR`, `PENILAI`, `PENANGGUNG_JAWAB_PJU`).
- **Supabase PostgreSQL Only:** Seluruh data operasional dan koordinat OSM asli jalan/gang Jatinangor disimpan di Supabase PostgreSQL (tanpa SQLite lokal).

---

## Struktur Direktori

```text
backend/
├── app/
│   ├── api/v1/endpoints/                 # 9 router modul REST API (auth, users, segments, observations, ahp, topsis, map_view, worklists, history)
│   ├── core/                             # Konfigurasi env Supabase, koneksi SQLAlchemy, keamanan JWT/bcrypt
│   ├── models/                           # 10 entitas tabel SQLAlchemy 2.0 (JSONB PostgreSQL)
│   ├── schemas/                          # Skema validasi request/response Pydantic v2, GeoJSON, & PinPoint
│   ├── services/                         # Engine AHP dinamis, TOPSIS dinamis, validator CSV, & utilitas pin point geometri
│   ├── db_setup.py                       # Utilitas cek koneksi Supabase, init skema 10 tabel, seed, & cek row count
│   ├── main.py                           # Entrypoint FastAPI + CORS + OpenAPI metadata
│   └── seed.py                           # Seeder idempotent akun RBAC, 12 segmen OSM Jatinangor, observasi, & AHP awal
├── sample_data/
│   └── sample_jatinangor_import.csv
├── scripts/
│   └── generate_api_docs.py              # Generator otomatis API_Documentation_DSS_Jatinangor.pdf dari OpenAPI FastAPI
├── tests/
│   └── test_engines.py                   # Unit & integration tests (pytest)
├── requirements.txt
├── API_Documentation_DSS_Jatinangor.pdf
└── .env.example
```

---

## Setup Database Supabase PostgreSQL

> **Penting:** Backend ini hanya terhubung ke **PostgreSQL / Supabase** (`DATABASE_URL` wajib berawalan `postgresql://` atau `postgresql+psycopg://`).

1. **Konfigurasi `backend/.env`:**

   ```powershell
   cd backend
   Copy-Item .env.example .env
   ```

   Edit `backend/.env` dan isi `DATABASE_URL` dengan connection string Supabase PostgreSQL (Transaction / Session Pooler):

   ```env
   DATABASE_URL="postgresql+psycopg://postgres.PROJECT_REF:PASSWORD_ANDA@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
   ```

   > **Tips karakter spesial password:** Jika password mengandung karakter seperti `@`, `#`, `:`, atau `/`, lakukan URL-encoding (mis. `@` menjadi `%40`).

2. **Aktifkan virtual environment & pasang dependensi:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Inisialisasi skema 10 tabel, seed data awal, dan verifikasi koneksi Supabase:**

   ```powershell
   python -m app.db_setup
   ```

   Contoh output sukses:

   ```text
   [DB Setup] Target dialect : postgresql
   [DB Setup] Target URL     : postgresql+psycopg://postgres.PROJECT_REF:***@.../postgres
   [DB Setup] Skema 10 tabel berhasil dipastikan ada (init_db).
   [DB Setup] Seeder idempotent selesai dijalankan.

   [DB Setup] Ringkasan jumlah baris per tabel:
     - users                    : 4
     - alley_segments           : 12
     - segment_observations     : 12
     - segment_criterion_values : 0
     - ahp_weight_versions      : 1
     - ahp_version_criteria     : 3
     - csv_import_batches       : 0
     - evaluation_cycles        : 1
     - cycle_ranking_results    : 12
     - worklist_decisions       : 0
   ```

4. **Jalankan server FastAPI:**

   ```powershell
   .\.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Daftar 10 Tabel Database (Supabase PostgreSQL)

| Tabel | Fungsi |
| :--- | :--- |
| `users` | Akun pengguna RBAC (`ADMIN`, `OPERATOR`, `PENILAI`, `PENANGGUNG_JAWAB_PJU`) |
| `alley_segments` | Master 12+ segmen gang Jatinangor, geometri GeoJSON OSM (`Point`/`LineString`/`Polygon`), & custom `pin_point` |
| `segment_observations` | Data kondisi lapangan terkini tiap segmen (lampu terpasang, lampu mati, curanmor, indekos, tanggal inspeksi) |
| `segment_criterion_values` | Nilai indikator kriteria dinamis tambahan per observasi segmen |
| `csv_import_batches` | Audit & staging pratinjau validasi impor CSV sebelum konfirmasi |
| `ahp_weight_versions` | Riwayat matriks perbandingan berpasangan `N×N`, `lambda_max`, `CI`, `RI`, `CR <= 0.10`, & status aktif |
| `ahp_version_criteria` | Definisi setiap kriteria (`code`, `label`, `direction`, `weight`, `display_order`) per versi AHP |
| `evaluation_cycles` | Riwayat eksekusi siklus TOPSIS beserta snapshot bobot & daftar kriteria |
| `cycle_ranking_results` | Hasil normalisasi (`normalized_values` + `norm_c1..c3`), matriks terbobot, `D+`, `D-`, skor preferensi, peringkat, & alasan ineligibel |
| `worklist_decisions` | Keputusan daftar kerja final, kuota kapasitas `K`, flag override, & audit alasan perubahan |

---

## Dokumentasi API & Regenerasi PDF

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`
- **PDF Dokumentasi API:** `backend/API_Documentation_DSS_Jatinangor.pdf`

Untuk men-generate ulang PDF dokumentasi secara otomatis setiap ada perubahan endpoint atau skema:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts/generate_api_docs.py
```

---

## Akun Default (Hasil Seeder)

Login (`POST /api/v1/auth/login`) mendukung **Email** maupun **Username**:

| Username | Email | Password | Role RBAC |
| :--- | :--- | :--- | :--- |
| `admin` | `admin@jatinangor-dss.id` | `admin123` | `ADMIN` |
| `operator` | `operator@jatinangor-dss.id` | `operator123` | `OPERATOR` |
| `penilai` | `penilai@jatinangor-dss.id` | `penilai123` | `PENILAI` |
| `pju_lead` | `pju.lead@jatinangor-dss.id` | `pju123` | `PENANGGUNG_JAWAB_PJU` |

---

## Ringkasan Modul Endpoint (`/api/v1`)

| Modul | Endpoint Utama | Akses |
| :--- | :--- | :--- |
| **Auth** | `POST /auth/login`, `GET /auth/me` | Publik (login) / JWT (me) |
| **Users** | `GET /users`, `POST /users`, `PATCH /users/{user_id}` | `ADMIN` |
| **Alley Segments** | `GET /segments`, `GET /segments/{segment_id}`, `POST /segments`, `PUT /segments/{segment_id}` | Baca: Opsional JWT · Tulis: `OPERATOR`/`ADMIN` |
| **Observations & CSV** | `GET /observations/validation-summary`, `GET /observations/csv-template`, `POST /observations/form`, `POST /observations/upload-csv`, `GET /observations/batches/{batch_id}`, `POST /observations/batches/{batch_id}/confirm`, `DELETE /observations/batches/{batch_id}` | Baca: Opsional JWT · Tulis/Batch: `OPERATOR`/`ADMIN` |
| **AHP Weighting (Dinamis)** | `GET /ahp/criteria`, `GET /ahp/versions`, `POST /ahp/calculate-preview`, `POST /ahp/versions`, `PATCH /ahp/versions/{version_id}/activate` | Baca: Opsional JWT · Tulis: `PENILAI`/`ADMIN` |
| **TOPSIS Ranking** | `GET /topsis/cycles/latest`, `GET /topsis/cycles/{cycle_id}`, `POST /topsis/cycles` | Baca: Opsional JWT · Tulis: `PENANGGUNG_JAWAB_PJU`/`ADMIN` |
| **Priority Map & Pin Points** | `GET /map/priority-layer` (`geometry_mode=segment\|pin`, live/historis), `GET /map/segments/{segment_id}/detail` | Opsional JWT |
| **Worklists & Audit** | `POST /worklists/cycles/{cycle_id}/propose`, `POST /worklists/cycles/{cycle_id}/finalize`, `GET /worklists/cycles/{cycle_id}` | `PENANGGUNG_JAWAB_PJU`/`ADMIN` (GET: JWT) |
| **History & Export** | `GET /history/cycles`, `GET /history/cycles/{cycle_id}`, `GET /history/cycles/{cycle_id}/export-csv` | Opsional JWT |

---

## Menjalankan Pengujian (`pytest`)

Pengujian unit & integrasi berjalan menggunakan fixture SQLite in-memory sehingga tidak memodifikasi data produksi di Supabase:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```
