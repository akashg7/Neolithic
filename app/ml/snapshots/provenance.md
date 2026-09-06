# Data Provenance Report

> **Status: ⚠️ BLOCKER — awaiting data owner answer.**
> No training proceeds until every section below is filled in and signed off.
> This is the "unrecoverable mistake" guard (I8): presenting imputed or
> synthetic data as "real Agmarknet-sourced" to a government panel.

---

## 1. Price columns (ModalPrice, MinPrice, MaxPrice, Arrivals)

| Question | Answer |
|---|---|
| Source | *(Agmarknet scrape? Manual entry?)* |
| Date range with real data | *(e.g. 2024-01-23 to YYYY-MM-DD)* |
| Any imputed/synthetic rows? | *(Yes/No — if Yes, which date range?)* |
| Row count with real price | |
| Row count with imputed price | |

## 2. Weather columns (rainfall, temp_anomaly, rain_anomaly, rain_avg_30)

| Question | Answer |
|---|---|
| Source | *(Open-Meteo actuals? Open-Meteo forecast? Synthetic?)* |
| How is "anomaly" computed? | *(Deviation from what baseline? 30-day backward-looking mean? Calendar-month normal?)* |
| Date range with real observations | |
| Any imputed/synthetic values? | *(Yes/No — if Yes, which columns and date range?)* |
| Why is completeness 100% across 367 mandis × 2.6 years? | *(Real weather stations rarely have 0 gaps. Was imputation used?)* |

## 3. Date range edge

| Question | Answer |
|---|---|
| CSV extends to 2026-09-02 ("today") | Is this real recent data, or was the date range extended/generated? |
| Are the most recent 30–60 days of price data real Agmarknet or forward-filled? | |

## 4. Sign-off

| Field | Value |
|---|---|
| Data assembled by | *(name / team)* |
| Date assembled | |
| Provenance confirmed by | *(name)* |
| Date confirmed | |
| Stamped source value | `real` / `imputed` / `mixed` |

---

*This file is committed alongside the model snapshot and referenced by the model card.*
