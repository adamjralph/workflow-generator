"""Ticket 02: synthetic concurrency at the typed-state/Deps boundary."""
import asyncio

from pydantic_graph import GraphBuilder, StepContext, reduce_list_append

from agent_lab.graph_workflow import GraphState
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

from agent_lab.state import Terminal

from agent_lab.approvals import ApprovalStore
from agent_lab.judgment import StubSource
from agent_lab.runlog import RunLog
from agent_lab.state import Budget, RunState, Stage
from agent_lab.workflow import Deps, step


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
        ctx.state.current = after
        return after

    joined = builder.join(reduce_list_append, initial_factory=list[RunState])

    @builder.step
    async def chair(ctx: StepContext[GraphState, Deps, list[RunState]]) -> RunState:
        assert len(ctx.inputs) == 3
        return ctx.state.current

    builder.add(
        builder.edge_from(builder.start_node).to(start),
        builder.edge_from(start).map(fork_id='findings').to(branch),
        builder.edge_from(branch).to(joined),
        builder.edge_from(joined).to(chair),
        builder.edge_from(chair).to(builder.end_node),
    )
    result = builder.build().run_sync(state=holder, deps=deps,
                                      inputs=['legal', 'pricing', 'ops'])
    assert sorted(result.notes) == ['legal', 'ops', 'pricing']
