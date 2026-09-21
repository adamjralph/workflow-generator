"""Real protected loopback Check; recordings never cause new model work."""
import json
from pathlib import Path

import pytest

from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_draft_run_server import FixtureSource, capture, post
from tests.test_designer_review_server import GuardianSource
from tests.test_designer_server import credentials, request, running_server


def test_http_check_uses_completed_identity_and_survives_restart_without_live_adapters(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource()
    with running_server(evidence, draft_config=config, draft_model_source=generator,
                        guardian_model_source=guardian) as server:
        identity = capture(server)
        saved = post(server, "/api/drafts/run", identity)[1]
        status, result = post(server, "/api/drafts/check", identity)
        assert status == 200 and result["passed"]
        assert result["snapshot"] == identity["snapshot"] and result["run_request"] == identity["run_request"]
        assert result["historical_usage"] == saved["role_usage"]
        assert result["model_calls"] == result["auth_requests"] == 0
        assert len(generator.requests) == len(guardian.requests) == 1
    # Normal startup has adapters with deliberately nonexistent credential files.
    with running_server(evidence, draft_config=config, codex_auth_file=folder / "missing-codex",
                        vertex_auth_file=folder / "missing-vertex") as server:
        fresh = post(server, "/api/drafts/check", identity)[1]
        assert fresh["passed"] and fresh["evidence"] != result["evidence"]
        assert Path(fresh["check_receipt"]).exists()


@pytest.mark.parametrize("change", ["token", "origin", "host", "json", "extra", "identity", "missing"])
def test_check_rejects_invalid_http_boundaries_before_replay(operator, change):
    config, folder, evidence = operator
    draft(folder, "old.md")
    with running_server(evidence, draft_config=config, draft_model_source=FixtureSource(),
                        guardian_model_source=GuardianSource()) as server:
        identity = capture(server)
        post(server, "/api/drafts/run", identity)
        headers = credentials(server)
        if change in ("token", "origin", "host", "json"):
            headers[{"token": "X-Designer-Token", "origin": "Origin", "host": "Host",
                     "json": "Content-Type"}[change]] = "wrong"
        elif change == "extra":
            identity["path"] = "/private/secret"
        elif change == "identity":
            identity["run_request"] = "../receipt.json"
        else:
            identity.pop("snapshot")
        status, _, body = request(server, "/api/drafts/check", method="POST", headers=headers,
                                   body=json.dumps(identity))
        assert status in (400, 403, 415) and not json.loads(body)["passed"]
        assert not list(evidence.glob("draft-check-*"))


def test_check_rejects_cross_capture_and_corrupt_receipt_without_new_calls(operator):
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource()
    with running_server(evidence, draft_config=config, draft_model_source=generator,
                        guardian_model_source=guardian) as server:
        identity = capture(server)
        post(server, "/api/drafts/run", identity)
        selected.write_text(selected.read_text() + "Changed source")
        newer = capture(server)
        cross = {**identity, "snapshot": newer["snapshot"]}
        for submitted in (cross, newer):
            status, result = post(server, "/api/drafts/check", submitted)
            assert status == 200 and not result["passed"] and result["completed_cases"] == []
        (evidence / "draft-runs" / identity["run_request"] / "receipt.json").write_text("SECRET_BAD_JSON")
        status, result = post(server, "/api/drafts/check", identity)
        assert status == 200 and not result["passed"]
        assert "SECRET_BAD_JSON" not in json.dumps(result)
        assert len(generator.requests) == len(guardian.requests) == 1
