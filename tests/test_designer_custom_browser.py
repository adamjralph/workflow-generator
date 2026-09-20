"""Real Chromium: custom input runs stay separate and never go stale."""
import pytest
from playwright.sync_api import expect

from test_designer_custom import REQUEST, failing_candidate

from test_designer_browser import app, page  # noqa: F401
from test_designer_triage import EXPECTED


def open_triage(page, url):
    page.goto(url)
    page.get_by_label("Workflow mode").select_option("triage")
    expect(page.get_by_role("button", name="Run request", exact=True)).to_be_enabled()


def fill_request(page, row):
    for label, value in zip(("Request ID", "Request category", "Request urgency", "Short description"), row[:4]):
        control = page.get_by_label(label, exact=True)
        if label in ("Request category", "Request urgency"):
            control.select_option(value)
        else:
            control.fill(value)


def test_browser_custom_runs_show_input_route_and_outputs_without_replacing_check(page, tmp_path):
    with app(tmp_path) as url:
        open_triage(page, url)
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("PASS")
        checked = page.locator("#result").inner_text()
        for row in EXPECTED:
            fill_request(page, row)
            page.get_by_role("button", name="Run request", exact=True).click()
            result = page.locator("#run-result")
            expect(result).to_contain_text("Run completed")
            expect(result).to_contain_text(row[6])
            expect(result).to_contain_text(" → ".join([*row[7], "COMPLETED"]))
            expect(result).to_contain_text(f"Team: {row[4]}; priority: {row[5]}")
            expect(result).not_to_contain_text("PASS")
            assert page.locator("#result").inner_text() == checked


def test_browser_custom_text_is_inert_and_current_authored_operations_execute(page, tmp_path):
    with app(tmp_path) as url:
        open_triage(page, url)
        fill_request(page, list(REQUEST.values()))
        page.locator('[data-node="billing_team"]').get_by_label("Team", exact=True).select_option("technical")
        page.locator('[data-node="urgent_priority"]').get_by_label("Priority", exact=True).select_option("normal")
        page.get_by_role("button", name="Run request", exact=True).click()
        result = page.locator("#run-result")
        expect(result).to_contain_text("Run completed")
        expect(result).to_contain_text("Custom-1: technical team; normal priority. <img src=x onerror=alert(1)>")
        expect(result.locator("img,script")).to_have_count(0)
        expect(result).to_contain_text('"category": "billing"')
        page.get_by_label("Request ID", exact=True).fill("<script>alert(1)</script>")
        expect(result).to_be_empty()
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(result).to_contain_text("Run failed")
        expect(result.locator("script")).to_have_count(0)


@pytest.mark.parametrize("edit", ["Request ID", "Request category", "Request urgency", "Short description",
                                  "team", "entry", "remove", "mode"])
@pytest.mark.parametrize("response", ["success", "failure"])
def test_workflow_and_request_edits_discard_inflight_runs(page, tmp_path, edit, response):
    options = {} if response == "success" else {"candidate_factory": failing_candidate("generation")}
    with app(tmp_path, **options) as url:
        open_triage(page, url)
        fill_request(page, list(REQUEST.values()))
        held = []
        page.route("**/api/run", lambda route: held.append(route))
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-status")).to_have_text("Running offline…")
        page.wait_for_timeout(100)
        assert held
        if edit in ("Request ID", "Short description"):
            page.get_by_label(edit, exact=True).fill("Changed")
        elif edit in ("Request category", "Request urgency"):
            page.get_by_label(edit, exact=True).select_option("general" if edit == "Request category" else "normal")
        elif edit == "team":
            page.locator('[data-node="billing_team"]').get_by_label("Team", exact=True).select_option("technical")
        elif edit == "entry":
            page.get_by_label("Entry node", exact=True).select_option("summary")
        elif edit == "remove":
            page.get_by_role("button", name="Remove summary", exact=True).click()
        else:
            page.get_by_label("Workflow mode").select_option("score")
        held[0].fulfill(response=held[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#run-status")).to_contain_text("invalidated")
        if edit in ("entry", "remove"):
            expect(page.locator("#status")).to_contain_text("Design failed")
            expect(page.locator("#run")).to_be_disabled()
        elif edit == "mode":
            expect(page.locator("#custom")).to_be_hidden()
        else:
            expect(page.locator("#run")).to_be_enabled()


@pytest.mark.parametrize("failure", ["generation", "unsupported", "execution", "budget", "evidence"])
def test_browser_custom_failures_never_show_success(page, tmp_path, failure):
    with app(tmp_path, **({} if failure == "evidence" else
                          {"candidate_factory": failing_candidate(failure)})) as url:
        open_triage(page, url)
        fill_request(page, list(REQUEST.values()))
        if failure == "evidence":
            (tmp_path / "evidence").write_text("blocked")
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-result")).to_contain_text("Run failed")
        expect(page.locator("#run-result")).not_to_contain_text("Run completed")
        expect(page.locator("#result")).to_be_empty()
        if failure == "execution":
            expect(page.locator("#run-result")).to_contain_text("FAILED_VALIDATION")


def test_browser_accepts_the_same_unicode_description_bound_as_the_core(page, tmp_path):
    with app(tmp_path) as url:
        open_triage(page, url)
        fill_request(page, ["Unicode", "general", "normal", ""])
        page.get_by_label("Short description", exact=True).focus()
        page.keyboard.insert_text("😀" * 240)
        expect(page.get_by_label("Short description", exact=True)).to_have_value("😀" * 240)
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-result")).to_contain_text("Run completed")
        expect(page.locator("#run-result")).to_contain_text("😀" * 240)
        page.get_by_label("Short description", exact=True).fill("😀" * 241)
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-result")).to_contain_text("Run failed")


def test_invalid_input_and_design_do_not_run_and_completed_results_clear(page, tmp_path):
    with app(tmp_path) as url:
        open_triage(page, url)
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-result")).to_contain_text("Run failed")
        assert not (tmp_path / "evidence").exists()
        fill_request(page, list(REQUEST.values()))
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-result")).to_contain_text("Run completed")
        page.get_by_label("Short description", exact=True).fill("   ")
        expect(page.locator("#run-result")).to_be_empty()
        page.get_by_role("button", name="Run request", exact=True).click()
        expect(page.locator("#run-result")).to_contain_text("Run failed")
        page.get_by_role("button", name="Remove summary", exact=True).click()
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.locator("#run")).to_be_disabled()
