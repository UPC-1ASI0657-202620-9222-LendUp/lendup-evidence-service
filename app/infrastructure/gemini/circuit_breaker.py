"""Process-local asynchronous circuit breaker with one recovery probe."""
import asyncio
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from time import monotonic


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    pass


@dataclass(frozen=True)
class Permit:
    generation: int
    probe: bool


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_seconds=60, clock=monotonic):
        if failure_threshold < 1 or recovery_seconds <= 0:
            raise ValueError("Invalid circuit breaker settings")
        self.threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.clock = clock
        self._lock = Lock()
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._generation = 0

    @property
    def state(self):
        with self._lock:
            return self._state

    def acquire(self):
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self.clock() - self._opened_at < self.recovery_seconds:
                    raise CircuitOpenError("Gemini temporalmente no disponible")
                self._state = CircuitState.HALF_OPEN
                self._generation += 1
                return Permit(self._generation, True)
            if self._state == CircuitState.HALF_OPEN:
                raise CircuitOpenError("Recuperación de Gemini en curso")
            return Permit(self._generation, False)

    def _open(self):
        self._state = CircuitState.OPEN
        self._opened_at = self.clock()
        self._generation += 1

    def success(self, permit):
        with self._lock:
            if permit.generation != self._generation:
                return
            self._failures = 0
            if permit.probe:
                self._state = CircuitState.CLOSED
                self._generation += 1

    def failure(self, permit):
        with self._lock:
            if permit.generation != self._generation:
                return
            self._failures += 1
            if permit.probe or self._failures >= self.threshold:
                self._open()

    def abandon(self, permit):
        # A cancelled/neutral recovery probe must not leave HALF_OPEN stuck.
        with self._lock:
            if permit.probe and permit.generation == self._generation:
                self._open()

    async def call(self, operation, counts_failure=lambda exc: True):
        permit = self.acquire()
        try:
            result = await operation()
        except asyncio.CancelledError:
            self.abandon(permit)
            raise
        except Exception as exc:
            if counts_failure(exc):
                self.failure(permit)
            else:
                self.abandon(permit)
            raise
        else:
            self.success(permit)
            return result


gemini_breaker = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
