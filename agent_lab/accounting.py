"""Run-level step reservations, shared by every branch through Deps.

This is in-process accounting, not a durable execution service. A resumed run
seeds a fresh owner from its joined typed state. Never resume from one branch's
snapshot or create separate owners for concurrently executing branches.
"""
from threading import Lock

from .state import Budget, RunState


class RunAccounting:
    """Reserve before work; model calls never hold the accounting lock."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._budgets: dict[str, Budget] = {}

    def spend(self, state: RunState) -> Budget:
        return self.reserve(state.run_id, state.budget)

    def reserve(self, run_id: str, initial: Budget) -> Budget:
        """Reserve one step independently of business-specific state fields."""
        with self._lock:
            budget = self._budgets.setdefault(run_id, initial)
            if budget.max_steps != initial.max_steps:
                raise ValueError("branches of a run must declare the same step cap")
            spent = budget.spend()
            self._budgets[run_id] = spent
            return spent

    def snapshot(self, state: RunState) -> RunState:
        """Refresh accounting without overwriting any branch-local results."""
        with self._lock:
            budget = self._budgets.get(state.run_id, state.budget)
            return state.model_copy(update={"budget": budget})
