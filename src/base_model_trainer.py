"""Abstract base class and concrete implementations for model training."""

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
import logging

from sklearn.metrics import mean_absolute_error
from .exceptions import ModelTrainingError, ConvergenceError
from .logging_config import get_logger

logger = get_logger(__name__)


class BaseModelTrainer(ABC):
    """Abstract base class for all model trainers."""
    
    def __init__(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        features: Optional[List[str]] = None,
        target: str = 'Total',
        model_name: Optional[str] = None
    ):
        """
        Initialize base trainer.
        
        Args:
            train_data: Training DataFrame
            test_data: Testing DataFrame
            features: List of feature columns to use
            target: Target column name
            model_name: Name of the model (auto-set from class name if None)
        """
        self.train_data = train_data
        self.test_data = test_data
        self.features = features or []
        self.target = target
        self.model_name = model_name or self.__class__.__name__
        
        # Validate data
        if train_data.empty or test_data.empty:
            raise ValueError("Training or test data is empty")
        
        if target not in train_data.columns:
            raise ValueError(f"Target '{target}' not found in training data")
        
        logger.debug(f"{self.model_name}: {len(train_data)} train, {len(test_data)} test rows")
    
    @abstractmethod
    def train(self) -> np.ndarray:
        """
        Train the model and return predictions on test set.
        
        Returns:
            Predictions array for test set
        
        Raises:
            ModelTrainingError: If training fails
        """
        pass
    
    def evaluate(self, predictions: np.ndarray) -> float:
        """
        Evaluate predictions using MAE.
        
        Args:
            predictions: Model predictions for test set
        
        Returns:
            Mean Absolute Error
        """
        try:
            mae = mean_absolute_error(self.test_data[self.target], predictions)
            logger.debug(f"{self.model_name} MAE: {mae:.2f}")
            return mae
        except Exception as e:
            logger.error(f"Evaluation failed for {self.model_name}: {str(e)}")
            raise
    
    def train_and_evaluate(self) -> Tuple[float, np.ndarray]:
        """
        Train model and evaluate it.
        
        Returns:
            Tuple of (MAE, predictions)
        
        Raises:
            ModelTrainingError: If training fails
        """
        try:
            logger.info(f"Training {self.model_name}")
            predictions = self.train()
            mae = self.evaluate(predictions)
            return mae, predictions
        except Exception as e:
            logger.error(f"Training failed for {self.model_name}: {str(e)}")
            raise


class SARIMATrainer(BaseModelTrainer):
    """SARIMA model trainer."""
    
    def __init__(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        order: Tuple[int, int, int] = (1, 1, 1),
        seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 52),
        **kwargs
    ):
        """
        Initialize SARIMA trainer.
        
        Args:
            train_data: Training DataFrame
            test_data: Testing DataFrame
            order: ARIMA order (p, d, q)
            seasonal_order: Seasonal order (P, D, Q, s)
        """
        super().__init__(train_data, test_data, model_name="SARIMA", **kwargs)
        self.order = order
        self.seasonal_order = seasonal_order
    
    def train(self) -> np.ndarray:
        """Train SARIMA model."""
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            
            logger.info(f"Fitting SARIMA{self.order}x{self.seasonal_order}")
            model = SARIMAX(
                self.train_data[self.target],
                order=self.order,
                seasonal_order=self.seasonal_order
            )
            result = model.fit(disp=False)
            predictions = result.forecast(len(self.test_data))
            logger.info("SARIMA training completed")
            return np.array(predictions)
            
        except Exception as e:
            logger.error(f"SARIMA training failed: {str(e)}")
            raise ConvergenceError(f"SARIMA failed to converge: {str(e)}") from e


class ProphetTrainer(BaseModelTrainer):
    """Facebook Prophet model trainer."""
    
    def __init__(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        yearly_seasonality: bool = True,
        daily_seasonality: bool = False,
        **kwargs
    ):
        """
        Initialize Prophet trainer.
        
        Args:
            train_data: Training DataFrame
            test_data: Testing DataFrame
            yearly_seasonality: Enable yearly seasonality
            daily_seasonality: Enable daily seasonality
        """
        super().__init__(train_data, test_data, model_name="Prophet", **kwargs)
        self.yearly_seasonality = yearly_seasonality
        self.daily_seasonality = daily_seasonality
    
    def train(self) -> np.ndarray:
        """Train Prophet model."""
        try:
            from prophet import Prophet
            import warnings
            warnings.filterwarnings('ignore')
            
            logger.info("Fitting Prophet model")
            
            # Prepare data for Prophet
            p_train = self.train_data[['Date', self.target]].copy()
            p_train.columns = ['ds', 'y']
            
            model = Prophet(
                yearly_seasonality=self.yearly_seasonality,
                daily_seasonality=self.daily_seasonality
            )
            model.fit(p_train)
            
            # Generate future dataframe
            future = model.make_future_dataframe(
                periods=len(self.test_data),
                freq='W'
            )
            forecast = model.predict(future)
            predictions = forecast['yhat'].iloc[-len(self.test_data):].values
            
            logger.info("Prophet training completed")
            return np.array(predictions)
            
        except Exception as e:
            logger.error(f"Prophet training failed: {str(e)}")
            raise ConvergenceError(f"Prophet failed: {str(e)}") from e


class XGBoostTrainer(BaseModelTrainer):
    """XGBoost model trainer."""
    
    def __init__(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        random_state: int = 42,
        **kwargs
    ):
        """
        Initialize XGBoost trainer.
        
        Args:
            train_data: Training DataFrame
            test_data: Testing DataFrame
            n_estimators: Number of boosting rounds
            learning_rate: Learning rate
            max_depth: Maximum tree depth
            random_state: Random seed
        """
        # XGBoost requires features, so set them here
        if 'features' not in kwargs:
            features = [col for col in train_data.columns 
                       if col not in ['Date', 'State', 'Category', 'Total']]
            kwargs['features'] = features
        
        super().__init__(train_data, test_data, **kwargs)
        self.model_name = "XGBoost"
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state
    
    def train(self) -> np.ndarray:
        """Train XGBoost model."""
        try:
            from xgboost import XGBRegressor
            
            if not self.features:
                raise ValueError("No features specified for XGBoost")
            
            logger.info(f"Fitting XGBoost with {len(self.features)} features")
            
            model = XGBRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                random_state=self.random_state,
                verbose=0
            )
            
            X_train = self.train_data[self.features]
            y_train = self.train_data[self.target]
            
            model.fit(X_train, y_train)
            
            X_test = self.test_data[self.features]
            predictions = model.predict(X_test)
            
            logger.info("XGBoost training completed")
            return np.array(predictions)
            
        except Exception as e:
            logger.error(f"XGBoost training failed: {str(e)}")
            raise ModelTrainingError(f"XGBoost failed: {str(e)}") from e


class LSTMTrainer(BaseModelTrainer):
    """LSTM model trainer with memory optimization."""
    
    def __init__(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        lstm_units: int = 50,
        dropout: float = 0.2,
        epochs: int = 10,
        batch_size: int = 32,
        random_state: int = 42,
        **kwargs
    ):
        """
        Initialize LSTM trainer.
        
        Args:
            train_data: Training DataFrame
            test_data: Testing DataFrame
            lstm_units: Number of LSTM units
            dropout: Dropout rate
            epochs: Number of training epochs
            batch_size: Batch size for training
            random_state: Random seed
        """
        # LSTM requires features
        if 'features' not in kwargs:
            features = [col for col in train_data.columns 
                       if col not in ['Date', 'State', 'Category', 'Total']]
            kwargs['features'] = features
        
        super().__init__(train_data, test_data, **kwargs)
        self.model_name = "LSTM"
        self.lstm_units = lstm_units
        self.dropout = dropout
        self.epochs = epochs
        self.batch_size = batch_size
        self.random_state = random_state
    
    def train(self) -> np.ndarray:
        """Train LSTM model with memory optimization."""
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from sklearn.preprocessing import MinMaxScaler
            import tensorflow as tf
            
            # Set random seeds for reproducibility
            tf.random.set_seed(self.random_state)
            np.random.seed(self.random_state)
            
            logger.info(f"Preparing LSTM data with {len(self.features)} features")
            
            if not self.features:
                raise ValueError("No features specified for LSTM")
            
            # Scale data
            scaler = MinMaxScaler()
            X_cols = [self.target] + self.features
            
            train_scaled = scaler.fit_transform(self.train_data[X_cols])
            test_scaled = scaler.transform(self.test_data[X_cols])
            
            # Reshape: [samples, timesteps, features]
            X_train = train_scaled[:, 1:].reshape(
                train_scaled.shape[0],
                1,
                len(self.features)
            )
            y_train = train_scaled[:, 0]
            
            logger.info(f"Building LSTM model: {self.lstm_units} units, dropout={self.dropout}")
            
            model = Sequential([
                LSTM(self.lstm_units, activation='relu', input_shape=(1, len(self.features))),
                Dropout(self.dropout),
                Dense(1)
            ])
            
            model.compile(optimizer='adam', loss='mse')
            
            # Train with controlled verbosity
            model.fit(
                X_train,
                y_train,
                epochs=self.epochs,
                batch_size=self.batch_size,
                verbose=0
            )
            
            # Make predictions
            X_test = test_scaled[:, 1:].reshape(
                test_scaled.shape[0],
                1,
                len(self.features)
            )
            preds = model.predict(X_test, verbose=0)
            
            # Inverse transform
            preds_full = np.concatenate([preds, test_scaled[:, 1:]], axis=1)
            predictions = scaler.inverse_transform(preds_full)[:, 0]
            
            logger.info("LSTM training completed")
            return np.array(predictions)
            
        except Exception as e:
            logger.error(f"LSTM training failed: {str(e)}")
            raise ModelTrainingError(f"LSTM failed: {str(e)}") from e
