from inspect import getmembers, isfunction
from sys import exc_info
from traceback import format_tb
from typing import Optional, Self


class ClueException(Exception):
    """Wrapper for all exceptions thrown in Clue' code"""

    message: str
    cause: Exception | None
    status_code: int | None

    def __init__(
        self: Self,
        message: str = "Something went wrong",
        cause: Exception | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.status_code = status_code

    def __repr__(self: Self) -> str:
        """String reproduction of the Clue exception. Pass the message on"""
        return self.message


class InvalidClassification(ClueException):
    """Exception for Invalid Classification"""


class InvalidDefinition(ClueException):
    """Exception for Invalid Definition"""


class InvalidRangeException(ClueException):
    """Exception for Invalid Range"""


class NonRecoverableError(ClueException):
    """Exception for an unrecoverable error"""


class RecoverableError(ClueException):
    """Exception for a recoverable error"""


class ConfigException(ClueException):
    """Exception thrown due to invalid configuration"""


class ResourceExists(ClueException):
    """Exception thrown due to a pre-existing resource"""


class VersionConflict(ClueException):
    """Exception thrown due to a version conflict"""

    def __init__(self: Self, message: str = "Something went wrong", cause: Optional[Exception] = None) -> None:
        ClueException.__init__(self, message, cause)


class ClueTypeError(ClueException, TypeError):
    """TypeError child specifically for exceptions thrown by us"""

    def __init__(
        self: Self,
        message: str = "Something went wrong",
        cause: Optional[Exception] = None,
        status_code: int | None = None,
    ) -> None:
        ClueException.__init__(
            self, message, cause if cause is not None else TypeError(message), status_code=status_code
        )


class ClueAttributeError(ClueException, AttributeError):
    """AttributeError child specifically for exceptions thrown by us"""

    def __init__(
        self: Self,
        message: str = "Something went wrong",
        cause: Optional[Exception] = None,
        status_code: int | None = None,
    ) -> None:
        ClueException.__init__(
            self, message, cause if cause is not None else AttributeError(message), status_code=status_code
        )


class ClueValueError(ClueException, ValueError):
    """ValueError child specifically for exceptions thrown by us"""

    def __init__(
        self: Self,
        message: str = "Something went wrong",
        cause: Optional[Exception] = None,
        status_code: int | None = None,
    ) -> None:
        ClueException.__init__(
            self, message, cause if cause is not None else ValueError(message), status_code=status_code
        )


class ClueNotImplementedError(ClueException, NotImplementedError):
    """NotImplementedError child specifically for exceptions thrown by us"""

    def __init__(self: Self, message: str = "Something went wrong", cause: Optional[Exception] = None) -> None:
        ClueException.__init__(self, message, cause if cause is not None else NotImplementedError(message))


class ClueKeyError(ClueException, KeyError):
    """KeyError child specifically for exceptions thrown by us"""

    def __init__(self: Self, message: str = "Something went wrong", cause: Optional[Exception] = None) -> None:
        ClueException.__init__(self, message, cause if cause is not None else KeyError(message))


class ClueRuntimeError(ClueException, RuntimeError):
    """RuntimeError child specifically for exceptions thrown by us"""

    def __init__(self: Self, message: str = "Something went wrong", cause: Optional[Exception] = None) -> None:
        ClueException.__init__(self, message, cause if cause is not None else RuntimeError(message))


class NotFoundException(ClueException):
    """Exception thrown when a resource cannot be found"""


class AccessDeniedException(ClueException):
    """Exception thrown when a resource cannot be accessed by a user"""


class InvalidDataException(ClueException):
    """Exception thrown when user-provided data is invalid"""


class AuthenticationException(ClueException):
    """Exception thrown when a user cannot be authenticated"""


class TimeoutException(ClueException):
    """Exception for Timeout"""


class UnprocessableException(ClueException):
    """Exception for Unprocessable"""


class Chain(object):
    """This class can be used as a decorator to override the type of exceptions returned by a function"""

    def __init__(self: Self, exception: type[Exception]):
        self.exception = exception

    def __call__(self, original):
        """Execute a function and wrap any resulting exceptions"""

        def wrapper(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception as e:
                wrapped = self.exception(str(e), e)
                raise wrapped.with_traceback(exc_info()[2])

        wrapper.__name__ = original.__name__
        wrapper.__doc__ = original.__doc__
        wrapper.__dict__.update(original.__dict__)

        return wrapper

    def execute(self, func, *args, **kwargs):
        """Execute a function and wrap any resulting exceptions"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            wrapped = self.exception(str(e), e)
            raise wrapped.with_traceback(exc_info()[2])


class ChainAll:
    """This class can be used as a decorator to override the type of exceptions returned by every method of a class"""

    def __init__(self: Self, exception: type[Exception]):
        self.exception = Chain(exception)

    def __call__(self, cls):
        """We can use an instance of this class as a decorator."""
        for method in getmembers(cls, predicate=isfunction):
            setattr(cls, method[0], self.exception(method[1]))

        return cls


def get_stacktrace_info(ex: Exception) -> str:
    """Get and format traceback information from a given exception"""
    return "".join(format_tb(exc_info()[2]) + [": ".join((ex.__class__.__name__, str(ex)))])
