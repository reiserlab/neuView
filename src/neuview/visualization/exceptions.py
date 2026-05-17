"""
Custom exceptions and error handling utilities for the eyemap visualization module.

This module provides specialized exception classes and validation utilities
to improve error handling, debugging, and user experience throughout the
eyemap generation pipeline.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path

logger = logging.getLogger(__name__)


class EyemapError(Exception):
    """Base exception class for all eyemap-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception with a message and optional details.

        Args:
            message: Human-readable error message
            details: Optional dictionary containing additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return a formatted string representation of the error."""
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} (Details: {detail_str})"
        return self.message


class ValidationError(EyemapError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected_type: Optional[Type] = None,
    ):
        """
        Initialize validation error with field-specific information.

        Args:
            message: Error message
            field: Name of the field that failed validation
            value: The invalid value
            expected_type: The expected type for the field
        """
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if expected_type is not None:
            details["expected_type"] = expected_type.__name__

        super().__init__(message, details)
        self.field = field
        self.value = value
        self.expected_type = expected_type


class ConfigurationError(EyemapError):
    """Raised when configuration is invalid or incomplete."""

    pass


class DataProcessingError(EyemapError):
    """Raised when data processing operations fail."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        data_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize data processing error with operation context.

        Args:
            message: Error message
            operation: Name of the operation that failed
            data_context: Additional context about the data being processed
        """
        details = {}
        if operation is not None:
            details["operation"] = operation
        if data_context is not None:
            details.update(data_context)

        super().__init__(message, details)
        self.operation = operation


class RenderingError(EyemapError):
    """Raised when rendering operations fail."""

    def __init__(
        self,
        message: str,
        format_type: Optional[str] = None,
        output_path: Optional[Path] = None,
    ):
        """
        Initialize rendering error with format and path context.

        Args:
            message: Error message
            format_type: The output format being rendered (SVG, PNG, etc.)
            output_path: The intended output path
        """
        details = {}
        if format_type is not None:
            details["format"] = format_type
        if output_path is not None:
            details["output_path"] = str(output_path)

        super().__init__(message, details)
        self.format_type = format_type
        self.output_path = output_path


class FileOperationError(EyemapError):
    """Raised when file I/O operations fail."""

    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        operation: Optional[str] = None,
    ):
        """
        Initialize file operation error with path and operation context.

        Args:
            message: Error message
            file_path: The file path involved in the operation
            operation: The type of operation (read, write, create, etc.)
        """
        details = {}
        if file_path is not None:
            details["file_path"] = str(file_path)
        if operation is not None:
            details["operation"] = operation

        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation


class DependencyError(EyemapError):
    """Raised when dependency injection or service resolution fails."""

    def __init__(
        self,
        message: str,
        service_type: Optional[str] = None,
        dependency_chain: Optional[List[str]] = None,
    ):
        """
        Initialize dependency error with service context.

        Args:
            message: Error message
            service_type: The type of service that failed to resolve
            dependency_chain: Chain of dependencies leading to the failure
        """
        details = {}
        if service_type is not None:
            details["service_type"] = service_type
        if dependency_chain is not None:
            details["dependency_chain"] = " -> ".join(dependency_chain)

        super().__init__(message, details)
        self.service_type = service_type
        self.dependency_chain = dependency_chain or []


class PerformanceError(EyemapError):
    """Raised when performance optimization operations fail."""

    pass


# Validation utilities


def validate_not_none(value: Any, field_name: str) -> None:
    """
    Validate that a value is not None.

    Args:
        value: The value to validate
        field_name: Name of the field for error reporting

    Raises:
        ValidationError: If value is None
    """
    if value is None:
        raise ValidationError(
            f"Field '{field_name}' cannot be None", field=field_name, value=value
        )


def validate_type(value: Any, expected_type: Type, field_name: str) -> None:
    """
    Validate that a value is of the expected type.

    Args:
        value: The value to validate
        expected_type: The expected type
        field_name: Name of the field for error reporting

    Raises:
        ValidationError: If value is not of expected type
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Field '{field_name}' must be of type {expected_type.__name__}, got {type(value).__name__}",
            field=field_name,
            value=value,
            expected_type=expected_type,
        )










def safe_operation(operation_name: str, operation_func, *args, **kwargs):
    """
    Execute an operation with comprehensive error handling and logging.

    Args:
        operation_name: Name of the operation for logging
        operation_func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the operation

    Raises:
        EyemapError: Wrapped version of any exception that occurs
    """
    try:
        logger.debug(f"Starting operation: {operation_name}")
        result = operation_func(*args, **kwargs)
        logger.debug(f"Completed operation: {operation_name}")
        return result
    except EyemapError:
        # Re-raise our custom exceptions
        logger.error(f"Operation failed: {operation_name}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in operation '{operation_name}': {e}")
        raise EyemapError(
            f"Operation '{operation_name}' failed: {str(e)}",
            details={"operation": operation_name},
        )


class ErrorContext:
    """Context manager for tracking operation context in error messages."""

    def __init__(self, operation: str, **context):
        """
        Initialize error context.

        Args:
            operation: Name of the operation
            **context: Additional context key-value pairs
        """
        self.operation = operation
        self.context = context
        self._original_operation = None

    def __enter__(self):
        """Enter the context manager."""
        logger.debug(f"Entering context: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and handle any exceptions."""
        if exc_type is None:
            logger.debug(f"Exiting context: {self.operation}")
            return False

        # If it's already our custom exception, don't wrap it again
        if isinstance(exc_val, EyemapError):
            logger.error(f"Error in context '{self.operation}': {exc_val}")
            return False

        # Wrap other exceptions with context
        logger.error(f"Unexpected error in context '{self.operation}': {exc_val}")
        wrapped_error = EyemapError(
            f"Error in {self.operation}: {str(exc_val)}",
            details={**self.context, "operation": self.operation},
        )

        # Replace the original exception with our wrapped one
        raise wrapped_error from exc_val
