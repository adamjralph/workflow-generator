"""Ticket 02: synthetic concurrency at the typed-state/Deps boundary."""
import asyncio
from dataclasses import replace

import pytest

from pydantic_graph import GraphBuilder, StepContext, reduce_list_append

from agent_lab.graph_workflow import GraphState, run_graph
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

from agent_lab.state import Terminal

from agent_lab.approvals import ApprovalStore
from agent_lab.judgment import StubSource
from agent_lab.runlog import RunLog
from agent_lab.state import Budget, RunState, Stage
from agent_lab.workflow import Deps, collect_findings, run_plain, step


class OverlappingSource(StubSource):
    """Both model calls must enter before either can finish (not a timing guess)."""

    def __init__(self, parties: int = 2):
        super().__init__()
        self.barrier = Barrier(parties, timeout=5)

    def judge(self, assessment: str):
        self.barrier.wait()
        return super().judge(assessment)


def dependencies(tmp_path: Path, source=None) -> Deps:
    return Deps(source or StubSource(), ApprovalStore(tmp_path / 'approvals.jsonl'),
                RunLog(tmp_path / 'run.jsonl'))


def base(cap: int = 12) -> RunState:
    return RunState(run_id='parallel', assessment_text='synthetic finding',
                    stage=Stage.CLASSIFY, budget=Budget(max_steps=cap))


def two_steps(state: RunState, deps: Deps) -> list[RunState]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(step, state, deps, 'classify', 0) for _ in range(2)]
        return [future.result(timeout=10) for future in futures]


def test_concurrent_events_have_run_level_sequence_in_append_order(tmp_path):
    deps = dependencies(tmp_path, OverlappingSource())
    two_steps(base(), deps)
    assert [event.seq for event in deps.log.read()] == [0, 1]


def test_two_concurrent_steps_spend_two_from_one_run_budget(tmp_path):
    deps = dependencies(tmp_path, OverlappingSource())
    results = two_steps(base(cap=2), deps)
    assert [result.budget.used_steps for result in results] == [2, 2]


def test_parallel_work_cannot_exceed_cap_while_first_call_is_in_flight(tmp_path):
    entered, release = Event(), Event()

    class HeldSource(StubSource):
        def judge(self, assessment):
            entered.set()
            assert release.wait(5), 'model call was never released'
            return super().judge(assessment)

    deps = dependencies(tmp_path, HeldSource())
    state = base(cap=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(step, state, deps, 'classify', 0)
        assert entered.wait(5)
        # Intake is a real second step, but must be refused before doing work.
        second = pool.submit(step, state.model_copy(update={'stage': Stage.INTAKE}),
                             deps, 'intake', 0)
        try:
            refused = second.result(timeout=5)
            assert refused.terminal is Terminal.FAILED_BUDGET
            assert refused.budget.used_steps == 1
        finally:
            release.set()
        assert first.result(timeout=5).budget.used_steps == 1
    assert [event.seq for event in deps.log.read()] == [0, 1]


def test_three_findings_survive_read_await_join(tmp_path):
    deps = dependencies(tmp_path, OverlappingSource(3))
    holder = GraphState(base(cap=3))
    builder = GraphBuilder(state_type=GraphState, deps_type=Deps,
                           input_type=list[str], output_type=RunState)

    @builder.step
    async def start(ctx: StepContext[GraphState, Deps, list[str]]) -> list[str]:
        return ctx.inputs

    @builder.step
    async def branch(ctx: StepContext[GraphState, Deps, str]) -> RunState:
        before = ctx.state.current
        after = await asyncio.to_thread(step, before, ctx.deps, 'classify', 0)
        after = after.model_copy(update={'notes': before.notes + (ctx.inputs,)})
        return after

    joined = builder.join(reduce_list_append, initial_factory=list[RunState])

    @builder.step
    async def chair(ctx: StepContext[GraphState, Deps, list[RunState]]) -> RunState:
        assert len(ctx.inputs) == 3
        return collect_findings(ctx.state.current, ctx.inputs, ctx.deps)

    builder.add(
        builder.edge_from(builder.start_node).to(start),
        builder.edge_from(start).map(fork_id='findings').to(branch),
        builder.edge_from(branch).to(joined),
        builder.edge_from(joined).to(chair),
        builder.edge_from(chair).to(builder.end_node),
    )
    result = builder.build().run_sync(state=holder, deps=deps,
                                      inputs=['legal', 'pricing', 'ops'])
    assert result.notes == ('legal', 'ops', 'pricing')
    assert result.budget.used_steps == 3
    assert holder.current.notes == ()  # no shared read/await/write accumulation


def test_overlapping_drivers_replay_identical_events_and_digests(tmp_path):
    outcomes = []
    for driver in (run_plain, run_graph):
        finished_first = Event()

        class ScheduledSource(OverlappingSource):
            def judge(self, assessment):
                judgment = super().judge(assessment)
                if assessment == 'second':
                    assert finished_first.wait(5)
                return judgment

        deps = dependencies(tmp_path / driver.__name__, ScheduledSource())
        state = base().model_copy(update={'stage': Stage.INTAKE})

        def branch(name):
            try:
                return driver(state.model_copy(update={'assessment_text': name}), deps)
            finally:
                if name == 'first!':
                    finished_first.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(branch, 'first!')
            second = pool.submit(branch, 'second')
            results = [first.result(timeout=10), second.result(timeout=10)]
        joined = collect_findings(state, results, deps)
        assert joined.budget.used_steps == 12
        assert [event.seq for event in deps.log.read()] == list(range(12))
        assert all(result.terminal is Terminal.NEEDS_REVIEW for result in results)
        outcomes.append((deps.log.read(), deps.log.digest(),
                         [result.draft_digest for result in results]))
    assert outcomes[0] == outcomes[1]


def test_separate_log_handles_share_sequence_allocation(tmp_path):
    deps = dependencies(tmp_path, OverlappingSource())
    other = replace(deps, log=RunLog(deps.log.path))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(step, base(), d, 'classify', 999) for d in (deps, other)]
        for future in futures:
            future.result(timeout=10)
    assert [event.seq for event in deps.log.read()] == [0, 1]


def test_join_keeps_common_notes_once_and_refreshes_a_stale_branch_budget(tmp_path):
    deps = dependencies(tmp_path)
    state = base(cap=2).model_copy(update={'notes': ('brief',)})
    first = step(state, deps, 'classify')
    second = step(state, deps, 'classify')
    assert first.budget.used_steps == 1  # immutable point-in-time snapshot
    branches = [first.model_copy(update={'notes': ('brief', 'legal')}),
                second.model_copy(update={'notes': ('brief', 'ops')})]
    joined = collect_findings(state, reversed(branches), deps)
    assert joined.notes == ('brief', 'legal', 'ops')
    assert joined.budget.used_steps == 2
    fresh = dependencies(tmp_path)
    assert step(joined, fresh, 'classify').terminal is Terminal.FAILED_BUDGET
    assert [event.seq for event in fresh.log.read()] == [0, 1, 2]


@pytest.mark.parametrize('update', [{'run_id': 'other'}, {'notes': ('changed',)}])
def test_join_rejects_unrelated_branch_snapshots(tmp_path, update):
    state = base().model_copy(update={'notes': ('brief',)})
    with pytest.raises(ValueError):
        collect_findings(state, [state.model_copy(update=update)], dependencies(tmp_path))


def test_budget_owner_keeps_runs_independent_and_rejects_changed_caps(tmp_path):
    deps = dependencies(tmp_path)
    state = base(cap=1)
    step(state, deps, 'classify')
    unrelated = step(state.model_copy(update={'run_id': 'other'}), deps, 'classify')
    assert unrelated.budget.used_steps == 1
    assert unrelated.terminal is None
    with pytest.raises(ValueError, match='same step cap'):
        step(base(cap=2), deps, 'classify')
