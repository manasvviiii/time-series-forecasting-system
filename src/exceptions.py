"""Custom exceptions for the forecasting system."""


class ForecastingError(Exception):
    """Base exception for forecasting system."""
    pass


class DataProcessingError(ForecastingError):
    """Raised when data loading or processing fails."""
    pass


class ModelTrainingError(ForecastingError):
    """Raised when model training fails."""
    pass


class ConvergenceError(ModelTrainingError):
    """Raised when a model fails to converge."""
    pass


class InvalidInputError(ForecastingError):
    """Raised when input data is invalid."""
    pass


class ModelSelectionError(ForecastingError):
    """Raised when model selection fails."""
    pass
