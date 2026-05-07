"""Configuration management for the forecasting system."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SARIMAConfig:
    """SARIMA model hyperparameters."""
    order: tuple = (1, 1, 1)
    seasonal_order: tuple = (1, 1, 1, 52)
    disp: bool = False


@dataclass
class ProphetConfig:
    """Prophet model hyperparameters."""
    yearly_seasonality: bool = True
    daily_seasonality: bool = False
    interval_width: float = 0.95


@dataclass
class XGBoostConfig:
    """XGBoost model hyperparameters."""
    n_estimators: int = 100
    learning_rate: float = 0.05
    max_depth: int = 6
    random_state: int = 42
    n_jobs: int = -1


@dataclass
class LSTMConfig:
    """LSTM model hyperparameters."""
    lstm_units: int = 50
    dropout: float = 0.2
    epochs: int = 10
    batch_size: int = 32
    verbose: int = 0
    random_state: int = 42


@dataclass
class DataConfig:
    """Data processing configuration."""
    resample_frequency: str = "W-SUN"
    interpolation_method: str = "linear"
    lag_features: list = None
    rolling_window: int = 4
    forecast_horizon: int = 8
    
    def __post_init__(self):
        if self.lag_features is None:
            self.lag_features = [1, 7, 30]


@dataclass
class TrainingConfig:
    """Training pipeline configuration."""
    data_path: str = "data/Forecasting Case- Study.xlsx"
    models_dir: str = "models"
    logs_dir: str = "logs"
    max_workers: int = 4  # For parallel training
    timeout_seconds: int = 300  # Timeout per state training
    
    # Model configurations
    sarima: SARIMAConfig = None
    prophet: ProphetConfig = None
    xgboost: XGBoostConfig = None
    lstm: LSTMConfig = None
    
    def __post_init__(self):
        if self.sarima is None:
            self.sarima = SARIMAConfig()
        if self.prophet is None:
            self.prophet = ProphetConfig()
        if self.xgboost is None:
            self.xgboost = XGBoostConfig()
        if self.lstm is None:
            self.lstm = LSTMConfig()


# Default configuration instance
DEFAULT_CONFIG = TrainingConfig()
