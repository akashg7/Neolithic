# 🌾 AgriSense Intelligence Hub — Complete Product Overview

> **Hybrid-AgriPrice-Forecaster | The Future of Agricultural Decision Intelligence**
>
> *Developed by: Karthik Reddy (230035) & Akash G (230098)*
> *B.Tech Computer Science & AI — 2024–2026*

---

## 1. What is AgriSense AI?

**AgriSense AI** is a production-grade, hybrid artificial intelligence platform that acts as a **unified decision-support system** for Indian farmers, traders, and agricultural stakeholders. It combines deep learning, gradient boosting, and computer vision into a single, modular platform to tackle the three pillars of agricultural risk:

| Pillar | Intelligence Layer | What It Does |
| :--- | :--- | :--- |
| 💰 **Economic** | Price Intelligence | 14-day multi-horizon price forecasting with probabilistic risk corridors |
| 🌿 **Ecological** | Crop Intelligence | Soil-climate synergistic crop recommendations optimized for profitability |
| 🦠 **Biological** | Disease Intelligence | Real-time plant disease detection from leaf images with visual explainability |

The platform is deployed as a **Next.js Premium Dashboard** backed by a **FastAPI Modular Hub**, with all AI models encapsulated in a hot-swappable `Engines/` architecture.

---

## 2. The Problem — Why This Product Exists

### 2.1 The Crisis in Indian Agriculture

Indian agriculture feeds 1.4 billion people, yet the farmers who sustain it operate in one of the most volatile and information-starved environments in the world. The problems are systemic and interconnected:

#### 🔴 Problem 1: Extreme Price Volatility
- Perishable commodities like **Onion and Tomato** experience **200–400% price swings** within weeks.
- Farmers make selling decisions based on outdated information from local brokers, often leading to **distress sales** at rock-bottom prices.
- **₹92,000+ crore (~$11 billion)** is lost annually in post-harvest waste due to poor market timing (*NITI Aayog, 2019*).

#### 🔴 Problem 2: Information Asymmetry
- Over **86% of Indian farmers are small and marginal landholders** with no access to real-time market intelligence tools.
- Existing government portals (like Agmarknet) provide only historical raw data — no forecasts, no trends, no actionable advice.
- Farmers cannot answer the most basic questions: *"Should I sell today or hold for a week?"*

#### 🔴 Problem 3: Crop Selection Blindness
- Farmers repeat the same crops year after year without scientific soil-climate analysis, leading to soil degradation and economic inefficiency.
- No system exists that combines **biological suitability** (what can grow) with **economic viability** (what will be profitable) in a single recommendation.

#### 🔴 Problem 4: Undetected Crop Diseases
- Plant diseases cause **20–40% yield loss globally** (*FAO, 2021*).
- Early-stage diseases are invisible to the untrained eye, and by the time symptoms are obvious, the damage is irreversible.
- Rural farmers have **zero access** to pathology experts for timely diagnosis.

#### 🔴 Problem 5: No Unified Platform
- Existing tools address these problems in isolation — a price tracker here, a weather app there, a disease identification tool somewhere else.
- There is **no single platform** that unifies price forecasting, crop recommendation, and disease detection into one coherent advisory system.

---

## 3. Our Aim — What We Set Out to Build

### The Core Objective
> **Build a single, production-ready AI platform that empowers Indian farmers with three layers of predictive intelligence — economic, ecological, and biological — to reduce financial risk and maximize agricultural productivity.**

### Specific Goals

| # | Goal | Target |
| :---: | :--- | :--- |
| 1 | Build a **multi-horizon price forecaster** that predicts commodity prices 14 days into the future with probabilistic risk intervals | > 90% accuracy on SMAPE |
| 2 | Create a **crop recommendation engine** that combines soil-climate analysis with predicted market prices to suggest the most profitable crop | > 95% F1-Score |
| 3 | Develop a **plant disease detection system** using computer vision that can identify 38 disease classes from leaf images in real-time | > 95% accuracy |
| 4 | Unify all modules into a **single, modular, deployable platform** with a premium user interface | Full-stack deployment |
| 5 | Ensure **interpretability and transparency** — not just predictions, but *why* the model made that prediction | Grad-CAM + Attention Weights |
| 6 | Validate against baselines and **zero-shot foundation models** to prove domain-specific training is essential | Outperform Moirai zero-shot |

---

## 4. What We Built — The Solution Architecture

### 4.1 The Decoupled Engine Pattern
We engineered a **Modular Micro-Engine Architecture** where each AI model operates as an independent, hot-swappable engine:

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend Dashboard                │
│              (Premium Dark-Mode Unified Interface)           │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│              AgriSense Hub Backend (FastAPI)                  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ TFT      │ │ LightGBM │ │ Crop     │ │ Disease       │  │
│  │ Engine   │ │ Engine   │ │ Engine   │ │ Engine        │  │
│  │          │ │          │ │          │ │               │  │
│  │ 96.15%   │ │ 91.20%   │ │ F1: 0.99 │ │ 98.42%        │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js (React) | Premium dark-mode dashboard |
| **Backend** | FastAPI (Python) | Modular API hub orchestrating all engines |
| **Deep Learning** | PyTorch, PyTorch Lightning, PyTorch Forecasting | TFT time-series forecasting |
| **Machine Learning** | LightGBM, scikit-learn | Gradient boosting for tabular data |
| **Computer Vision** | TensorFlow, Keras, EfficientNet-B0 | Disease classification + Grad-CAM |
| **Data Engineering** | Pandas, NumPy | Feature engineering pipeline |
| **External APIs** | Agmarknet, NASA POWER, IndianCities | Market data, weather, geolocation |
| **Deployment** | Docker | Containerized production deployment |

---

## 5. The AI Models — Deep Dive

### 5.1 Price Intelligence (Dual-Track Forecasting)

We implemented a **dual-model strategy** because no single model excels at everything:

#### 🏆 Primary Engine: Temporal Fusion Transformer (TFT)
The TFT is a Google Research architecture designed specifically for multi-horizon forecasting with heterogeneous inputs.

| Component | Description |
| :--- | :--- |
| **Variable Selection Networks (VSN)** | Automatically prunes redundant features — if rainfall matters this season but not the next, VSN adapts |
| **Gated Residual Networks (GRN)** | Lets the model skip complexity when relationships are simple, preventing overfitting |
| **Interpretable Multi-Head Attention** | Focuses on specific long-range temporal patterns (e.g., "what happened exactly 1 year ago?") |
| **Quantile Outputs** | Predicts 10th, 50th, and 90th percentiles — giving farmers worst-case, expected, and best-case price scenarios |

**Configuration (Production — Epoch 15):**
- Hidden Size: **128** (scaled from initial 16)
- Context Window: **60 days** lookback
- Prediction Horizon: **14 days** ahead
- Dropout: **0.20**
- Loss Function: Quantile Loss (7 quantiles)

#### ⚡ Secondary Engine: LightGBM (GOSS-Optimized)
A gradient boosting decision tree optimized for ultra-fast inference on tabular data.

- Optimized with **GOSS** (Gradient-based One-Side Sampling) and **EFB** (Exclusive Feature Bundling)
- Handles high-cardinality categorical features (Mandi IDs, District names) natively
- Inference speed: **< 100ms** per mandi-commodity pair

#### 🧪 Experimental: Salesforce Moirai (Zero-Shot)
We tested the state-of-the-art zero-shot foundation model to validate whether localized fine-tuning is necessary.

- **Result: Failed.** MAE ~543 vs LightGBM's 160.41
- **Conclusion:** Zero-shot models cannot capture the hyper-local dynamics of Indian agricultural markets. Domain-specific training is non-negotiable.

---

### 5.2 Ecological Intelligence (Crop Recommendation)

A **Leaf-wise Gradient Boosting Decision Tree (LightGBM/GBDT)** classifier that determines the best crop based on soil and climate conditions.

**Innovation — Profitability Fusion:**
Unlike existing systems that only consider biological suitability, our engine **cross-references crop recommendations with the 14-day price forecast** to recommend the most *profitable* option. A biologically perfect crop is worthless if its market price has crashed.

**Feature Engineering (from 7 → 45+ features):**
- Raw inputs: N, P, K, Temperature, Humidity, pH, Rainfall
- Engineered: `n_ratio`, `p_ratio`, `dominant_nutrient`, `nutrient_balance`, `aridity_index`, `heat_index`, `rainfall_regime`, `ph_regime`, `temp_regime`
- Dataset: 2,200 observations across 22 crop classes (perfectly balanced — 100 per class)

---

### 5.3 Biological Intelligence (Disease Detection)

An **EfficientNet-B0** transfer learning pipeline with **Grad-CAM** interpretability.

**Why EfficientNet-B0:**
- Uses **Compound Scaling** (Width × Depth × Resolution) to be 100× smaller than VGG-16 while maintaining superior accuracy
- Only **5.3MB** in size — deployable on edge devices and smartphones
- **MBConv blocks** with depth-wise separable convolutions for computational efficiency
- **Squeeze-and-Excitation (SE) blocks** act as "volume knobs" that amplify diseased regions and suppress healthy background

**Training Strategy:**
- Phase 1: Frozen backbone — train only the classification head
- Phase 2: Unfreeze top layers — fine-tune on plant-specific disease features
- Dataset: **87,000+ images** across **38 classes** (merged from two Kaggle datasets with perceptual hashing for deduplication)

---

## 6. Data Engineering — The Hidden Engine

### 6.1 Data Collection Pipeline

| Source | Method | Data Volume |
| :--- | :--- | :--- |
| **Agmarknet** (Market Prices) | Custom reverse-engineered API scraper | Daily data, Jan 2024 – Dec 2025, 10 commodities |
| **NASA POWER** (Weather) | Parallelized REST API collector | 7 weather parameters per district per day |
| **IndianCities** (Geolocation) | Fuzzy matching with Levenshtein Distance | Lat/Lon for every mandi district |
| **Kaggle** (Crop Data) | Direct download | 2,200 soil-climate samples |
| **Kaggle** (Disease Images) | Merged + deduplicated | 87,000+ leaf images |

### 6.2 Feature Engineering (20 → 70+ Features)

Raw market data was expanded through massive dimensionality amplification:

| Category | Features | Examples |
| :--- | :--- | :--- |
| **Temporal** | Calendar + Fourier | `day`, `month`, `is_weekend`, `sin1`, `cos1` |
| **Price Dynamics** | Lags + Rolling Stats | 1/3/7/14/30-day lags, rolling mean/std, `zscore_7`, `momentum_7` |
| **Supply Dynamics** | Arrival Analysis | `arrivals_lag_1`...`14`, `arrival_change_7`, `arrivals_avg_30` |
| **Environmental** | Anomaly Detection | `temp_anomaly`, `rain_anomaly`, `rain_intensity` |
| **Spatial** | Geographic Embeddings | `lat_sin`, `lat_cos`, `lon_sin`, `lon_cos` |

---

## 7. Results & Accuracy — What We Achieved

### 7.1 Price Forecasting Results

#### TFT (Production — Epoch 15, Heavy Architecture)

| Metric | Value |
| :--- | ---: |
| **Accuracy (1 - SMAPE)** | **96.15%** |
| **SMAPE** | **3.85%** |
| **RMSE** | **155.96** |
| **MAE** | **78.89 ₹/qtl** |
| **Prediction Horizon** | **14 days** |
| **Confidence** | High (Momentum Signal: +1.0) |

> **What this means:** For a commodity priced at ₹2,000/qtl, our prediction is off by only ₹78.89 on average — a 3.85% error across a 14-day horizon. The farmer also gets worst-case and best-case price corridors for risk planning.

#### LightGBM (Benchmark — GOSS-Optimized)

| Metric | Value |
| :--- | ---: |
| **Accuracy (1 - SMAPE)** | **91.20%** |
| **SMAPE** | **8.80%** |
| **MAE** | **160.41 ₹/qtl** |
| **RMSE** | **355.80** |
| **Inference Speed** | **< 100ms** |
| **Test Rows** | **56,826** |

#### Moirai Zero-Shot (Experimental — Failed)

| Metric | Value |
| :--- | ---: |
| **MAE** | **~543 ₹/qtl** |
| **SMAPE** | **~24.10%** |
| **Verdict** | ❌ Outperformed by both domain-specific models |

#### Comparative Summary (Price Track)

| Model | Accuracy | MAE (₹/qtl) | RMSE | Strengths |
| :--- | ---: | ---: | ---: | :--- |
| **TFT (Epoch 15)** | **96.15%** | **78.89** | **155.96** | Probabilistic quantiles, multi-horizon, interpretable |
| **LightGBM** | **91.20%** | **160.41** | **355.80** | Ultra-fast inference, tabular data champion |
| **Moirai (Zero-Shot)** | ~75.90% | ~543 | — | Zero-shot (no training needed) |
| **Naive Baseline** | 86.86% | 344.36 | 799.32 | Simple carry-forward (no ML) |

> **Key Insight:** TFT achieved a **75% reduction in RMSE** from its initial prototype (Epoch 9: RMSE 647.88) to production (Epoch 15: RMSE 155.96) through architectural scaling (hidden_size 16→128, context window 14→60 days).

---

### 7.2 Crop Recommendation Results

| Metric | Score |
| :--- | ---: |
| **F1-Score (Macro)** | **0.99** |
| **Accuracy** | **> 99%** |
| **Classes** | **22 crops** |
| **Feature Expansion** | 7 raw → 45+ engineered features |

> **Honest Assessment:** The near-perfect score is partly a result of the noiseless Kaggle benchmark dataset. In real-world deployment with sensor noise, we expect a 5–10% degradation. However, the feature engineering strategy (nutrient ratios, climate regimes, aridity indices) demonstrably outperforms raw-input baselines.

---

### 7.3 Plant Disease Detection Results

| Metric | Score |
| :--- | ---: |
| **Accuracy** | **98.42%** |
| **Precision (Weighted)** | **98.45%** |
| **Recall (Weighted)** | **98.42%** |
| **F1-Score (Weighted)** | **98.43%** |
| **Healthy vs. Diseased Recall** | **~99.8%** |
| **Dataset Size** | **87,000+ images** |
| **Classes** | **38** |
| **Test Images** | **~13,050 unseen** |

> **Interpretability:** Grad-CAM heatmaps confirm the model focuses on **lesion contours and discoloration** — not background noise — validating biological relevance.

> **Confusion Patterns:** Primary errors occur between visually identical lesions (e.g., *Potato Early Blight* vs. *Tomato Early Blight* in early stages), which is also challenging for trained pathologists.

---

### 7.4 Consolidated Results Dashboard

| Module | Model | Primary Metric | Result | Status |
| :--- | :--- | :--- | ---: | :--- |
| **Price Forecasting** | TFT (Epoch 15) | Accuracy (1-SMAPE) | **96.15%** | ✅ Production |
| **Price Forecasting** | LightGBM | Accuracy (1-SMAPE) | **91.20%** | ✅ Production |
| **Crop Recommendation** | GBDT (LightGBM) | F1-Score | **0.99** | ✅ Production |
| **Disease Detection** | EfficientNet-B0 | Accuracy | **98.42%** | ✅ Production |
| **Zero-Shot Baseline** | Salesforce Moirai | MAE | ~543 ₹/qtl | ❌ Rejected |

---

## 8. Problems Solved — Impact Summary

| Problem | How We Solved It | Impact |
| :--- | :--- | :--- |
| **Price Volatility** | 14-day probabilistic forecasting with TFT quantile corridors | Farmers can plan sales timing; reduces distress sales |
| **Information Asymmetry** | Unified dashboard with real-time price intelligence | Democratizes market intelligence for small farmers |
| **Crop Selection Blindness** | Soil-climate recommendation fused with price forecasts | Farmers grow the most **profitable** crop, not just any viable one |
| **Undetected Diseases** | 98.42% accurate leaf image diagnosis with Grad-CAM | Early detection saves 20–40% yield loss |
| **Fragmented Tools** | Single modular platform unifying all three tracks | One app replaces five separate tools |
| **Black Box AI Distrust** | Grad-CAM heatmaps + Attention weights + Quantile corridors | Every prediction comes with visual/statistical justification |
| **Zero-Shot Model Hype** | Proved domain-specific training is essential (Moirai failed) | Validates localized training approach for Indian markets |

---

## 9. Key Innovations & Technical Contributions

1. **Dual-Track Forecasting Strategy** — First system to combine TFT (probabilistic, multi-horizon) with LightGBM (deterministic, ultra-fast) for agricultural price prediction in a single platform.

2. **Profitability-Fused Crop Recommendation** — Goes beyond biological suitability by crossing crop viability with predicted 14-day market prices to recommend the most economically optimal crop.

3. **70+ Feature Engineering Pipeline** — Expanded raw 20-column market data into 70+ engineered features capturing temporal cycles (Fourier), price psychology (momentum, z-scores), supply shocks (arrival changes), and environmental anomalies.

4. **Reverse-Engineered Agmarknet Scraper** — Built a custom scraper to extract daily mandi prices from India's government portal (which has no bulk download API), covering Jan 2024 – Dec 2025 across 10 commodities.

5. **NASA Weather Fusion** — Enriched market data with hyper-local meteorological signals (temperature, rainfall, humidity, solar radiation, wind speed) from NASA POWER API, enabling the model to detect weather-driven price shocks 7–14 days before they manifest.

6. **Decoupled Engine Architecture** — All models are hot-swappable; weights can be updated (Epoch 9 → Epoch 15) without changing a single line of API or frontend code.

7. **Interpretability-First Design** — Grad-CAM for disease detection and VSN attention weights for price forecasting ensure every prediction is auditable and transparent.

---

## 10. Literature Foundation

| Reference | Relevance to Our Work |
| :--- | :--- |
| **Lim et al. (2021)** — *Temporal Fusion Transformers*, Int. J. Forecasting | Core TFT architecture; recommended hidden_size=160+ (we used 128) |
| **Grinsztajn et al. (2022)** — *Why tree-based models outperform DL on tabular data*, NeurIPS | Justifies our dual-track approach (LightGBM for tabular, TFT for sequences) |
| **Woo et al. (2024)** — *Unified Time Series Transformers* (Moirai), ICML | Zero-shot baseline; our results confirm localized training is essential |
| **Makridakis et al. (2018)** — *Forecasting methods: Concerns and ways forward*, PLOS ONE | Validates the importance of comparing against strong naive baselines |
| **Tan & Le (2019)** — *EfficientNet: Rethinking Model Scaling*, ICML | Foundation for our disease detection backbone; compound scaling principle |
| **Chand (2012)** — *Development Policies and Agricultural Markets*, EPW | Documents India's agricultural price volatility crisis |
| **NITI Aayog (2019)** — *Demand and Supply Projections Towards 2033* | Quantifies the ~$8B annual post-harvest loss problem |

---

## 11. Evolution Journey — From Prototype to Production

| Phase | What Changed | Accuracy Impact |
| :--- | :--- | :--- |
| **Phase 1: Prototype** | LightGBM only, basic features, no weather data | ~85% |
| **Phase 2: Multi-Model** | Added TFT (hidden_size=16), Moirai experiment, weather fusion | TFT: 86.59%, LGBM: 91.20% |
| **Phase 3: Production** | Scaled TFT (hidden_size=128, 60-day context), added disease + crop modules, built unified dashboard | **TFT: 96.15%**, Disease: **98.42%**, Crop F1: **0.99** |

> **The critical scaling decision:** Increasing TFT's hidden_size from 16 to 128 and context window from 14 to 60 days resulted in a **~10 percentage point accuracy improvement** (86.59% → 96.15%) and a **76% RMSE reduction** (647.88 → 155.96).

---

## 12. API Endpoints

The FastAPI backend exposes four clean endpoints:

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/api/tft/predict` | `POST` | 14-day probabilistic price forecast with quantile corridors |
| `/api/lgbm/predict` | `POST` | Ultra-fast deterministic price point prediction |
| `/api/crop/recommend` | `POST` | Profitability-optimized crop recommendation |
| `/api/disease/detect` | `POST` | Plant disease classification from leaf image upload |

---

## 13. Future Roadmap

| Initiative | Description | Expected Impact |
| :--- | :--- | :--- |
| **Hyper-Local IoT Integration** | Village-level weather station data instead of NASA satellite data | More granular weather signals |
| **Continuous Learning** | Streaming LightGBM updates without full retraining | Always up-to-date predictions |
| **Edge Deployment** | Quantized EfficientNet-B0 for offline mobile inference | Works in areas with no internet |
| **Multi-Language Dashboard** | Hindi, Telugu, Tamil, Marathi support | Accessible to non-English farmers |
| **Supply Chain Integration** | Direct integration with FPO (Farmer Producer Org) logistics | From prediction to action |

---

## 14. Conclusion

AgriSense Intelligence Hub demonstrates that **hybrid AI architectures** — combining the probabilistic power of deep learning (TFT), the tabular efficiency of gradient boosting (LightGBM), and the visual intelligence of convolutional networks (EfficientNet) — can be unified into a single, production-ready platform to address the multi-dimensional challenges of Indian agriculture.

**By the numbers:**
- 📈 **96.15%** price forecasting accuracy across a 14-day horizon
- 🌾 **0.99 F1-Score** on crop recommendation with profitability fusion
- 🔬 **98.42%** disease detection accuracy across 38 classes
- ⚡ **< 100ms** inference latency for real-time dashboard interactions
- 📊 **70+ engineered features** from 5 different data sources
- 🔍 **Full interpretability** through Grad-CAM and attention visualization

This is not just a model — it is a **complete decision-support ecosystem** that gives Indian farmers the intelligence they need to reduce financial risk, maximize yield, and make data-driven agricultural decisions.

---

*AgriSense Intelligence Hub — Precision Agriculture Through Hybrid Intelligence.*
