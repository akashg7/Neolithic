# Data Health & Ingestion Report

- **Raw records loaded:** 240,679
- **Duplicates dropped on (series_id, date) & (Mandi, Commodity, date):** 5,392
- **Clean curated snapshot rows:** 6,464
- **Outliers flagged (>50% DoD jump, preserved unclipped):** 51
- **Provenance stamp:** `source = 'real'` (100% of rows)

---

## Curated Mandi Breakdown

| Commodity | Role | Mandi | Rows | Start Date | End Date | Calendar Days | Outlier Count |
|---|---|---|---|---|---|---|---|
| Onion | **Core** | `Lasalgaon APMC` | 671 | 2024-02-08 | 2026-09-02 | 938 | 6 |
| Onion | **Core** | `Pimpalgaon APMC` | 647 | 2024-02-08 | 2026-06-18 | 862 | 6 |
| Onion | **Core** | `Pune(Manjri) APMC` | 763 | 2024-02-02 | 2026-09-02 | 944 | 17 |
| Onion | **Pooling Neighbor** | `Kopargaon APMC` | 651 | 2024-02-02 | 2026-09-02 | 944 | 2 |
| Onion | **Pooling Neighbor** | `Pune(Moshi) APMC` | 648 | 2024-02-08 | 2026-09-01 | 937 | 14 |
| Onion | **Pooling Neighbor** | `Kolhapur APMC` | 735 | 2024-02-08 | 2026-09-02 | 938 | 2 |
| Onion | **Pooling Neighbor** | `Satara APMC` | 716 | 2024-02-11 | 2026-09-02 | 935 | 4 |
| Soyabean | **Core** | `Akola APMC` | 273 | 2025-09-08 | 2026-09-02 | 360 | 0 |
| Soyabean | **Core** | `Latur APMC` | 177 | 2025-09-13 | 2026-07-31 | 322 | 0 |
| Soyabean | **Core** | `Nanded APMC` | 146 | 2025-09-08 | 2026-08-24 | 351 | 0 |
| Soyabean | **Pooling Neighbor** | `Amravati APMC` | 269 | 2025-09-06 | 2026-09-02 | 362 | 0 |
| Soyabean | **Pooling Neighbor** | `Kopargaon APMC` | 265 | 2025-09-08 | 2026-09-02 | 360 | 0 |
| Soyabean | **Pooling Neighbor** | `Hinganghat APMC` | 250 | 2025-09-06 | 2026-09-02 | 362 | 0 |
| Soyabean | **Pooling Neighbor** | `Tuljapur APMC` | 253 | 2025-09-05 | 2026-09-02 | 363 | 0 |

---

## Missing Value Analysis

| Column Category | Missing / Null Count | Completeness |
|---|---|---|
| Identifiers & Target (date, Mandi, Commodity, ModalPrice) | 0 | 100.0% |
| Arrivals & Lags | 0 | 100.0% |
| Weather Dynamics (Open-Meteo) | 0 | 100.0% |

---

## Deduplication Integrity Check

- Duplicates by `(series_id, date)` in snapshot: **0**
- Duplicates by `(Mandi, Commodity, date)` in snapshot: **0**
