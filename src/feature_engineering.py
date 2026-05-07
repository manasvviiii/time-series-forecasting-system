"""Feature engineering module for time series data."""

import pandas as pd
import holidays
from typing import Tuple, List, Optional
import logging

from .config import DataConfig
from .exceptions import DataProcessingError
from .logging_config import get_logger

logger = get_logger(__name__)


def generate_features(
    df: pd.DataFrame,
    config: Optional[DataConfig] = None
) -> pd.DataFrame:
    """
    Create lag features, rolling statistics, and temporal features.
    
    Args:
        df: Input DataFrame with 'State', 'Date', and 'Total' columns
        config: Data configuration (uses default if None)
    
    Returns:
        DataFrame with engineered features
    
    Raises:
        DataProcessingError: If feature engineering fails
    """
    if config is None:
        config = DataConfig()
    
    try:
        logger.info("Starting feature engineering")
        df = df.sort_values(['State', 'Date'])
        
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        
        us_holidays = holidays.US()
        initial_rows = len(df)
        
        # 1. Lag Features
        logger.debug(f"Creating lag features: {config.lag_features}")
        for lag in config.lag_features:
            df[f'lag_{lag}'] = df.groupby('State')['Total'].shift(lag)
        
        # 2. Rolling Statistics
        logger.debug(f"Creating rolling statistics (window={config.rolling_window})")
        df['rolling_mean'] = df.groupby('State')['Total'].transform(
            lambda x: x.rolling(window=config.rolling_window).mean()
        )
        df['rolling_std'] = df.groupby('State')['Total'].transform(
            lambda x: x.rolling(window=config.rolling_window).std()
        )
        
        # 3. Temporal Features
        logger.debug("Creating temporal features")
        df['month'] = df['Date'].dt.month
        df['day_of_week'] = df['Date'].dt.dayofweek
        df['is_holiday'] = df['Date'].apply(lambda x: 1 if x in us_holidays else 0)
        
        # Drop NaNs created by lags/rolling stats
        nan_count = df.isna().sum().sum()
        df = df.dropna()
        final_rows = len(df)
        
        logger.info(
            f"Feature engineering complete: {initial_rows} → {final_rows} rows "
            f"({nan_count} NaN values removed)"
        )
        
        return df
        
    except Exception as e:
        logger.error(f"Feature engineering failed: {str(e)}")
        raise DataProcessingError(f"Failed to generate features: {str(e)}") from e


def time_series_split(
    df: pd.DataFrame,
    forecast_horizon: int = 8
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data using time series logic (no data leakage).
    
    Last `forecast_horizon` time steps are used for validation.
    
    Args:
        df: Input DataFrame
        forecast_horizon: Number of periods to reserve for testing
    
    Returns:
        Tuple of (train_df, test_df)
    
    Raises:
        DataProcessingError: If split fails
    """
    try:
        logger.debug(f"Splitting data with forecast_horizon={forecast_horizon}")
        
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        
        if forecast_horizon <= 0 or forecast_horizon >= len(df):
            raise ValueError(
                f"forecast_horizon must be > 0 and < len(df). Got {forecast_horizon} "
                f"for {len(df)} rows"
            )
        
        unique_dates = sorted(df['Date'].unique())
        train_dates = unique_dates[:-forecast_horizon]
        
        train = df[df['Date'].isin(train_dates)]
        test = df[~df['Date'].isin(train_dates)]
        
        logger.debug(
            f"Data split: {len(train)} train rows, {len(test)} test rows"
        )
        
        return train, test
        
    except Exception as e:
        logger.error(f"Time series split failed: {str(e)}")
        raise DataProcessingError(f"Failed to split data: {str(e)}") from e