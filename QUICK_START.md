"""
QUICK START GUIDE - Production Forecasting System
==================================================

This guide helps you get started with the refactored, production-ready forecasting system.

## INSTALLATION

1. Prerequisites:
   - Python 3.8+
   - 43-state sales data in Excel format

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python -c "from src import load_and_clean_data; print('OK')"
   ```


## USAGE

### Option 1: Train All Models with Parallel Processing (RECOMMENDED)

```bash
python run_training.py
```

This will:
1. Load data from `data/Forecasting Case- Study.xlsx`
2. Engineer features (lags, rolling stats, temporal features)
3. Train 4 models (SARIMA, Prophet, XGBoost, LSTM) for each state
4. Select the best model based on MAE
5. Save champion models to `models/{state}_champion.txt`
6. Log all activities to `logs/training.log`
7. Process all 43 states in parallel (4 cores by default)

Expected output:
```
============================================================
PHASE 1: Loading and cleaning data
...
PHASE 2: Generating features
...
PHASE 3: Training models (parallel processing)
[1/43] Alabama: XGBoost (MAE: 1946282.26)
[2/43] Alaska: Prophet (MAE: 234567.89)
...
[43/43] Wyoming: SARIMA (MAE: 987654.32)

TRAINING COMPLETE - SUMMARY
============================================================
Total states: 43
Successful: 43
Failed: 0
```

### Option 2: Start FastAPI Service

```bash
python main.py
```

Then access the API:
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/
- List states: http://localhost:8000/states
- Get forecast: http://localhost:8000/predict/Alabama


### Option 3: Programmatic Usage (Python)

```python
from src import (
    load_and_clean_data,
    generate_features,
    time_series_split,
    ModelTrainer,
    setup_logger,
    TrainingConfig
)

# Setup logging
logger = setup_logger("my_app", log_file="logs/my_app.log")

# Load and prepare data
df = load_and_clean_data("data/Forecasting Case- Study.xlsx")
df_featured = generate_features(df)

# Train models for a specific state
state_data = df_featured[df_featured['State'] == 'California']
train, test = time_series_split(state_data)

# Create trainer with custom config
config = TrainingConfig()
config.xgboost.n_estimators = 200  # Customize hyperparameters
trainer = ModelTrainer(train, test, config)

# Select best model
best_model, mae = trainer.select_best_model()
print(f"Best model: {best_model}, MAE: {mae:.2f}")
```


## CONFIGURATION

Customize model hyperparameters in your code:

```python
from src import TrainingConfig

config = TrainingConfig()

# SARIMA configuration
config.sarima.order = (1, 1, 1)
config.sarima.seasonal_order = (1, 1, 1, 52)

# Prophet configuration
config.prophet.yearly_seasonality = True
config.prophet.daily_seasonality = False

# XGBoost configuration
config.xgboost.n_estimators = 100
config.xgboost.learning_rate = 0.05
config.xgboost.max_depth = 6

# LSTM configuration
config.lstm.lstm_units = 50
config.lstm.dropout = 0.2
config.lstm.epochs = 10

# Data configuration
config.data.resample_frequency = "W-SUN"  # Weekly, Sunday
config.data.lag_features = [1, 7, 30]
config.data.rolling_window = 4

# Training configuration
config.max_workers = 4  # Parallel processes
config.timeout_seconds = 600  # Per-state timeout
```

Or modify `src/config.py` defaults directly.


## LOGGING

By default, logs go to:
- Console: INFO level and above
- File: `logs/training.log` with full details

To access logs:
```bash
tail -f logs/training.log  # Watch in real-time
```

To change log level in code:
```python
from src import setup_logger
logger = setup_logger("my_app", level=10)  # DEBUG level
```


## OUTPUT FILES

After training, you'll have:
- `models/{state}_champion.txt` - Contains the name of the best model for each state
- `logs/training.log` - Complete training log
- `logs/api.log` - FastAPI service logs (when running main.py)


## ARCHITECTURE

### Data Flow:
```
Excel File
    ↓
Load & Clean (resampling, interpolation)
    ↓
Feature Engineering (lags, rolling stats, dates)
    ↓
Time Series Split (train/test)
    ↓
[Parallel Processing - 4 cores]
    ├── SARIMA Trainer
    ├── Prophet Trainer
    ├── XGBoost Trainer
    ├── LSTM Trainer
    └── Model Selection (lowest MAE)
    ↓
Save Champion Model
    ↓
API Ready for Predictions
```

### Module Organization:
```
src/
├── __init__.py              # Package exports
├── logging_config.py        # Logging setup
├── config.py               # Configuration classes
├── exceptions.py           # Custom exceptions
├── data_loader.py          # Data loading
├── feature_engineering.py  # Feature creation
├── base_model_trainer.py   # ABC and model implementations
└── model_trainer.py        # Model orchestration

run_training.py             # Main training script
main.py                     # FastAPI service
requirements.txt            # Dependencies
```


## TROUBLESHOOTING

### Problem: "Module not found" error
Solution: Make sure you're in the correct directory and dependencies are installed:
```bash
cd /path/to/forecasting
pip install -r requirements.txt
```

### Problem: TensorFlow not installed (LSTM model fails)
Solution: This is expected and handled gracefully. LSTM will skip and another model
will be selected. To use LSTM, install:
```bash
pip install tensorflow
```

### Problem: Training is slow
Solution: Check the number of workers in config:
```python
config.max_workers = 8  # Use more cores if available
```

### Problem: Out of memory
Solution: Reduce LSTM units or batch size:
```python
config.lstm.lstm_units = 25
config.lstm.batch_size = 16
```

### Problem: API won't start
Solution: Check if port 8000 is already in use:
```bash
python main.py --port 8001  # Use different port
```


## PERFORMANCE TIPS

1. **Faster Training**: Increase max_workers based on CPU cores
   ```python
   config.max_workers = 8  # For 8-core system
   ```

2. **Faster Models**: Reduce SARIMA/Prophet settings
   ```python
   config.sarima.order = (1, 0, 0)  # Simpler model
   config.prophet.interval_width = 0.8  # Less computation
   ```

3. **Reduce Memory**: Use smaller LSTM
   ```python
   config.lstm.lstm_units = 25
   config.lstm.epochs = 5
   ```

4. **Fast Iteration**: Test with subset of states
   ```python
   states = df_featured['State'].unique()[:5]  # Just 5 states
   ```


## MONITORING

### Health Check Endpoint:
```bash
curl http://localhost:8000/
```

Response:
```json
{
  "status": "healthy",
  "data_loaded": true,
  "available_states": 43
}
```

### Metrics Endpoint:
```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "data_loaded": true,
  "total_states": 43,
  "models_trained": 43
}
```


## NEXT STEPS

1. **Run Training**: `python run_training.py`
2. **Start API**: `python main.py`
3. **Make Prediction**: `curl http://localhost:8000/predict/Alabama`
4. **Check Logs**: `tail -f logs/training.log`
5. **Review Results**: Check `models/` directory
6. **Production Deploy**: See DEPLOYMENT.md


## SUPPORT

For issues or questions:
1. Check logs in `logs/training.log`
2. Review REFACTORING_SUMMARY.md for architecture details
3. Check source code docstrings for API documentation
4. Review test examples in the code


## KEY FEATURES

✓ Parallel training (4-8x faster than sequential)
✓ Production logging (not print statements)
✓ Automatic model selection (lowest MAE wins)
✓ Error handling & recovery
✓ Type hints throughout
✓ Configuration management
✓ FastAPI service ready
✓ Graceful degradation (models can fail individually)
✓ Memory optimized LSTM
✓ Time series validation (no data leakage)


Enjoy your production forecasting system!
"""
