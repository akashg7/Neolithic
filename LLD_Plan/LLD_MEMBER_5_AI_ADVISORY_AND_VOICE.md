# Member 5: AI Market Advisory, Warehouse Pledge & Voice Adapter

> **Assigned Team Member:** Member 5  
> **Core Role:** Intelligence, Financial Inclusivity & Adapter Integration Engineer  
> **Execution Priority:** **Step 5 (Executes Fifth)** — Consumes Member 2's `Lot` data; Bridges external AI and provides offline-first voice accessibility.

---

## 1. Domain Responsibility & Scope

Member 5 empowers rural farmers who face low literacy and price opacity:
1. **14-Day Quantile Price Forecasting (`app/engines/price_engine.py`, `app/routers/ai.py`)**: Serving hierarchical quantile models ($p10, p50, p90$) to eliminate distress selling.
2. **Sale Window & Warehouse Pledge Advisory (`app/engines/window_engine.py`)**: Comparing immediate spot sale vs. holding in a WDRA warehouse with pledge loan financing.
3. **Trilingual Voice Assistant Adapter (`app/engines/voice_engine.py`, `app/src/voice/`)**: Integrating Sarvam AI for Marathi (`mr-IN`) and Hindi (`hi-IN`) Speech-to-Text and Text-to-Speech with local disk caching.

---

## 2. Assigned Database Models (7 Tables)

Member 5 owns the following models in [`app/models/`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/models/):

| Model Name | Table Name | Purpose | Key Attributes & Foreign Keys |
| :--- | :--- | :--- | :--- |
| **`PriceForecast`** | `price_forecasts` | 14-day quantile predictions | `id` (PK), `mandi_id`, `commodity_id`, `forecast_date`, `p10_paise`, `p50_paise`, `p90_paise`, `confidence` |
| **`PriceObservation`**| `price_observations`| Real mandi spot prices | `id` (PK), `mandi_id`, `commodity_id`, `observation_date`, `modal_price_paise`, `arrivals_mt` |
| **`ModelRun`** | `model_runs` | ML evaluation logs | `id` (PK), `commodity_id`, `mase_score`, `trained_at`, `model_path` |
| **`PledgeQuoteRecord`**| `pledge_quotes` | Warehouse loan quotes | `id` (PK), `lot_id`, `warehouse_id`, `assessed_value_paise`, `loan_amount_paise`, `interest_rate_bps` |
| **`CallSession`** | `call_sessions` | Farmer voice calls | `id` (PK), `farmer_id`, `started_at`, `status` (`active`, `completed`) |
| **`VoiceInteraction`**| `voice_interactions`| Audio turns & transcripts | `id` (PK), `session_id`, `input_audio_url`, `transcript_marathi`, `intent_detected`, `response_audio_url` |
| **`LogisticsProvider`**|`logistics_providers`| Transport & Storage | `id` (PK), `name`, `type` (`storage`, `transport`), `district`, `geom` (Point) |

---

## 3. Assigned REST APIs (Endpoints & Contracts)

Member 5 owns [`app/routers/ai.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/ai.py) and [`app/routers/voice.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/voice.py):

| Method | Endpoint | Request Payload | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/ai/forecast` | `?mandi=Lasalgaon&commodity=Onion` | `ForecastRes` | Returns 14-day $p10, p50, p90$ price curves |
| `POST` | `/api/v1/ai/window/recommend`| `{"commodity_id": "Onion", "qty_kg": 5000, "current_price_paise": 220000}` | `WindowRes` | Returns "SELL NOW" vs "HOLD", storage costs, and pledge loan quote |
| `POST` | `/api/v1/voice/transcribe` | *Form-Data: audio file (wav)* | `TranscribeOut`| Sarvam AI Speech-to-Text in Marathi/Hindi |
| `POST` | `/api/v1/voice/narrate` | `{"text": "तुमचा माल ए-ग्रेड आहे", "language": "mr-IN"}` | `AudioOut (WAV)` | Synthesizes advisory audio narration |
| `GET` | `/api/v1/logistics/nearby` | `?lat=20.14&lng=74.23&radius_km=50` | `LogisticsNearbyOut` | Fetches nearby WDRA warehouses and trucks |

---

## 4. GoF Design Patterns Implementation

### Pattern 1: Adapter Pattern (Structural)
- **Problem Solved**: Third-party voice APIs (Sarvam AI, Google Speech, Bhashini) have distinct SDKs and network requirements. Tightly coupling router handlers to Sarvam AI makes unit testing impossible and creates vendor lock-in.
- **Implementation**:
  - `IVoiceProvider` (Domain interface defining `transcribe(audio_bytes) -> str` and `synthesize(text, lang) -> bytes`).
  - `SarvamVoiceAdapter` (Concrete adapter invoking Sarvam AI REST API).
  - `MockVoiceAdapter` (In-memory adapter used for offline runs and test suites).

```python
# app/adapters/voice_adapter.py
from abc import ABC, abstractmethod
import httpx

class IVoiceProvider(ABC):
    @abstractmethod
    async def speech_to_text(self, audio_bytes: bytes, language_code: str) -> str: pass

    @abstractmethod
    async def text_to_speech(self, text: str, language_code: str) -> bytes: pass

class SarvamVoiceAdapter(IVoiceProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.sarvam.ai"

    async def speech_to_text(self, audio_bytes: bytes, language_code: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/speech-to-text",
                headers={"api-subscription-key": self.api_key},
                files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                data={"language_code": language_code}
            )
            return resp.json().get("transcript", "")

    async def text_to_speech(self, text: str, language_code: str) -> bytes:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/text-to-speech",
                headers={"api-subscription-key": self.api_key},
                json={"inputs": [text], "target_language_code": language_code}
            )
            return resp.content

class MockVoiceAdapter(IVoiceProvider):
    async def speech_to_text(self, audio_bytes: bytes, language_code: str) -> str:
        return "कांदा बाजार भाव काय आहे"  # "What is the onion market price?"

    async def text_to_speech(self, text: str, language_code: str) -> bytes:
        return b"RIFFfake_wav_audio_payload"
```

### Pattern 2: Decorator Pattern (Structural)
- **Problem Solved**: In rural mandi environments with spotty 2G internet, live TTS calls take 3+ seconds and fail frequently. Fixed sentences (e.g. "Your produce is Grade A") should play instantly without hitting the external API.
- **Implementation**: `CachedVoiceDecorator` wraps any `IVoiceProvider`, checks disk cache by hashing the text string, and only calls the real adapter on a cache miss:

```python
# app/adapters/cached_voice_decorator.py
import hashlib
import os
from app.adapters.voice_adapter import IVoiceProvider

class CachedVoiceDecorator(IVoiceProvider):
    def __init__(self, wrapped: IVoiceProvider, cache_dir: str = "/tmp/audio_cache"):
        self.wrapped = wrapped
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_hash_path(self, text: str, lang: str) -> str:
        h = hashlib.sha256(f"{lang}:{text}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.wav")

    async def speech_to_text(self, audio_bytes: bytes, language_code: str) -> str:
        return await self.wrapped.speech_to_text(audio_bytes, language_code)

    async def text_to_speech(self, text: str, language_code: str) -> bytes:
        path = self._get_hash_path(text, language_code)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()  # CACHE HIT: Instant return (<5ms)
        
        # CACHE MISS: Invoke upstream adapter & cache result
        audio = await self.wrapped.text_to_speech(text, language_code)
        with open(path, "wb") as f:
            f.write(audio)
        return audio
```

### Pattern 3: Singleton Pattern (Creational)
- **Problem Solved**: Loading LightGBM model weights from disk takes ~1.5 seconds. Instantiating a new model on every HTTP request would destroy latency.
- **Implementation**: `PriceEngine` is instantiated once as a module-level singleton in [`app/engines/price_engine.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/engines/price_engine.py):

```python
# app/engines/price_engine.py
class PriceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.models = {}
            cls._instance.is_loaded = False
        return cls._instance

    def load_models(self):
        if not self.is_loaded:
            # Load LightGBM booster weights once into memory
            self.is_loaded = True

price_engine = PriceEngine()  # Global Singleton
```

---

## 5. SOLID Principles Proof Matrix (Member 5)

1. **Single Responsibility Principle (SRP)**:
   - `SarvamVoiceAdapter` handles API transport; `CachedVoiceDecorator` handles disk persistence; `WindowEngine` handles net economic gain calculation.
2. **Open/Closed Principle (OCP)**:
   - To integrate Google Cloud Text-to-Speech or Bhashini, we write `GoogleVoiceAdapter(IVoiceProvider)` without changing a single line in `voice.py` or `CachedVoiceDecorator`.
3. **Liskov Substitution Principle (LSP)**:
   - `MockVoiceAdapter` substitutes `SarvamVoiceAdapter` in automated test suites without any runtime discrepancies.
4. **Interface Segregation Principle (ISP)**:
   - `IVoiceProvider` exposes only the 2 methods the client needs (`speech_to_text` and `text_to_speech`).
5. **Dependency Inversion Principle (DIP)**:
   - High-level voice endpoints depend on the abstraction `IVoiceProvider` rather than hardcoded `SarvamVoiceAdapter`.

---

## 6. Pytest Automated Test Suite

Save in `tests/test_member_5_ai_voice.py`:

```python
import pytest
from app.adapters.voice_adapter import MockVoiceAdapter
from app.adapters.cached_voice_decorator import CachedVoiceDecorator
import os

@pytest.mark.asyncio
async def test_cached_voice_decorator_hit(tmp_path):
    mock = MockVoiceAdapter()
    decorator = CachedVoiceDecorator(mock, cache_dir=str(tmp_path))

    text = "कांदा बाजार भाव"
    lang = "mr-IN"

    # First call: Cache miss, writes to disk
    audio_1 = await decorator.text_to_speech(text, lang)
    assert audio_1 == b"RIFFfake_wav_audio_payload"
    assert len(os.listdir(tmp_path)) == 1

    # Second call: Cache hit, reads directly from disk
    audio_2 = await decorator.text_to_speech(text, lang)
    assert audio_2 == audio_1

def test_quantile_non_crossing_invariant():
    """Verify p10 <= p50 <= p90 holds true across all forecast horizons."""
    from app.engines.price_engine import price_engine
    forecasts = price_engine.predict_range("Lasalgaon APMC", "Onion", days=14)
    for day in forecasts:
        assert day["p10_paise"] <= day["p50_paise"] <= day["p90_paise"], "Quantiles must never cross!"
```

---

## 7. Faculty Viva Defense Guide (Member 5)

* **Faculty Q: "Why did you use the Decorator Pattern for the voice cache instead of just putting caching logic inside the adapter?"**
  * *Answer:* *"Putting caching inside `SarvamVoiceAdapter` violates the Single Responsibility Principle by mixing network transport with disk caching. With the Decorator Pattern, `CachedVoiceDecorator` wraps any `IVoiceProvider`. If we tomorrow switch the underlying voice engine from Sarvam AI to Google Cloud TTS or Microsoft Azure Speech, our caching layer works immediately without touching a line of caching code."*

* **Faculty Q: "What is Quantile Crossing, and how does your architecture prevent it?"**
  * *Answer:* *"If you train 3 separate regression models for the 10th, 50th, and 90th percentiles, numerical instability often causes $p10$ to be higher than $p50$, which is mathematically invalid and confuses farmers. Our engine uses a hierarchical structure: it predicts the median trajectory ($p50$), and then predicts a parametric volatility tunnel ($\sigma$). By calculating $p10 = p50 - 1.28\sigma$ and $p90 = p50 + 1.28\sigma$, we mathematically guarantee that $p10 \le p50 \le p90$ across all 14 forecast days."*

