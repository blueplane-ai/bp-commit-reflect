"""REPL mode for commit-reflect.

This package provides a persistent terminal interface that listens for
git commits via HTTP notifications and prompts users for reflections.
"""

from .state_machine import REPLState, StateMachine, StateContext
from .queue import QueuedCommit, CommitQueue
from .server import CommitNotificationServer
from .input_handler import AsyncInputHandler
from .display import REPLDisplay
from .repl_session import REPLMode, run_repl_mode

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
