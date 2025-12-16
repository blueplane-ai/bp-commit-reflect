"""REPL mode for commit-reflect.

This package provides a persistent terminal interface that listens for
git commits via HTTP notifications and prompts users for reflections.
"""

from .display import REPLDisplay
from .input_handler import AsyncInputHandler
from .queue import CommitQueue, QueuedCommit
from .repl_session import REPLMode, run_repl_mode
from .server import CommitNotificationServer
from .state_machine import REPLState, StateContext, StateMachine

__all__ = [
    # State machine
    "REPLState",
    "StateMachine",
    "StateContext",
    # Queue
    "QueuedCommit",
    "CommitQueue",
    # Server
    "CommitNotificationServer",
    # Input
    "AsyncInputHandler",
    # Display
    "REPLDisplay",
    # Main
    "REPLMode",
    "run_repl_mode",
]
