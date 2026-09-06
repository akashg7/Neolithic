"""Price Engine — loads pre-trained LightGBM quantile models at startup.

Provides price predictions with quantile ranges (p10/p50/p90).

When real model artifacts are present (app/ml/artifacts/*.pkl), this
delegates to app.ml.quantile.predict_quantiles.  When they are absent it
falls back to a clearly-labelled SYNTHETIC stub so the app still boots.
"""

from __future__ import annotations

from datetime import datetime, timedelta, date

from app.ml.quantile import load_models, predict_quantiles, ModelUnavailable


class PriceEngine:
    """Singleton — loaded once at app startup via lifespan."""

    def __init__(self):
        self._loaded = False

    def load_models(self) -> None:
        """Called in FastAPI lifespan startup. Loads LightGBM pickles."""
        load_models()
        self._loaded = True

    def _try_real_predict(self, mandi: str, commodity: str, when: str) -> dict | None:
        """Return real quantiles from the trained model, or None if unavailable."""
        try:
            quantiles = predict_quantiles(commodity, mandi, when, horizon=1)
            if not quantiles:
                return None
            p10, p50, p90 = quantiles[0]
            return {
                "p10_paise": int(p10),
                "p50_paise": int(p50),
                "p90_paise": int(p90),
                "confidence": 0.85,
                "source": "AGMARKNET_ML",
                "source_url": "https://agmarknet.gov.in",
            }
        except (ModelUnavailable, Exception):
            return None

    def predict(self, mandi: str, commodity: str, when: str | date | datetime) -> dict:
        """Predict today's p10/p50/p90.

        Returns:
          {"p10_paise": int, "p50_paise": int, "p90_paise": int,
           "confidence": float, "source": str, "source_url": str}
        """
        as_of = when if isinstance(when, str) else datetime.now().isoformat()

        # Try real model first.
        real = self._try_real_predict(mandi, commodity, as_of)
        if real is not None:
            return real

        # Fall back to a deterministic, clearly-labelled SYNTHETIC stub.
        base_prices = {
            "wheat": 210000,
            "rice": 250000,
            "onion": 180000,
            "potato": 150000,
            "tomato": 200000,
            "soybean": 380000,
            "soyabean": 380000,
        }
        base = base_prices.get(commodity.lower(), 200000)
        # Deterministic base factor per mandi (not randomised hash seed).
        mandi_factor = (sum(ord(c) for c in mandi) % 20 - 10) / 100.0  # -10% to +10%
        base = int(base * (1 + mandi_factor))

        p50 = base
        if commodity.lower() == "onion":
            p10 = int(p50 * 0.70)  # 30% down
            p90 = int(p50 * 1.30)  # 30% up (Total spread = 6000 bps > 3500 threshold)
        else:
            p10 = int(p50 * 0.90)  # 10% down
            p90 = int(p50 * 1.10)  # 10% up (Total spread = 2000 bps)

        confidence = 0.85  # Fixed confidence for stub

        return {
            "p10_paise": p10,
            "p50_paise": p50,
            "p90_paise": p90,
            "confidence": 0.85,
            "source": "SYNTHETIC",
            "source_url": "https://agmarknet.gov.in",  # Stub
        }

    def predict_range(
        self, mandi: str, commodity: str,
        when: str | date | datetime | None = None,
        days: int = 14,
    ) -> list[dict]:
        """Predict for the next N days. Returns list of daily predictions."""
        as_of = when if when is not None else datetime.now().isoformat()

        # Try the real multi-horizon model.
        try:
            quantiles = predict_quantiles(commodity, mandi, as_of, horizon=days)
            results = []
            base_dt = (
                datetime.fromisoformat(as_of)
                if isinstance(as_of, str) else as_of
            )
            for i, (p10, p50, p90) in enumerate(quantiles):
                fc_date = base_dt + timedelta(days=i + 1)
                results.append({
                    "date": fc_date.strftime("%Y-%m-%d"),
                    "p10_paise": int(p10),
                    "p50_paise": int(p50),
                    "p90_paise": int(p90),
                    "confidence": round(max(0.5, 0.85 - i * 0.02), 2),
                    "source": "AGMARKNET_ML",
                    "source_url": "https://agmarknet.gov.in",
                })
            return results
        except (ModelUnavailable, Exception):
            pass

        # Fall back to the synthetic range.
        base_prediction = self.predict(mandi, commodity, as_of)
        results = []
        base_dt = (
            datetime.fromisoformat(as_of)
            if isinstance(as_of, str) else datetime.now()
        )
        for i in range(days):
            fc_date = base_dt + timedelta(days=i + 1)
            results.append({
                "date": fc_date.strftime("%Y-%m-%d"),
                "p10_paise": base_prediction["p10_paise"],
                "p50_paise": base_prediction["p50_paise"],
                "p90_paise": base_prediction["p90_paise"],
                "confidence": round(max(0.5, base_prediction["confidence"] - i * 0.02), 2),
                "source": "SYNTHETIC",
                "source_url": "https://agmarknet.gov.in",
            })
        return results


# Module-level singleton
price_engine = PriceEngine()
