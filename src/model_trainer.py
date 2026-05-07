"""Model orchestrator for training and comparing multiple models."""

from typing import Dict, Tuple, Optional, List
import pandas as pd
import numpy as np
import logging
from pathlib import Path

from .base_model_trainer import (
    BaseModelTrainer,
    SARIMATrainer,
    ProphetTrainer,
    XGBoostTrainer,
    LSTMTrainer
)
from .config import TrainingConfig, DEFAULT_CONFIG
from .exceptions import ModelTrainingError, ModelSelectionError
from .logging_config import get_logger

logger = get_logger(__name__)


class ModelTrainer:
    """Orchestrates training and selection of multiple models."""
    
    def __init__(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        config: Optional[TrainingConfig] = None
    ):
        """
        Initialize ModelTrainer.
        
        Args:
            train_data: Training DataFrame
            test_data: Testing DataFrame
            config: Training configuration
        """
        self.train_data = train_data
        self.test_data = test_data
        self.config = config or DEFAULT_CONFIG
        
        # Extract feature columns (all columns except metadata and target)
        self.features = [
            col for col in train_data.columns
            if col not in ['Date', 'State', 'Category', 'Total']
        ]
        
        logger.debug(
            f"ModelTrainer initialized with {len(self.features)} features: {self.features}"
        )
        
        self.results: Dict[str, Tuple[float, np.ndarray]] = {}
    
    def _train_model(
        self,
        model_class: type,
        model_name: str,
        **model_kwargs
    ) -> Tuple[str, float, np.ndarray]:
        """
        Train a single model with error handling.
        
        Args:
            model_class: Model class to instantiate
            model_name: Name of the model
            **model_kwargs: Additional kwargs for model
        
        Returns:
            Tuple of (model_name, mae, predictions)
        """
        try:
            logger.info(f"Starting {model_name} training")
            
            trainer = model_class(
                self.train_data,
                self.test_data,
                features=self.features,
                **model_kwargs
            )
            
            mae, predictions = trainer.train_and_evaluate()
            
            logger.info(f"{model_name} completed with MAE: {mae:.2f}")
            return model_name, mae, predictions
            
        except Exception as e:
            logger.warning(f"{model_name} training failed: {str(e)}")
            # Return high MAE and empty predictions on failure
            return model_name, float('inf'), np.array([])
    
    def select_best_model(self) -> Tuple[str, float]:
        """
        Train all models and select the one with lowest MAE.
        
        Returns:
            Tuple of (best_model_name, mae)
        
        Raises:
            ModelSelectionError: If no models succeeded
        """
        try:
            logger.info("Beginning model selection process")
            
            # Train all models
            models_to_train = [
                (SARIMATrainer, "SARIMA", {
                    'order': self.config.sarima.order,
                    'seasonal_order': self.config.sarima.seasonal_order
                }),
                (ProphetTrainer, "Prophet", {
                    'yearly_seasonality': self.config.prophet.yearly_seasonality,
                    'daily_seasonality': self.config.prophet.daily_seasonality
                }),
                (XGBoostTrainer, "XGBoost", {
                    'n_estimators': self.config.xgboost.n_estimators,
                    'learning_rate': self.config.xgboost.learning_rate,
                    'max_depth': self.config.xgboost.max_depth,
                    'random_state': self.config.xgboost.random_state
                }),
                (LSTMTrainer, "LSTM", {
                    'lstm_units': self.config.lstm.lstm_units,
                    'dropout': self.config.lstm.dropout,
                    'epochs': self.config.lstm.epochs,
                    'batch_size': self.config.lstm.batch_size,
                    'random_state': self.config.lstm.random_state
                })
            ]
            
            results: Dict[str, float] = {}
            
            for model_class, model_name, model_kwargs in models_to_train:
                name, mae, predictions = self._train_model(
                    model_class,
                    model_name,
                    **model_kwargs
                )
                results[name] = mae
                if mae != float('inf'):
                    self.results[name] = (mae, predictions)
            
            # Check if any model succeeded
            successful_models = {k: v for k, v in results.items() if v != float('inf')}
            if not successful_models:
                raise ModelSelectionError("All models failed to train")
            
            # Select best model
            best_model = min(successful_models, key=successful_models.get)
            best_mae = successful_models[best_model]
            
            logger.info(f"Model selection complete. Results: {successful_models}")
            logger.info(f"Winner: {best_model} (MAE: {best_mae:.2f})")
            
            return best_model, best_mae
            
        except Exception as e:
            logger.error(f"Model selection failed: {str(e)}")
            raise ModelSelectionError(f"Failed to select best model: {str(e)}") from e
    
    def get_model_results(self) -> Dict[str, Tuple[float, np.ndarray]]:
        """
        Get results from all trained models.
        
        Returns:
            Dictionary mapping model name to (MAE, predictions)
        """
        return self.results.copy()