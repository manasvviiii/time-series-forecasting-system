"""Data loading and preprocessing module."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .config import DataConfig
from .exceptions import DataProcessingError
from .logging_config import get_logger

logger = get_logger(__name__)


def load_and_clean_data(
    filepath: str,
    config: Optional[DataConfig] = None
) -> pd.DataFrame:
    """
    Load Excel file, resample to weekly frequency, and interpolate missing values.
    
    Args:
        filepath: Path to Excel file
        config: Data configuration (uses default if None)
    
    Returns:
        Cleaned DataFrame with all states
    
    Raises:
        DataProcessingError: If data loading or processing fails
    """
    if config is None:
        config = DataConfig()
    
    try:
        # Validate file exists
        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        logger.info(f"Loading data from {filepath}")
        df = pd.read_excel(filepath)
        logger.debug(f"Loaded {len(df)} rows from Excel file")
        
        if df.empty:
            raise ValueError("Excel file is empty")
        
        # Ensure required columns exist
        required_cols = ['Date', 'State', 'Total']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        df['Date'] = pd.to_datetime(df['Date'])
        logger.debug(f"Found {df['State'].nunique()} unique states")
        
        cleaned_frames: List[pd.DataFrame] = []
        
        # Process each state individually as a separate time series
        for state in df['State'].unique():
            try:
                state_df = df[df['State'] == state].copy()
                initial_rows = len(state_df)
                
                state_df = state_df.set_index('Date').sort_index()
                
                # Resample to weekly frequency
                state_df = state_df.resample(config.resample_frequency).asfreq()
                logger.debug(
                    f"State '{state}': {initial_rows} rows → "
                    f"{len(state_df)} rows after resampling"
                )
                
                # Interpolate missing values
                state_df['Total'] = state_df['Total'].interpolate(
                    method=config.interpolation_method
                )
                
                # Forward fill metadata
                state_df['State'] = state
                state_df['Category'] = 'Beverages'
                
                cleaned_frames.append(state_df.reset_index())
                
            except Exception as e:
                logger.warning(f"Error processing state '{state}': {str(e)}")
                raise DataProcessingError(f"Failed to process state '{state}': {str(e)}")
        
        result = pd.concat(cleaned_frames, ignore_index=True)
        logger.info(f"Data cleaning complete: {len(result)} total rows")
        
        return result
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {filepath}")
        raise DataProcessingError(f"Data file not found: {filepath}") from e
    except Exception as e:
        logger.error(f"Data loading failed: {str(e)}")
        raise DataProcessingError(f"Failed to load and clean data: {str(e)}") from e