"""Chromium + actual HTTP + real draft execution, with a fixture model source."""
import pytest
from playwright.sync_api import expect

from test_designer_browser import app, page  # noqa: F401
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_drafts_browser import capture_draft, open_drafts
from tests.test_designer_draft_run_server import FixtureSource, POST


def test_explicit_generator_run_inert_output_usage_and_warned_new_run(page, tmp_path, operator):
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    original = selected.read_bytes()
    source = FixtureSource()
    with app(tmp_path, draft_config=config, draft_model_source=source) as url:
        open_drafts(page, url)
        expect(page.locator("#draft-run")).to_be_disabled()
        capture_draft(page)
        assert not source.requests
        expect(page.locator("#check")).not_to_be_visible()
        page.get_by_role("button", name="Run Signal Generator", exact=True).click()
        expect(page.locator("#draft-run-status")).to_contain_text("Not reviewed")
        assert POST in page.locator("#draft-run-result").text_content()
        expect(page.locator("#draft-run-result")).to_contain_text('"input_tokens": 17')
        expect(page.locator("#draft-run-result")).to_contain_text('"output_tokens": 9')
        assert page.evaluate("window.injected") is None
        assert len(source.requests) == 1
        expect(page.locator("#draft-run")).to_be_disabled()
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#draft-new-request").click()
        expect(page.locator("#draft-run")).to_be_disabled()
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#draft-new-request").click()
        expect(page.locator("#draft-run-status")).to_contain_text("New request ready on the same capture")
        assert len(source.requests) == 1
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Not reviewed")
        assert len(source.requests) == 2
    assert selected.read_bytes() == original


def test_recapture_warns_after_attempt_but_never_runs_automatically(page, tmp_path, operator):
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    source = FixtureSource()
    with app(tmp_path, draft_config=config, draft_model_source=source) as url:
        open_drafts(page, url)
        capture_draft(page)
        capture_draft(page)
        expect(page.locator("#draft-status")).not_to_contain_text("already run")
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Not reviewed")
        capture_draft(page)
        expect(page.locator("#draft-status")).to_contain_text("already run")
        expect(page.locator("#draft-status")).to_contain_text("another model call")
        assert len(source.requests) == 1
        selected.write_bytes(selected.read_bytes() + b"Changed body.\n")
        capture_draft(page)
        expect(page.locator("#draft-status")).not_to_contain_text("already run")
        assert len(source.requests) == 1


def test_lost_run_response_is_uncertain_and_same_identity_is_safe(page, tmp_path, operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = FixtureSource()
    with app(tmp_path, draft_config=config, draft_model_source=source) as url:
        open_drafts(page, url)
        capture_draft(page)
        def lose_response(route):
            route.fetch()  # The server executed; only the response is lost.
            route.abort("failed")
        page.route("**/api/drafts/run", lose_response)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Uncertain")
        assert len(source.requests) == 1
        page.unroute("**/api/drafts/run", lose_response)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Not reviewed")
        assert len(source.requests) == 1


@pytest.mark.parametrize("outcome,label", [("blocked", "Blocked"), ("invalid", "Failed"),
                                           ("exception", "Failed"), ("timeout", "Uncertain")])
def test_real_execution_states_are_distinct(page, tmp_path, operator, outcome, label):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = FixtureSource(outcome)
    with app(tmp_path, draft_config=config, draft_model_source=source) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text(label)
        expect(page.locator("body")).not_to_contain_text("SECRET_PROVIDER_FAILURE")
        expect(page.locator("body")).not_to_contain_text("bearer-secret")
        expect(page.locator("#draft-new-request")).to_be_enabled()
        assert len(source.requests) == 1


@pytest.mark.parametrize("change", ["recapture", "mode"])
@pytest.mark.parametrize("outcome", ["draft", "invalid", "timeout"])
def test_late_run_response_cannot_restore_invalidated_display(page, tmp_path, operator, change, outcome):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = FixtureSource(outcome)
    with app(tmp_path, draft_config=config, draft_model_source=source) as url:
        open_drafts(page, url)
        capture_draft(page)
        held = []
        # Delay delivery only: fetch still executes the real HTTP endpoint and drivers.
        page.route("**/api/drafts/run", lambda route: held.append((route, route.fetch())))
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Running")
        for _ in range(50):
            if held:
                break
            page.wait_for_timeout(20)
        assert held and len(source.requests) == 1
        if change == "recapture":
            capture_draft(page)
        else:
            page.locator("#mode").select_option("score")
        route, response = held[0]
        route.fulfill(response=response)
        page.wait_for_timeout(100)
        expect(page.locator("#draft-run-result")).to_be_empty()
        expect(page.locator("#draft-run-status")).to_contain_text("previous display invalidated")
        if change == "mode":
            open_drafts(page, url)
            expect(page.locator("#draft-run")).to_be_disabled()
        assert len(source.requests) == 1
