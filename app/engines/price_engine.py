"""
Price Engine — Loads pre-trained TFT + LightGBM models at startup.
Provides price predictions with quantile ranges (p10/p50/p90).

NOTE: This is a stub implementation using mock data. Replace with real model
inference once Nikhil integrates the trained model artifacts.
"""
import random
from datetime import datetime, timedelta


class PriceEngine:
    """Singleton — loaded once at app startup via lifespan."""

    def __init__(self):
        self.tft_model = None
        self.lgbm_model = None
        self._loaded = False

    def load_models(self):
        """Called in FastAPI lifespan startup."""
        # TODO: Load real models when available
        # self.tft_model = tf.saved_model.load("ai_models/tft_model")
        # with open("ai_models/lgbm_model.pkl", "rb") as f:
        #     self.lgbm_model = pickle.load(f)
        self._loaded = True

    def predict(self, mandi: str, commodity: str, date: str) -> dict:
        """
        Returns:
          {
            "p10_paise": int,
            "p50_paise": int,
            "p90_paise": int,
            "confidence": float  # 0.0 to 1.0
          }

        STUB: Returns realistic mock predictions until real models are integrated.
        """
        # Base prices by commodity (paise per quintal)
        base_prices = {
            "wheat": 210000,
            "rice": 250000,
            "onion": 180000,
            "potato": 150000,
            "tomato": 200000,
            "soybean": 380000,
        }
        base = base_prices.get(commodity.lower(), 200000)

        # Add some variation based on mandi name hash
        mandi_factor = (hash(mandi) % 20 - 10) / 100  # -10% to +10%
        base = int(base * (1 + mandi_factor))

        p50 = base
        p10 = int(p50 * 0.90)  # 10th percentile
        p90 = int(p50 * 1.10)  # 90th percentile
        confidence = round(random.uniform(0.70, 0.92), 2)

        return {
            "p10_paise": p10,
            "p50_paise": p50,
            "p90_paise": p90,
            "confidence": confidence,
        }

    def predict_range(self, mandi: str, commodity: str, days: int = 14) -> list[dict]:
        """Predict for the next N days. Returns list of daily predictions."""
        results = []
        base_prediction = self.predict(mandi, commodity, datetime.now().isoformat())

        for i in range(days):
            date = datetime.now() + timedelta(days=i + 1)
            # Slight trend upward with noise
            trend = 1 + (i * 0.003) + (random.uniform(-0.02, 0.02))
            results.append({
                "date": date.strftime("%Y-%m-%d"),
                "p10_paise": int(base_prediction["p10_paise"] * trend),
                "p50_paise": int(base_prediction["p50_paise"] * trend),
                "p90_paise": int(base_prediction["p90_paise"] * trend),
                "confidence": round(max(0.5, base_prediction["confidence"] - i * 0.02), 2),
            })

        return results


# Module-level singleton
price_engine = PriceEngine()
