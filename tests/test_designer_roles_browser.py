"""Required real Chromium role-workflow scenarios."""
import pytest

from playwright.sync_api import expect
from test_designer_roles import altered_candidate
from test_designer_browser import app, page  # noqa: F401


def test_browser_composes_inspects_runs_and_checks_role_fixtures(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        page.locator("#mode").select_option("roles", timeout=2000)
        expect(page.locator("#check")).to_be_enabled()
        expect(page.locator("#role-contracts")).to_contain_text("bounded_writing_brief")
        expect(page.locator("#role-contracts")).to_contain_text("review_verdict")
        expect(page.locator("#role-policy")).to_contain_text("historical")
        expect(page.locator("#graph")).to_contain_text("generator")
        expect(page.locator("#graph")).to_contain_text("evidence_handoff")
        expect(page.locator("#graph")).to_contain_text("review_verdict")
        expect(page.locator("#budget")).to_contain_text("2")
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("evidence_present")
        expect(page.locator("#run-result")).to_contain_text("synthetic-note")
        expect(page.locator("#run-result")).to_contain_text("Run evidence:")
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        expect(page.locator("#result")).to_contain_text("evidence_missing")
        page.locator("#role-fixture").select_option("without_evidence")
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#result")).to_contain_text("PASS")
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("evidence_missing")
        expect(page.locator("#run-result")).to_contain_text("COMPLETED")
        page.locator("#role-consumer").select_option("studio_producer")
        expect(page.locator("#status")).to_contain_text("Incompatible")
        expect(page.locator("#role-contracts")).to_contain_text("approved_copy")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#check")).to_be_disabled()
        page.locator("#role-output").select_option("caption")
        expect(page.locator("#status")).to_contain_text("Unsupported fixture operation")
        expect(page.locator("#run")).to_be_disabled()
        page.locator("#role-output").select_option("evidence_handoff")
        page.locator("#role-consumer").select_option("signal_guardian")
        expect(page.locator("#check")).to_be_enabled()
        page.locator("#mode").select_option("triage")
        expect(page.locator("#request-description")).to_be_visible()
        expect(page.locator("#role-fixture")).to_be_hidden()
        page.locator("#mode").select_option("score")
        expect(page.locator("#check")).to_be_enabled()


def open_roles(page, url):
    page.goto(url)
    page.locator("#mode").select_option("roles")
    expect(page.locator("#status")).to_have_text("Current design ready; not checked.")


@pytest.mark.parametrize("edit", ["fixture", "consumer", "producer", "output", "mode"])
@pytest.mark.parametrize("failure", [False, True])
def test_late_role_run_responses_cannot_restore_stale_results(page, tmp_path, edit, failure):
    options = {"candidate_factory": altered_candidate("generation")} if failure else {}
    with app(tmp_path, **options) as url:
        open_roles(page, url)
        held = []
        page.route("**/api/run", lambda route: held.append(route))
        page.locator("#run").click()
        expect(page.locator("#run-status")).to_have_text("Running offline…")
        page.wait_for_timeout(100)
        assert held
        if edit == "fixture":
            page.locator("#role-fixture").select_option("without_evidence")
        elif edit == "mode":
            page.locator("#mode").select_option("score")
        else:
            page.locator(f"#role-{edit}").select_option("caption" if edit == "output" else "studio_producer")
        held[0].fulfill(response=held[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#run-status")).to_contain_text("invalidated")
        if edit == "fixture":
            expect(page.locator("#run")).to_be_enabled()
        elif edit != "mode":
            expect(page.locator("#run")).to_be_disabled()


@pytest.mark.parametrize("failure", [False, True])
def test_late_role_check_and_design_responses_cannot_restore_rejected_composition(page, tmp_path, failure):
    options = {"candidate_factory": altered_candidate("generation")} if failure else {}
    with app(tmp_path, **options) as url:
        open_roles(page, url)
        checks, designs = [], []
        page.route("**/api/check", lambda route: checks.append(route))
        page.locator("#check").click()
        expect(page.locator("#status")).to_contain_text("Generating")
        page.wait_for_timeout(100)
        page.route("**/api/design", lambda route: designs.append(route))
        # Hold a valid response, then author an incompatible newer composition.
        page.locator("#role-consumer").select_option("signal_guardian")
        page.wait_for_timeout(100)
        assert designs
        page.unroute("**/api/design")
        page.locator("#role-consumer").select_option("studio_producer")
        expect(page.locator("#status")).to_contain_text("Incompatible")
        checks[0].fulfill(response=checks[0].fetch())
        designs[0].fulfill(response=designs[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#check")).to_be_disabled()
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#status")).to_contain_text("Incompatible")


@pytest.mark.parametrize("failure", ["generation", "unsupported", "budget", "route", "behavior", "execution", "evidence", "audit"])
def test_browser_role_failures_never_imply_conformance_or_run_success(page, tmp_path, monkeypatch, failure):
    if failure == "audit":
        from pathlib import Path
        original = Path.open
        def fail(path, mode="r", *args, **kwargs):
            if path.suffix == ".jsonl" and mode == "a+":
                raise OSError("audit unavailable")
            return original(path, mode, *args, **kwargs)
        monkeypatch.setattr(Path, "open", fail)
    options = {} if failure in ("evidence", "audit") else {"candidate_factory": altered_candidate(failure)}
    with app(tmp_path, **options) as url:
        open_roles(page, url)
        if failure == "evidence":
            (tmp_path / "evidence").write_text("blocked")
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("FAIL")
        expect(page.locator("#result")).not_to_contain_text("PASS")
        if failure != "behavior":
            page.locator("#run").click()
            expect(page.locator("#run-result")).to_contain_text("Run failed")
            expect(page.locator("#run-result")).not_to_contain_text("Run completed")


def test_fixture_selection_does_not_invalidate_inflight_case_scoped_check(page, tmp_path):
    with app(tmp_path) as url:
        open_roles(page, url)
        held = []
        page.route("**/api/check", lambda route: held.append(route))
        page.locator("#check").click()
        expect(page.locator("#status")).to_contain_text("Generating")
        page.wait_for_timeout(100)
        page.locator("#role-fixture").select_option("without_evidence")
        held[0].fulfill(response=held[0].fetch())
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        expect(page.locator("#result")).to_contain_text("with_evidence")
        expect(page.locator("#result")).to_contain_text("without_evidence")
        expect(page.locator("#run-result")).to_be_empty()


def test_browser_malformed_catalog_is_a_visible_nonexecuting_failure(page, tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from agent_lab.designer import author_design
    from test_designer_roles import DEFAULT
    catalog = author_design(DEFAULT).view()["catalog"]
    catalog["roles"][2]["reviews"] = []
    original = Path.read_text
    def corrupted(path, *args, **kwargs):
        return json.dumps(catalog) if path.name == "role_catalog.json" else original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", corrupted)
    with app(tmp_path) as url:
        page.goto(url)
        page.locator("#mode").select_option("roles")
        expect(page.locator("#status")).to_contain_text("review relationship")
        expect(page.locator("#check")).to_be_disabled()
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#result")).to_be_empty()
        assert not (tmp_path / "evidence").exists()


def test_role_contracts_and_candidate_outputs_render_inertly(page, tmp_path):
    from dataclasses import replace
    from agent_lab.designer import generate_candidate
    from agent_lab.reference import TransformResult
    payload = '<img src=x onerror="window.injected=1">'
    def factory(design):
        def inert(state):
            result = design.bindings["generate_handoff"](state)
            return TransformResult(result.state.model_copy(update={"handoff":
                result.state.handoff.model_copy(update={"text": payload})}), "done")
        return generate_candidate(replace(design, bindings={**design.bindings, "generate_handoff": inert}))
    with app(tmp_path, candidate_factory=factory) as url:
        open_roles(page, url)
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("<img src=x")
        expect(page.locator("#run-result img")).to_have_count(0)
        assert page.evaluate("window.injected") is None
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("behavioral_mismatch")
        expect(page.locator("#result img")).to_have_count(0)
