"""Real Chromium/HTTP pair execution with independent offline fixture sources."""
import hashlib

import pytest
from playwright.sync_api import expect

from test_designer_browser import app, page  # noqa: F401
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_drafts_browser import capture_draft, open_drafts
from tests.test_designer_review_server import (
    GuardianSource, FixtureSource, POST, DETAIL, DIAGNOSTIC_CODES, diagnostic_guardian,
)


@pytest.mark.parametrize("verdict", ["Approved", "Changes requested", "Blocked"])
def test_browser_completed_editorial_verdict_exact_copy_inert_review_usage(page, tmp_path, operator, verdict):
    config, folder, _ = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource(verdict)
    with app(tmp_path, draft_config=config, draft_model_source=generator, guardian_model_source=guardian) as url:
        open_drafts(page, url)
        expect(page.locator("#draft-policy")).to_contain_text("two generation attempts")
        capture_draft(page)
        assert not generator.requests and not guardian.requests
        page.get_by_role("button", name="Run Generator + Guardian", exact=True).click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        expect(page.locator("#draft-run-status")).to_contain_text("no publication permission")
        result = page.locator("#draft-run-result")
        expect(result).to_contain_text(verdict)
        assert POST in result.text_content() and DETAIL in result.text_content()
        expect(result).to_contain_text(hashlib.sha256(POST.encode()).hexdigest())
        for value in ["Image consistency not reviewed.", "copy-only", "Required fixes", "Optional preferences",
                      '"input_tokens": 17', '"input_tokens": 31', '"auth_requests": 1']:
            expect(result).to_contain_text(value)
        for req in [generator.requests[0], guardian.requests[0]]:
            for value in [req.operation, req.operation_version, req.schema_version]:
                expect(result).to_contain_text(value)
        assert result.locator("script, img").count() == 0
        assert page.evaluate("window.injected") is None
        expect(page.locator("#draft-run")).to_be_disabled()
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#draft-new-request").click()
        expect(page.locator("#draft-run")).to_be_disabled()
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#draft-new-request").click()
        expect(page.locator("#draft-run")).to_be_enabled()
        assert len(generator.requests) == len(guardian.requests) == 1
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        assert len(generator.requests) == len(guardian.requests) == 2
        capture_draft(page)
        expect(page.locator("#draft-status")).to_contain_text("already run")
        assert len(generator.requests) == len(guardian.requests) == 2


@pytest.mark.parametrize("outcome,label", [("invalid", "Failed"), ("exception", "Failed"), ("timeout", "Uncertain")])
def test_browser_guardian_failure_retains_unreviewed_exact_copy(page, tmp_path, operator, outcome, label):
    config, folder, _ = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource(outcome=outcome)
    with app(tmp_path, draft_config=config, draft_model_source=generator, guardian_model_source=guardian) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text(label)
        result = page.locator("#draft-run-result")
        assert POST in result.text_content()
        expect(result).to_contain_text("No valid Guardian review")
        expect(result).not_to_contain_text("Approved")
        expect(page.locator("body")).not_to_contain_text("SECRET_PROVIDER_FAILURE")
        assert len(generator.requests) == len(guardian.requests) == 1


@pytest.mark.parametrize("code", DIAGNOSTIC_CODES)
def test_browser_displays_only_sanitized_diagnostic(page, tmp_path, operator, code):
    config, folder, _ = operator
    draft(folder, "old.md")
    (config.parent / "guardian.yaml").write_text("model:\n  provider: vertex\n  default: guardian-model\n")
    guardian, calls = diagnostic_guardian(tmp_path, code)
    with app(tmp_path, draft_config=config, draft_model_source=FixtureSource(), guardian_model_source=guardian) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Failed")
        expect(page.locator("#draft-run-result")).to_contain_text(code)
        expect(page.locator("body")).not_to_contain_text("SECRET_PROVIDER_COOKIE")
        expect(page.locator("#draft-run")).to_be_disabled()
        assert len(calls) == 1


@pytest.mark.parametrize("change", ["recapture", "mode"])
def test_browser_late_pair_response_cannot_restore_invalidated_display(page, tmp_path, operator, change):
    config, folder, _ = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource()
    with app(tmp_path, draft_config=config, draft_model_source=generator, guardian_model_source=guardian) as url:
        open_drafts(page, url)
        capture_draft(page)
        held = []
        page.route("**/api/drafts/run", lambda route: held.append((route, route.fetch())))
        page.locator("#draft-run").click()
        for _ in range(50):
            if held:
                break
            page.wait_for_timeout(20)
        assert held and len(guardian.requests) == 1
        if change == "recapture":
            capture_draft(page)
        else:
            page.locator("#mode").select_option("score")
        route, response = held[0]
        route.fulfill(response=response)
        page.wait_for_timeout(100)
        expect(page.locator("#draft-run-result")).to_be_empty()
        expect(page.locator("#draft-run-status")).to_contain_text("previous display invalidated")
        assert len(generator.requests) == len(guardian.requests) == 1


def test_browser_lost_pair_response_inspects_same_identity_without_resend(page, tmp_path, operator):
    config, folder, _ = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource()
    with app(tmp_path, draft_config=config, draft_model_source=generator, guardian_model_source=guardian) as url:
        open_drafts(page, url)
        capture_draft(page)
        def lose_response(route):
            route.fetch()
            route.abort("failed")
        page.route("**/api/drafts/run", lose_response)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Uncertain")
        page.unroute("**/api/drafts/run", lose_response)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        assert len(generator.requests) == len(guardian.requests) == 1
