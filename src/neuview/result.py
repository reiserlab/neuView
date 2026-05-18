"""
Simplified Result pattern for explicit error handling.

This module provides a simple Result type for handling success and error cases
without exceptions, making error handling explicit and composable.
"""

from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass

T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type


class Result(Generic[T, E]):
    """
    A Result type that represents either success (Ok) or failure (Err).

    This provides explicit error handling without exceptions, making
    error cases visible in the type system.
    """

    def __init__(self):
        raise NotImplementedError("Use Ok() or Err() to create Result instances")

    def is_ok(self) -> bool:
        """Check if this is a success result."""
        return isinstance(self, Ok)

    def is_err(self) -> bool:
        """Check if this is an error result."""
        return isinstance(self, Err)

    def unwrap(self) -> T:
        """
        Get the success value or raise an exception if this is an error.

        Use this only when you're certain the result is Ok.
        """
        if self.is_ok():
            return self.value
        else:
            raise ValueError(f"Called unwrap() on Err value: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Get the success value or return the default if this is an error."""
        if self.is_ok():
            return self.value
        else:
            return default

    def unwrap_err(self) -> E:
        """
        Get the error value or raise an exception if this is a success.

        Use this only when you're certain the result is Err.
        """
        if self.is_err():
            return self.error
        else:
            raise ValueError(f"Called unwrap_err() on Ok value: {self.value}")

    def map(self, func: Callable[[T], Any]) -> "Result":
        """Apply a function to the success value if Ok, otherwise return the Err."""
        if self.is_ok():
            try:
                return Ok(func(self.value))
            except Exception as e:
                return Err(str(e))
        else:
            return self

    def map_err(self, func: Callable[[E], Any]) -> "Result":
        """Apply a function to the error value if Err, otherwise return the Ok."""
        if self.is_err():
            return Err(func(self.error))
        else:
            return self



@dataclass
class Ok(Result[T, E]):
    """Success variant of Result."""

    value: T

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Ok) and self.value == other.value


@dataclass
class Err(Result[T, E]):
    """Error variant of Result."""

    error: E

    def __init__(self, error: E):
        self.error = error

    def __repr__(self) -> str:
        return f"Err({self.error!r})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Err) and self.error == other.error


