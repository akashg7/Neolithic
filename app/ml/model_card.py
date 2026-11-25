"""The price model's measured record — one source for every screen.

Recorded from the hold-out evaluation of the LightGBM quantile model
(train 2024-01-23 → 2026-07-31). The verdict card, /ai/forecast and
/ai/model-card all quote these numbers, so they can never disagree.
"""

MODEL_CARD = {
    "mase": 0.5718,               # vs seasonal-naive; < 1 beats the baseline
    "coverage_80_bps": 6960,      # p10–p90 band held the actual price 69.6% of the time
    "algo": "lightgbm_quantile",
    "trained_at": "2026-09-06T19:09:00+05:30",
    "train_rows": 267756,
    "train_from": "2024-01-23",
    "train_to": "2026-07-31",
    "baseline": "seasonal_naive",
}
