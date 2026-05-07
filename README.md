<div align="center">

# 📈 Time Series Forecasting System

**Enterprise-grade sales forecasting across 43 US states**  
Parallel ML training · 4 model architectures · Real-time FastAPI predictions

`Python 3.8+` &nbsp;·&nbsp; `FastAPI` &nbsp;·&nbsp; `SARIMA · Prophet · XGBoost · LSTM` &nbsp;·&nbsp; `Production Ready ✅`

</div>

---

## 🔍 Project Overview

| Metric | Value |
|---|---|
| States covered | 43 US states |
| Models trained per state | 4 (SARIMA, Prophet, XGBoost, LSTM) |
| Training time | 15–30 min on 4 cores |
| Forecast horizon | 8 weeks |
| API response time | < 100ms |
| Model size on disk | ~20 KB per state |
| Lines of code | ~1,500+ |

---

## 🗺️ Documentation Map

| Goal | File |
|---|---|
| 🚀 Get running fast | [`QUICK_START.md`](QUICK_START.md) |
| 🏗️ Understand the architecture | [`REFACTORING_SUMMARY.md`](REFACTORING_SUMMARY.md) |
| 🔍 Review code changes | [`CODE_REVIEW.md`](CODE_REVIEW.md) |
| 🌐 Fix FastAPI issues | [`FASTAPI_SETUP.md`](FASTAPI_SETUP.md) |
| 🔮 Understand predictions | [`REAL_PREDICTIONS.md`](REAL_PREDICTIONS.md) |
| 📋 Full project summary | [`COMPLETION_REPORT.md`](COMPLETION_REPORT.md) |

---

## 🏗️ System Architecture

### Data pipeline

```
┌──────────────────────────────────────────────┐
│            INPUT: Excel File                 │
│   43 states · irregular gaps · weekly data   │
└───────────────────┬──────────────────────────┘
                    │
          ┌─────────▼─────────┐
          │  PHASE 1          │  load_and_clean_data()
          │  Data Loading     │  · Read Excel & parse dates
          │                   │  · Resample → weekly (Sunday)
          │                   │  · Interpolate missing values
          │  OUT: 11,008 rows │
          │      × 4 columns  │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │  PHASE 2          │  generate_features()
          │  Feature          │  · Lags: lag_1, lag_7, lag_30
          │  Engineering      │  · Rolling: mean & std (4-week)
          │                   │  · Temporal: month, dow, holiday
          │  OUT: 8,041 rows  │
          │      × 12 columns │
          └─────────┬─────────┘
                    │
       ┌────────────▼────────────┐
       │  PHASE 3                │  ProcessPoolExecutor (4 workers)
       │  Parallel Training      │
       └──┬──────────┬───────────┘
          │          │          │  ... × 43 states
    ┌─────▼──┐ ┌─────▼──┐ ┌────▼───┐
    │Alabama │ │ Alaska │ │Arizona │
    └─────┬──┘ └─────┬──┘ └────┬───┘
          └──────────┴──────────┘
                    │
          80/20 time-series split
          Train: 21 weeks  |  Test: 8 weeks
                    │
          ┌─────────▼─────────┐
          │  Train 4 models   │  SARIMA · Prophet
          │  → pick best MAE  │  XGBoost · LSTM
          └─────────┬─────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
  models/{state}          models/{state}
  _champion.txt           _{model}.pkl
  (best model name)       (trained object)
```

### Prediction serving

```
HTTP GET /predict/Alabama
        │
        ├─ 1. Validate state name
        ├─ 2. Load  models/Alabama_champion.txt  → "XGBoost"
        ├─ 3. Load  models/Alabama_XGBoost.pkl   → trainer object
        ├─ 4. Fetch latest Alabama data from df_clean
        ├─ 5. Generate features (same pipeline as training)
        ├─ 6. Extract last 8 weeks of features
        ├─ 7. trainer.predict() → real values
        └─ 8. Return JSON ↓

{
  "state":            "Alabama",
  "best_model_used":  "XGBoost",
  "forecast_horizon": 8,
  "predictions":      [216061152.0, 218432871.0, ...],
  "status":           "success"
}
```

---

## 🚀 Quick Start

**Prerequisites:** Python 3.8+, pip, ~1 GB free disk space

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train all 43 states (15–30 min)
python run_training.py

# 3. Start the prediction API
python main.py
```

| Endpoint | URL |
|---|---|
| Health check | http://localhost:8000/ |
| Swagger docs | http://localhost:8000/docs |
| Predict | http://localhost:8000/predict/{state} |
| All states | http://localhost:8000/states |
| Model metrics | http://localhost:8000/metrics |

---

## ✨ Features

### Concurrency
```
ProcessPoolExecutor → 4 workers → 43 states in parallel
1–2 hours (sequential)  →  15–30 minutes  (4–8× faster)
```

### Error handling
```python
ForecastingError          # base
├── DataProcessingError
├── ModelTrainingError
├── ConvergenceError
├── InvalidInputError
└── ModelSelectionError
```

### ABC architecture
```python
BaseModelTrainer (ABC)
├── SARIMATrainer
├── ProphetTrainer
├── XGBoostTrainer
└── LSTMTrainer          # memory-optimised, ~30% less RAM
```
> Adding a new model = inherit `BaseModelTrainer` + implement `train()`

### Configuration management
```python
TrainingConfig
├── SARIMAConfig    # SARIMA hyperparameters
├── ProphetConfig   # Prophet hyperparameters
├── XGBoostConfig   # XGBoost hyperparameters
├── LSTMConfig      # LSTM hyperparameters
└── DataConfig      # paths, splits, forecast horizon
```
> All hyperparameters in one place — no hunting through code.

---

## 📁 File Structure

```
forecasting/
│
├── run_training.py              ← training entry point (ProcessPoolExecutor)
├── main.py                      ← FastAPI service (8 endpoints)
├── requirements.txt
│
├── src/
│   ├── config.py                ← all dataclass configs
│   ├── logging_config.py        ← setup_logger(), get_logger()
│   ├── exceptions.py            ← custom exception hierarchy
│   ├── data_loader.py           ← load_and_clean_data()
│   ├── feature_engineering.py   ← generate_features(), time_series_split()
│   ├── base_model_trainer.py    ← BaseModelTrainer ABC + 4 trainers
│   └── model_trainer.py         ← orchestrator, selects best MAE
│
├── data/
│   └── Forecasting Case- Study.xlsx
│
├── models/                      ← created after training
│   ├── Alabama_champion.txt     ← e.g. "XGBoost"
│   ├── Alabama_XGBoost.pkl      ← serialised trainer (~20 KB)
│   └── ...                      ← 43 states × 2 files each
│
└── logs/
    ├── training.log
    └── api.log
```

---



<div align="center">

```bash
python run_training.py    # train all 43 states
python main.py            # start the API
# → http://localhost:8000/docs
```

**43 states · 4 ML models · real predictions · < 100ms API**

</div>