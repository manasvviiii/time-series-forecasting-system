"""FastAPI service for time series forecasting."""

import logging
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib

from src import (
    load_and_clean_data,
    generate_features,
    setup_logger,
    get_logger,
    DataProcessingError
)

# Setup logging
setup_logger(__name__, log_file="logs/api.log", level=logging.INFO)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Microgcc Forecasting Service",
    description="Time Series Forecasting API",
    version="1.0.0"
)

# Configuration
DATA_PATH = "data/Forecasting Case- Study.xlsx"
MODELS_DIR = Path("models")

# Load data at startup with error handling
try:
    logger.info(f"Loading data from {DATA_PATH}")
    df_clean = load_and_clean_data(DATA_PATH)
    available_states = sorted(df_clean['State'].unique().tolist())
    logger.info(f"Data loaded successfully. Available states: {len(available_states)}")
except Exception as e:
    logger.error(f"Failed to load data at startup: {str(e)}")
    df_clean = None
    available_states = []


# Pydantic models for request/response validation
class PredictionResponse(BaseModel):
    """Response model for predictions."""
    state: str = Field(..., description="State name")
    best_model_used: str = Field(..., description="Name of the champion model")
    forecast_horizon: int = Field(default=8, description="Number of weeks forecasted")
    predictions: List[float] = Field(..., description="Forecasted values")
    status: str = Field(default="success", description="Status of the prediction")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


class HealthCheck(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    data_loaded: bool = Field(..., description="Whether training data is loaded")
    available_states: int = Field(..., description="Number of available states")


# Endpoints
@app.get("/", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    logger.info("Health check requested")
    return HealthCheck(
        status="healthy" if df_clean is not None else "unhealthy",
        data_loaded=df_clean is not None,
        available_states=len(available_states)
    )


@app.get("/states", response_model=List[str])
async def list_states() -> List[str]:
    """Get list of available states."""
    logger.info("States list requested")
    if not available_states:
        raise HTTPException(status_code=503, detail="Data not loaded")
    return available_states


@app.get("/predict/{state}", response_model=PredictionResponse)
async def get_prediction(state: str) -> PredictionResponse:
    """
    Get forecast for a specific state.
    
    Args:
        state: State name (case-insensitive)
    
    Returns:
        PredictionResponse with forecast
    """
    try:
        # Validate input
        if not state or not isinstance(state, str):
            logger.warning(f"Invalid state parameter: {state}")
            raise HTTPException(status_code=400, detail="State must be a non-empty string")
        
        # Normalize state name
        state_normalized = state.capitalize()
        
        if df_clean is None:
            logger.error("Training data not loaded")
            raise HTTPException(status_code=503, detail="Training data not loaded")
        
        if state_normalized not in available_states:
            logger.warning(f"State not found: {state_normalized}")
            raise HTTPException(
                status_code=404,
                detail=f"State '{state_normalized}' not found. "
                       f"Available states: {', '.join(available_states[:5])}..."
            )
        
        # Load champion model metadata
        champion_file = MODELS_DIR / f"{state_normalized}_champion.txt"
        if not champion_file.exists():
            logger.warning(f"Champion model not found for {state_normalized}")
            return PredictionResponse(
                state=state_normalized,
                best_model_used="unknown",
                forecast_horizon=8,
                predictions=[],
                status="model_not_trained"
            )
        
        try:
            with open(champion_file, "r") as f:
                best_model_name = f.read().strip()
            logger.info(f"Prediction requested for {state_normalized}: {best_model_name}")
        except Exception as e:
            logger.error(f"Failed to read champion model for {state_normalized}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to read model metadata"
            )
        
        # Load the actual trained model and make predictions
        model_file = MODELS_DIR / f"{state_normalized}_{best_model_name}.pkl"
        
        if not model_file.exists():
            logger.warning(f"Trained model file not found for {state_normalized}: {best_model_name}")
            # Fallback to mock data if model not saved yet
            mock_predictions = [
                12000000.0 + i * 100000 for i in range(8)
            ]
            return PredictionResponse(
                state=state_normalized,
                best_model_used=best_model_name,
                forecast_horizon=8,
                predictions=mock_predictions,
                status="model_not_persisted"
            )
        
        try:
            # Load the trained model
            logger.info(f"Loading trained model: {best_model_name}")
            model = joblib.load(model_file)
            
            # Get the latest data for this state to make future predictions
            state_data = df_clean[df_clean['State'] == state_normalized]
            
            # Generate features for prediction
            from src import generate_features
            state_featured = generate_features(state_data.copy())
            
            # Get feature columns (all except metadata)
            feature_cols = [col for col in state_featured.columns 
                          if col not in ['Date', 'State', 'Category', 'Total']]
            
            # Make predictions on the last 8 weeks (or available data)
            X_pred = state_featured[feature_cols].tail(8)
            
            # Different prediction logic based on model type
            if best_model_name == "XGBoost":
                predictions = model.predict(X_pred)
            elif best_model_name == "SARIMA":
                # SARIMA returns forecast directly
                predictions = model.forecast(steps=8)
            elif best_model_name == "Prophet":
                # Prophet returns dataframe, extract yhat
                future = model.make_future_dataframe(periods=8, freq='W')
                forecast = model.predict(future)
                predictions = forecast['yhat'].tail(8).values
            elif best_model_name == "LSTM":
                # LSTM model prediction
                from sklearn.preprocessing import MinMaxScaler
                scaler = getattr(model, '_scaler', None)
                if scaler and len(X_pred) > 0:
                    X_scaled = scaler.transform(X_pred)
                    X_reshaped = X_scaled[:, :].reshape(X_scaled.shape[0], 1, X_scaled.shape[1] - 1)
                    preds = model.predict(X_reshaped, verbose=0)
                    predictions = scaler.inverse_transform(
                        np.concatenate([preds, X_scaled[:, 1:]], axis=1)
                    )[:, 0]
                else:
                    predictions = state_featured['Total'].tail(8).values
            else:
                predictions = state_featured['Total'].tail(8).values
            
            # Convert to float list for JSON serialization
            predictions_list = [float(p) for p in predictions]
            
            logger.info(f"Predictions for {state_normalized}: {predictions_list}")
            
            return PredictionResponse(
                state=state_normalized,
                best_model_used=best_model_name,
                forecast_horizon=8,
                predictions=predictions_list,
                status="success"
            )
        
        except Exception as e:
            logger.error(f"Failed to make predictions: {str(e)}")
            # Fallback to mock data on error
            mock_predictions = [
                12000000.0 + i * 100000 for i in range(8)
            ]
            return PredictionResponse(
                state=state_normalized,
                best_model_used=best_model_name,
                forecast_horizon=8,
                predictions=mock_predictions,
                status="prediction_error"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in prediction endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics() -> dict:
    """Get service metrics."""
    logger.debug("Metrics requested")
    return {
        "data_loaded": df_clean is not None,
        "total_states": len(available_states),
        "models_trained": len(list(MODELS_DIR.glob("*_champion.txt"))) if MODELS_DIR.exists() else 0
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)