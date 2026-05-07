# Quick Start Guide

## Installation

```bash
pip install -r requirements.txt

# Verify
python -c "from src import load_and_clean_data; print('OK')"
```

---

## Running the System

### 1 — Train all 43 states

```bash
python run_training.py
```

Expected output:
```
PHASE 1: Loading and cleaning data
PHASE 2: Generating features
PHASE 3: Training models (parallel processing)
[1/43] Alabama: XGBoost (MAE: 1946282.26)
[2/43] Alaska: Prophet (MAE: 234567.89)
...
[43/43] Wyoming: SARIMA (MAE: 987654.32)

Total states: 43 | Successful: 43 | Failed: 0
```

### 2 — Start the API

```bash
python main.py
```

| Endpoint | URL |
|---|---|
| Health check | http://localhost:8000/ |
| Swagger docs | http://localhost:8000/docs |
| Predict | http://localhost:8000/predict/{state} |
| All states | http://localhost:8000/states |
| Metrics | http://localhost:8000/metrics |

### 3 — Programmatic usage

```python
from src import load_and_clean_data, generate_features, time_series_split, ModelTrainer, TrainingConfig

df = load_and_clean_data("data/Forecasting Case- Study.xlsx")
df_featured = generate_features(df)

state_data = df_featured[df_featured['State'] == 'California']
train, test = time_series_split(state_data)

config = TrainingConfig()
trainer = ModelTrainer(train, test, config)
best_model, mae = trainer.select_best_model()
print(f"Best model: {best_model}, MAE: {mae:.2f}")
```

---

## Configuration

All hyperparameters live in `src/config.py`. Override in code:

```python
from src import TrainingConfig

config = TrainingConfig()

# SARIMA
config.sarima.order = (1, 1, 1)
config.sarima.seasonal_order = (1, 1, 1, 52)

# Prophet
config.prophet.yearly_seasonality = True
config.prophet.daily_seasonality = False

# XGBoost
config.xgboost.n_estimators = 100
config.xgboost.learning_rate = 0.05
config.xgboost.max_depth = 6

# LSTM
config.lstm.lstm_units = 50
config.lstm.dropout = 0.2
config.lstm.epochs = 10

# Data
config.data.resample_frequency = "W-SUN"
config.data.lag_features = [1, 7, 30]
config.data.rolling_window = 4

# Parallelism
config.max_workers = 4
config.timeout_seconds = 600
```

---

## Logging

```bash
tail -f logs/training.log   # watch training in real-time
tail -f logs/api.log        # watch API in real-time
```

```python
from src import setup_logger
logger = setup_logger("my_app", level=10)  # 10 = DEBUG
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| LSTM fails | Expected — TensorFlow optional. Install with `pip install tensorflow` to enable |
| Training is slow | Increase `config.max_workers = 8` (match your CPU core count) |
| Out of memory | Reduce `config.lstm.lstm_units = 25` and `config.lstm.batch_size = 16` |
| Port 8000 in use | Run `python main.py --port 8001` |
| Still seeing mock predictions | Check `models/` has `.pkl` files — re-run training if empty |

---

## Performance Tips

```python
config.max_workers = 8          # use all cores
config.sarima.order = (1, 0, 0) # simpler/faster SARIMA
config.lstm.lstm_units = 25     # smaller LSTM = less RAM
config.lstm.epochs = 5

# Test with a subset before full run
states = df_featured['State'].unique()[:5]
```