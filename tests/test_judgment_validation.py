"""Offline regression tests at the judgment and driver boundaries."""

from unittest.mock import MagicMock

import pytest
from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer, SystemOneResponse, Usage

from agent_lab.approvals import ApprovalStore
from agent_lab.graph_workflow import run_graph
from agent_lab.judgment import JevSource, JudgmentError, RecordedSource, StubSource
from agent_lab.runlog import RunLog
from agent_lab.state import Judgment, RunState, Stage, Terminal, Transition
from agent_lab.workflow import Deps, run_plain


def sdk_response(monkeypatch, answers, usage=None):
    response = SystemOneResponse(model="offline", answers=answers, usage=usage or Usage())
    client = MagicMock()
    client.__enter__.return_value.system_one.return_value = response
    monkeypatch.setattr("typesafe_sdk.TypeSafeClient", lambda **kwargs: client)
    return client


def valid_answers():
    return {
        "intervention": ChoiceAnswer(choice="review_follow_up", confidence=0.9, probabilities={}),
        "review_gap": NoulAnswer(noul=0.8),
    }


@pytest.mark.parametrize("key", ["intervention", "review_gap"])
@pytest.mark.parametrize("replacement", [None, ScoreAnswer(score=0.7, confidence=0.9, legend={}, probabilities={})])
def test_jev_rejects_missing_or_wrong_answer(monkeypatch, key, replacement):
    answers = valid_answers()
    if replacement is None:
        del answers[key]
    else:
        answers[key] = replacement
    sdk_response(monkeypatch, answers)
    with pytest.raises(JudgmentError, match=key):
        JevSource().judge("assessment")


@pytest.mark.parametrize("usage", [Usage(), Usage(input_tokens=0, output_tokens=17),
                                   Usage(input_tokens=12)])
def test_jev_preserves_unreported_usage(monkeypatch, usage):
    sdk_response(monkeypatch, valid_answers(), usage)
    source = JevSource()
    assert source.judge("assessment").source == "jev"
    assert source.last_usage == {
        "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
    }


@pytest.mark.parametrize("driver", [run_plain, run_graph])
def test_missing_sdk_answer_is_a_recorded_failure(monkeypatch, tmp_path, driver):
    sdk_response(monkeypatch, {})
    deps = Deps(JevSource(), ApprovalStore(tmp_path / "approvals"), RunLog(tmp_path / "log"))
    result = driver(RunState(run_id="missing", assessment_text="assessment"), deps)
    assert result.terminal is Terminal.FAILED_VALIDATION
    assert result.budget.used_steps == 2
    assert deps.log.read()[-1].transition == Transition.FAIL_VALIDATION.value
    assert "intervention" in deps.log.read()[-1].detail["error"]


@pytest.mark.parametrize("driver", [run_plain, run_graph])
@pytest.mark.parametrize("answer", [None, Judgment.model_construct(
    intervention="unknown", confidence=2, review_gap_evidenced=0.8, source="stub",
)])
def test_malformed_source_judgment_is_a_recorded_failure(tmp_path, driver, answer):
    class MalformedSource:
        name = "malformed"

        def judge(self, assessment):
            return answer

    deps = Deps(MalformedSource(), ApprovalStore(tmp_path / "approvals"), RunLog(tmp_path / "log"))
    result = driver(RunState(run_id="malformed", assessment_text="assessment"), deps)
    assert result.terminal is Terminal.FAILED_VALIDATION
    assert result.budget.used_steps == 2
    assert deps.log.read()[-1].transition == Transition.FAIL_VALIDATION.value
    assert "judgment" in deps.log.read()[-1].detail["error"]


@pytest.mark.parametrize("driver,stage", [
    (run_plain, Stage.ROUTE), (run_plain, Stage.PREPARE),
    (run_plain, Stage.VERIFY), (run_plain, Stage.APPROVE),
    (run_graph, Stage.APPROVE),
])
def test_missing_state_judgment_is_a_recorded_failure(tmp_path, driver, stage):
    deps = Deps(StubSource(), ApprovalStore(tmp_path / "approvals"), RunLog(tmp_path / "log"))
    state = RunState(run_id="missing", stage=stage, draft="draft\n", draft_digest="digest")
    result = driver(state, deps)
    assert result.terminal is Terminal.FAILED_VALIDATION
    assert result.budget.used_steps == 1
    event = deps.log.read()[-1]
    assert event.transition == Transition.FAIL_VALIDATION.value
    assert "judgment" in event.detail["error"]


@pytest.mark.parametrize("driver", [run_plain, run_graph])
@pytest.mark.parametrize("payload", ["{", "[]", "{}",
    '{"intervention":"review_follow_up","confidence":null,"review_gap":0.8}',
])
def test_malformed_recording_is_a_recorded_failure(tmp_path, driver, payload):
    recording = tmp_path / "recording.json"
    recording.write_text(payload)
    deps = Deps(RecordedSource(recording), ApprovalStore(tmp_path / "approvals"),
                RunLog(tmp_path / "log"))
    result = driver(RunState(run_id="recording", assessment_text="assessment"), deps)
    assert result.terminal is Terminal.FAILED_VALIDATION
    assert deps.log.read()[-1].transition == Transition.FAIL_VALIDATION.value

