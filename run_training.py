"""Main training orchestrator with parallel processing."""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
import joblib
import pandas as pd

from src import (
    load_and_clean_data,
    generate_features,
    time_series_split,
    ModelTrainer,
    TrainingConfig,
    setup_logger,
    get_logger,
    DataProcessingError,
    ModelSelectionError,
)

logger = get_logger(__name__)


def train_single_state(
    state_name: str,
    state_data: "pd.DataFrame",
    config: TrainingConfig,
    models_dir: Path
) -> Tuple[str, Optional[str], Optional[float], str]:
    """
    Train models for a single state (runs in separate process).
    
    Args:
        state_name: State name
        state_data: State-specific data
        config: Training configuration
        models_dir: Directory to save trained models
    
    Returns:
        Tuple of (state_name, best_model, mae, status)
    """
    try:
        logger.info(f"Processing State: {state_name}")
        
        # Split data
        train, test = time_series_split(state_data)
        
        # Train models
        trainer = ModelTrainer(train, test, config)
        best_model_name, mae = trainer.select_best_model()
        
        logger.info(f"State {state_name}: Winner={best_model_name}, MAE={mae:.2f}")
        
        # Save the champion model
        try:
            model_results = trainer.get_model_results()
            if best_model_name in model_results:
                mae_score, predictions = model_results[best_model_name]
                # Save model file with state name and model type
                model_file = models_dir / f"{state_name}_{best_model_name}.pkl"
                joblib.dump(trainer, model_file)
                logger.info(f"Saved trained model: {model_file}")
        except Exception as e:
            logger.warning(f"Failed to save trained model for {state_name}: {str(e)}")
        
        return state_name, best_model_name, mae, "success"
        
    except Exception as e:
        logger.error(f"Training failed for {state_name}: {str(e)}")
        return state_name, None, None, f"failed: {str(e)}"


def execute_pipeline(
    data_path: str,
    config: Optional[TrainingConfig] = None,
    max_workers: int = 4,
    timeout_seconds: int = 300
) -> dict:
    """
    Execute complete training pipeline with parallel processing.
    
    Args:
        data_path: Path to data file
        config: Training configuration
        max_workers: Number of parallel processes
        timeout_seconds: Timeout per state
    
    Returns:
        Dictionary with results and summary
    """
    try:
        # Initialize configuration
        if config is None:
            config = TrainingConfig()
        
        # Create output directory
        models_dir = Path(config.models_dir)
        models_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Models directory: {models_dir}")
        
        # Phase 1: Load and Clean
        logger.info("=" * 60)
        logger.info("PHASE 1: Loading and cleaning data")
        logger.info("=" * 60)
        df = load_and_clean_data(data_path, config=None)
        logger.info(f"Loaded {len(df)} rows from {len(df['State'].unique())} states")
        
        # Phase 2: Feature Engineering
        logger.info("=" * 60)
        logger.info("PHASE 2: Generating features")
        logger.info("=" * 60)
        df_featured = generate_features(df)
        logger.info(f"Feature engineering complete: {len(df_featured)} rows")
        
        # Phase 3: Model Training & Selection (Parallel)
        logger.info("=" * 60)
        logger.info("PHASE 3: Training models (parallel processing)")
        logger.info("=" * 60)
        
        states = sorted(df_featured['State'].unique())
        logger.info(f"Training {len(states)} states with {max_workers} workers")
        
        results = {}
        failed_states = []
        
        # Use ProcessPoolExecutor for parallel training
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_state = {}
            for state in states:
                state_data = df_featured[df_featured['State'] == state]
                future = executor.submit(
                    train_single_state,
                    state,
                    state_data,
                    config,
                    models_dir
                )
                future_to_state[future] = state
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_state, timeout=timeout_seconds):
                state_name, best_model, mae, status = future.result()
                completed += 1
                
                if status == "success":
                    results[state_name] = {
                        'model': best_model,
                        'mae': mae,
                        'status': 'success'
                    }
                    # Save champion model metadata
                    with open(models_dir / f"{state_name}_champion.txt", "w") as f:
                        f.write(best_model)
                    logger.info(f"[{completed}/{len(states)}] {state_name}: {best_model} (MAE: {mae:.2f})")
                else:
                    results[state_name] = {
                        'model': None,
                        'mae': None,
                        'status': status
                    }
                    failed_states.append(state_name)
                    logger.warning(f"[{completed}/{len(states)}] {state_name}: {status}")
        
        # Summary
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE - SUMMARY")
        logger.info("=" * 60)
        
        successful = len([r for r in results.values() if r['status'] == 'success'])
        failed = len(failed_states)
        
        logger.info(f"Total states: {len(states)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        if failed_states:
            logger.warning(f"Failed states: {failed_states}")
        
        return {
            'results': results,
            'total_states': len(states),
            'successful': successful,
            'failed': failed,
            'failed_states': failed_states
        }
        
    except DataProcessingError as e:
        logger.error(f"Data processing error: {str(e)}")
        raise
    except ModelSelectionError as e:
        logger.error(f"Model selection error: {str(e)}")
        raise
    except TimeoutError as e:
        logger.error(f"Training timeout: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    
    # Setup logging
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    setup_logger(__name__, log_file="logs/training.log", level=logging.INFO)
    
    logger.info("Starting Time Series Forecasting Pipeline")
    
    try:
        # Execute pipeline
        data_path = "data/Forecasting Case- Study.xlsx"
        result = execute_pipeline(
            data_path,
            max_workers=4,
            timeout_seconds=600
        )
        
        logger.info("Pipeline execution successful")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)