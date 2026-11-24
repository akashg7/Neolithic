"""Price Engine — loads pre-trained LightGBM SOTA & quantile models at startup.

Provides real price predictions with quantile ranges (p10/p50/p90).

When real Maharashtra SOTA models are present (app/ml/sota_models/),
this delegates to app.ml.sota_models.AgriPricePredictor for high-precision
inference on 129 commodities and 367 Maharashtra APMC mandis.
"""

from __future__ import annotations

import logging
from threading import RLock
from datetime import datetime, timedelta, date

from app.ml.quantile import load_models as load_quantile_models, predict_quantiles, ModelUnavailable

logger = logging.getLogger(__name__)

try:
    from app.ml.sota_models.predictor import AgriPricePredictor
except ImportError:
    AgriPricePredictor = None


class PriceEngine:
    """Singleton — loaded once at app startup via lifespan."""

    _instance = None
    _lock = RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._loaded = False
                cls._instance._sota_predictor = None
            return cls._instance

    def load_models(self) -> None:
        """Called in FastAPI lifespan startup. Loads SOTA & LightGBM pickles."""
        with self._lock:
            if self._loaded:
                return
            self._load_models_once()

    def _load_models_once(self) -> None:
        # 1. Load SOTA Maharashtra Model package if available
        if AgriPricePredictor is not None:
            try:
                self._sota_predictor = AgriPricePredictor()
                self._sota_predictor.load()
                logger.info("Successfully loaded SOTA Maharashtra LightGBM models.")
            except Exception as e:
                logger.warning("Could not load SOTA models: %s", e)
                self._sota_predictor = None

        # 2. Load legacy quantile pickles if present
        try:
            load_quantile_models()
        except Exception as e:
            logger.warning("Could not load quantile models: %s", e)

        self._loaded = True

    def _try_sota_predict(self, mandi: str, commodity: str, days: int = 14,
                          current_price_paise: int | None = None) -> list[dict] | None:
        """Run inference using the trained SOTA Maharashtra models, anchored on
        the observed price when one is given (else the predictor's own default)."""
        if self._sota_predictor is None:
            return None
        try:
            res = self._sota_predictor.predict_range(
                mandi=mandi, commodity=commodity, days=days,
                current_price_rs=(current_price_paise / 100.0) if current_price_paise else None)
            if res and len(res) > 0:
                return res
        except Exception as e:
            logger.warning("SOTA prediction failed for %s @ %s: %s", commodity, mandi, e)
        return None

    def _try_real_predict(self, mandi: str, commodity: str, when: str) -> dict | None:
        """Return real quantiles from SOTA or trained quantile models, or None if unavailable."""
        # 1. Try SOTA first
        sota_res = self._try_sota_predict(mandi, commodity, days=1)
        if sota_res:
            d0 = sota_res[0]
            return {
                "p10_paise": d0["p10_paise"],
                "p50_paise": d0["p50_paise"],
                "p90_paise": d0["p90_paise"],
                "confidence": d0.get("confidence", 0.85),
                "source": "AGMARKNET_SOTA",
                "source_url": "https://agmarknet.gov.in",
            }

        # 2. Try legacy quantile pkl
        try:
            quantiles = predict_quantiles(commodity, mandi, when, horizon=1)
            if quantiles:
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
            pass

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
        mandi_factor = (sum(ord(c) for c in mandi) % 20 - 10) / 100.0
        base = int(base * (1 + mandi_factor))

        p50 = base
        if commodity.lower() == "onion":
            p10 = int(p50 * 0.70)
            p90 = int(p50 * 1.30)
        else:
            p10 = int(p50 * 0.90)
            p90 = int(p50 * 1.10)

        return {
            "p10_paise": p10,
            "p50_paise": p50,
            "p90_paise": p90,
            "confidence": 0.85,
            "source": "SYNTHETIC",
            "source_url": "https://agmarknet.gov.in",
        }

    def predict_range(
        self, mandi: str, commodity: str,
        when: str | date | datetime | None = None,
        days: int = 14,
        current_price_paise: int | None = None,
    ) -> list[dict]:
        """Predict for the next N days. Returns list of daily predictions.

        `current_price_paise` anchors the SOTA trajectory on today's observed
        mandi price; without it the predictor falls back to a crop default."""
        as_of = when if when is not None else datetime.now().isoformat()

        # 1. Try real SOTA Maharashtra LightGBM models first
        sota_range = self._try_sota_predict(mandi, commodity, days=days,
                                            current_price_paise=current_price_paise)
        if sota_range:
            return sota_range

        # 2. Try the multi-horizon pkl model
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

        # 3. Fall back to the synthetic range
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
