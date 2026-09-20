"""Required real Chromium smoke tests. Install requirements-browser.txt; no skips."""
import contextlib
import os
import shutil
import threading

import pytest
from playwright.sync_api import expect, sync_playwright

from agent_lab.designer import author_design, generate_candidate
from agent_lab.designer.server import create_server


@pytest.fixture
def page():
    executable = os.environ.get("CHROMIUM") or shutil.which("chromium") or shutil.which("chromium-browser")
    assert executable, "Install system Chromium or set CHROMIUM to its executable"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
                                             args=["--no-sandbox"])
        page = browser.new_page()
        yield page
        browser.close()


@contextlib.contextmanager
def app(tmp_path, **kwargs):
    server = create_server(tmp_path / "evidence", **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_browser_answers_graph_check_and_edit_invalidation(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        page.get_by_label("Threshold", exact=True).select_option("10")
        page.get_by_label("Below threshold", exact=True).select_option("ACCEPTED")
        page.get_by_label("At or above threshold", exact=True).select_option("REVIEW")
        button = page.get_by_role("button", name="Generate / check")
        expect(button).to_be_enabled()
        graph = page.get_by_role("img", name="Authored workflow nodes, routes and terminals")
        expect(graph).to_contain_text("ACCEPTED")
        expect(graph).to_contain_text("REVIEW")
        expect(graph).to_contain_text("FAILED_VALIDATION")
        expect(graph).to_contain_text("FAILED_BUDGET")
        expect(page.locator("#cases")).to_contain_text("score 9 → ACCEPTED")
        expect(page.locator("#cases")).to_contain_text("score 10 → REVIEW")
        expect(page.locator("#cases")).to_contain_text("score 11 → REVIEW")
        button.click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        expect(page.locator("#result")).to_contain_text("Reference:")
        expect(page.locator("#result")).to_contain_text("Candidate:")
        page.get_by_label("Threshold", exact=True).select_option("100")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#cases")).to_contain_text("score 100 → REVIEW")
        button.click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")


def wrong_candidate(design):
    # A real generated graph for a deliberately different authored spec.
    return generate_candidate(author_design({"threshold": 10, "below": "ACCEPTED", "at_or_above": "REVIEW"}))


def test_browser_surfaces_nonconforming_candidate(page, tmp_path):
    with app(tmp_path, candidate_factory=wrong_candidate) as url:
        page.goto(url)
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("FAIL — conformance not established")
        expect(page.locator("#result")).not_to_contain_text("PASS")
        expect(page.locator("#result li")).not_to_have_count(0)


def test_browser_generation_failure_is_visible(page, tmp_path):
    def broken(design):
        raise RuntimeError("deliberate generator failure")
    with app(tmp_path, candidate_factory=broken) as url:
        page.goto(url)
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("FAIL")
        expect(page.locator("#result")).to_contain_text("deliberate generator failure")
        expect(page.locator("#result")).not_to_contain_text("PASS")


def test_browser_evidence_write_failure_is_visible(page, tmp_path):
    # A real filesystem failure at the operator-selected root, not a mocked report.
    (tmp_path / "evidence").write_text("not a directory")
    with app(tmp_path) as url:
        page.goto(url)
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("FAIL — conformance not established")
        expect(page.locator("#result")).to_contain_text("incomplete")
        expect(page.locator("#result")).not_to_contain_text("PASS")


def test_late_check_response_cannot_restore_old_evidence(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()
        pending = []
        page.route("**/api/check", lambda route: pending.append(route))
        page.get_by_role("button", name="Generate / check").click()
        page.wait_for_timeout(100)
        assert pending
        page.get_by_label("Threshold", exact=True).select_option("100")
        expect(page.locator("#cases")).to_contain_text("score 100")
        # This is an actual check response, delayed at the HTTP boundary.
        pending[0].fulfill(response=pending[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#status")).to_contain_text("not checked")
