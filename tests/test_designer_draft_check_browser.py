"""Real Chromium and HTTP: Check is separate from editorial review and Run."""
import json

import pytest
from playwright.sync_api import expect

from test_designer_browser import app, page  # noqa: F401
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_drafts_browser import capture_draft, open_drafts
from tests.test_designer_review_server import FixtureSource, GuardianSource


@pytest.mark.parametrize("verdict", ["Approved", "Changes requested", "Blocked"])
def test_browser_completed_pair_check_is_offline_fresh_and_separate_from_verdict(page, tmp_path, operator, verdict):
    config, folder, _ = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource(verdict)
    with app(tmp_path, draft_config=config, draft_model_source=generator, guardian_model_source=guardian) as url:
        open_drafts(page, url)
        capture_draft(page)
        expect(page.locator("#draft-check")).to_be_disabled()
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        original_review = page.locator("#draft-run-result").text_content()
        page.locator("#draft-check").click()
        expect(page.locator("#draft-check-status")).to_contain_text("Passed")
        result = page.locator("#draft-check-result")
        for value in ("Case-scoped", "not a new editorial review", "publication permission", "Historical usage",
                      '"input_tokens": 17', '"input_tokens": 31', "Model calls: 0", "authentication requests: 0",
                      "Snapshot:", "Run request:", "Receipt digest:", "reference", "candidate"):
            expect(result).to_contain_text(value)
        first = result.text_content()
        page.locator("#draft-check").click()
        expect(page.locator("#draft-check-status")).to_contain_text("Passed")
        assert result.text_content() != first
        assert page.locator("#draft-run-result").text_content() == original_review
        assert len(generator.requests) == len(guardian.requests) == 1
        assert result.locator("script,img").count() == 0
        assert page.evaluate("window.injected") is None


def test_browser_corrupt_recording_fails_without_erasing_editorial_result(page, tmp_path, operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    with app(tmp_path, draft_config=config, draft_model_source=FixtureSource(), guardian_model_source=GuardianSource()) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        original = page.locator("#draft-run-result").text_content()
        receipt = next(evidence.glob("draft-runs/*/receipt.json"))
        receipt.write_text("corrupt")
        page.locator("#draft-check").click()
        expect(page.locator("#draft-check-status")).to_contain_text("Failed")
        expect(page.locator("#draft-check-result")).to_contain_text("invalid_recording")
        assert page.locator("#draft-run-result").text_content() == original


@pytest.mark.parametrize("change", ["recapture", "mode", "new_request"])
@pytest.mark.parametrize("response_kind", ["success", "error"])
def test_late_check_cannot_restore_invalidated_result(page, tmp_path, operator, change, response_kind):
    config, folder, _ = operator
    draft(folder, "old.md")
    with app(tmp_path, draft_config=config, draft_model_source=FixtureSource(), guardian_model_source=GuardianSource()) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        held = []
        page.route("**/api/drafts/check", lambda route: held.append((route, route.fetch())))
        page.locator("#draft-check").click()
        for _ in range(50):
            if held:
                break
            page.wait_for_timeout(20)
        assert held
        if change == "recapture":
            capture_draft(page)
        elif change == "mode":
            page.locator("#mode").select_option("score")
        else:
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#draft-new-request").click()
            expect(page.locator("#draft-run-status")).to_contain_text("New request ready")
        route, response = held[0]
        if response_kind == "error":
            route.abort("failed")
        else:
            route.fulfill(response=response)
        page.wait_for_timeout(100)
        expect(page.locator("#draft-check-result")).to_be_empty()
        expect(page.locator("#draft-check")).to_be_disabled()


def test_check_failure_text_is_inert_and_lost_response_can_be_checked_again(page, tmp_path, operator):
    config, folder, _ = operator
    draft(folder, "old.md")
    with app(tmp_path, draft_config=config, draft_model_source=FixtureSource(), guardian_model_source=GuardianSource()) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-run").click()
        expect(page.locator("#draft-run-status")).to_contain_text("Completed")
        page.route("**/api/drafts/check", lambda route: route.abort("failed"))
        page.locator("#draft-check").click()
        expect(page.locator("#draft-check-status")).to_contain_text("Failed")
        page.unroute("**/api/drafts/check")
        payload = '<img src=x onerror="window.injected=true">'
        def inert_error(route):
            response = route.fetch()
            body = response.json()
            body["passed"] = False
            body["findings"] = [{"code": "fixture", "path": ["fixture"], "message": payload}]
            route.fulfill(response=response, body=json.dumps(body))
        page.route("**/api/drafts/check", inert_error)
        page.locator("#draft-check").click()
        expect(page.locator("#draft-check-status")).to_contain_text("Failed")
        expect(page.locator("#draft-check-result")).to_contain_text(payload)
        assert page.locator("#draft-check-result img").count() == 0
        assert page.evaluate("window.injected") is None
