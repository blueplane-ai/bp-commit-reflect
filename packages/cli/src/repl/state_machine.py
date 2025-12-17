"""REPL state machine for managing interactive reflection flow."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class REPLState(Enum):
    """REPL state machine states."""

    HOME = auto()  # Idle, waiting for commits or commands
    PROMPTING = auto()  # Showing "Start reflection?" prompt
    IN_REFLECTION = auto()  # Actively answering questions
    COMPLETING = auto()  # Saving and finishing reflection


@dataclass
class StateContext:
    """Context passed during state transitions."""

    current_commit_hash: str | None = None
    pending_count: int = 0
    current_question_index: int = 0
    last_error: str | None = None
    metadata: dict = field(default_factory=dict)


# Type alias for state transition callbacks
StateTransitionCallback = Callable[[REPLState, REPLState, StateContext], None]


class StateMachine:
    """Manages REPL state transitions with validation and callbacks."""

    # Valid state transitions
    _VALID_TRANSITIONS: dict[REPLState, list[REPLState]] = {
        REPLState.HOME: [REPLState.PROMPTING],
        REPLState.PROMPTING: [REPLState.HOME, REPLState.IN_REFLECTION],
        REPLState.IN_REFLECTION: [REPLState.COMPLETING, REPLState.HOME],
        REPLState.COMPLETING: [REPLState.HOME, REPLState.PROMPTING],
    }

    def __init__(self, initial_state: REPLState = REPLState.HOME):
        """Initialize state machine.

        Args:
            initial_state: Starting state (default: HOME)
        """
        self._state = initial_state
        self._context = StateContext()
        self._listeners: list[StateTransitionCallback] = []

    @property
    def state(self) -> REPLState:
        """Current state."""
        return self._state

    @property
    def context(self) -> StateContext:
        """Current context."""
        return self._context

    def transition_to(
        self,
        new_state: REPLState,
        context_updates: dict[str, Any] | None = None,
    ) -> bool:
        """Transition to a new state if valid.

        Args:
            new_state: Target state
            context_updates: Optional dict of context field updates

        Returns:
            True if transition succeeded, False if invalid
        """
        if not self._is_valid_transition(self._state, new_state):
            return False

        old_state = self._state
        self._state = new_state

        # Update context if provided
        if context_updates:
            for key, value in context_updates.items():
                if hasattr(self._context, key):
                    setattr(self._context, key, value)
                else:
                    self._context.metadata[key] = value

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(old_state, new_state, self._context)
            except Exception:
                # Don't let listener errors break state transitions
                pass

        return True

    def _is_valid_transition(self, from_state: REPLState, to_state: REPLState) -> bool:
        """Check if a state transition is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is allowed
        """
        valid_targets = self._VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_targets

    def on_transition(self, callback: StateTransitionCallback) -> None:
        """Register a callback for state transitions.

        Args:
            callback: Function called with (old_state, new_state, context)
        """
        self._listeners.append(callback)

    def remove_listener(self, callback: StateTransitionCallback) -> bool:
        """Remove a transition listener.

        Args:
            callback: The callback to remove

        Returns:
            True if callback was found and removed
        """
        try:
            self._listeners.remove(callback)
            return True
        except ValueError:
            return False

    def is_busy(self) -> bool:
        """Check if currently in a state where commits should be queued.

        Returns:
            True if IN_REFLECTION or COMPLETING
        """
        return self._state in (REPLState.IN_REFLECTION, REPLState.COMPLETING)

    def is_idle(self) -> bool:
        """Check if in idle/home state.

        Returns:
            True if HOME
        """
        return self._state == REPLState.HOME

    def can_transition_to(self, target: REPLState) -> bool:
        """Check if transition to target state is currently valid.

        Args:
            target: Target state to check

        Returns:
            True if transition would be allowed
        """
        return self._is_valid_transition(self._state, target)

    def reset(self) -> None:
        """Reset state machine to initial HOME state with fresh context."""
        self._state = REPLState.HOME
        self._context = StateContext()

    def __repr__(self) -> str:
        return f"StateMachine(state={self._state.name}, busy={self.is_busy()})"
