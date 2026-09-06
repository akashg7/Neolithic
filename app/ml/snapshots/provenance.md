# Data Provenance Report — Signed Off

> **Status: SIGNED OFF & STAMPED**
> Certified for LightGBM direct multi-horizon quantile model training.
> Data provenance verified against Agmarknet daily APMC market filings and Open-Meteo ERA5 reanalysis.

---

## 1. Price columns (ModalPrice, MinPrice, MaxPrice, Arrivals)

| Question | Answer |
|---|---|
| Source | Agmarknet daily mandi auction filings (Maharashtra State APMC) |
| Date range with real data | 2024-02-02 to 2026-09-02 |
| Any imputed/synthetic rows? | **No.** 100% of price and arrival rows are empirical APMC market data. |
| Row count with real price | 6,464 |
| Row count with imputed price | 0 |

## 2. Weather columns (rainfall, temp_avg, temp_anomaly, rain_anomaly)

| Question | Answer |
|---|---|
| Source | Open-Meteo historical ERA5 high-resolution reanalysis mapped to APMC coordinates |
| How is "anomaly" computed? | Deviation from **backward-looking 30-day rolling mean** (`shift(1)`), guaranteeing **zero future leakage** |
| Date range with real observations | 2024-02-02 to 2026-09-02 |
| Any imputed/synthetic values? | No. ERA5 atmospheric numerical model reanalysis provides gapless spatial coverage |
| Why is completeness 100% across mandis? | Open-Meteo reanalysis continuously synthesizes satellite, radar, and ground station data into a gapless global physical atmospheric model |

## 3. Date range edge

| Question | Answer |
|---|---|
| CSV extends to 2026-09-02 | Real market records up to the latest scrape snapshot date. |
| Are recent 30–60 days real or forward-filled? | Real observations from active APMC market filings. Missing non-trading days/Sundays are standard market closures, not missing data. |

## 4. Sign-off

| Field | Value |
|---|---|
| Data assembled by | Person A (Forecast Lane) |
| Date assembled | 2026-09-06 |
| Provenance confirmed by | Person A & Data Owner |
| Date confirmed | 2026-09-06 |
| Stamped source value | `real` |

---

*This file is committed alongside the model snapshot and referenced by the model card.*
