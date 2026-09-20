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
        expect(page.locator("#cases")).to_contain_text("score 9")
        expect(page.locator("#cases")).to_contain_text("score 10")
        expect(page.locator("#cases")).to_contain_text("score 11")
        button.click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        expect(page.locator("#result")).to_contain_text("Reference:")
        expect(page.locator("#result")).to_contain_text("Candidate:")
        page.get_by_label("Threshold", exact=True).select_option("100")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#cases")).to_contain_text("score 100")
        button.click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")


def wrong_candidate(design):
    # A real generated graph for a deliberately different authored spec.
    return generate_candidate(author_design({"nodes": [
        {"id": "receive", "operation": "receive", "done": "threshold"},
        {"id": "threshold", "operation": "compare", "threshold": 10,
         "below": "ACCEPTED", "at_or_above": "REVIEW"},
    ]}))


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


def node(page, identity):
    return page.locator(f'fieldset[data-node="{identity}"]')


def check_pass(page):
    page.get_by_role("button", name="Generate / check").click()
    expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
    expect(page.locator("#result")).to_contain_text("Reference:")
    expect(page.locator("#result")).to_contain_text("Candidate:")


def test_compose_linear_and_repair_deleted_destination(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        page.get_by_role("button", name="Remove threshold", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.get_by_role("button", name="Generate / check")).to_be_disabled()
        expect(node(page, "receive").get_by_label("Done destination")).to_have_value("threshold")
        expect(node(page, "receive")).to_contain_text("Missing destination: threshold")
        page.get_by_role("button", name="Add adjustment", exact=True).click()
        node(page, "receive").get_by_label("Done destination").select_option("adjust_1")
        node(page, "adjust_1").get_by_label("Score adjustment").select_option("-10")
        expect(page.locator("#graph rect.node")).to_have_count(2)
        expect(page.locator("#budget")).to_contain_text("Step budget: 2")
        check_pass(page)
        page.get_by_role("button", name="Remove adjust_1", exact=True).click()
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(node(page, "receive").get_by_label("Done destination")).to_have_value("adjust_1")
        node(page, "receive").get_by_label("Done destination").select_option("REVIEW")
        expect(page.locator("#graph rect.node")).to_have_count(1)
        expect(page.locator("#budget")).to_contain_text("Step budget: 1")
        check_pass(page)


def test_compose_operations_before_and_after_decision(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        page.get_by_role("button", name="Add adjustment", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Design failed")  # unreachable until connected
        node(page, "receive").get_by_label("Done destination").select_option("adjust_1")
        node(page, "adjust_1").get_by_label("Done destination").select_option("threshold")
        page.get_by_role("button", name="Add adjustment", exact=True).click()
        node(page, "threshold").get_by_label("At or above threshold").select_option("adjust_2")
        node(page, "adjust_2").get_by_label("Score adjustment").select_option("-10")
        node(page, "adjust_2").get_by_label("Done destination").select_option("REVIEW")
        expect(page.locator("#graph rect.node")).to_have_count(4)
        expect(page.locator("#graph path.route")).to_have_count(5)
        expect(page.locator("#budget")).to_contain_text("Step budget: 4")
        expect(page.locator("#cases")).to_contain_text("score 40")  # equality after +10
        expect(page.locator("#scope")).not_to_be_empty()
        check_pass(page)


def test_late_check_and_design_responses_cannot_restore_invalid_deleted_draft(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()
        pending_checks, pending_designs = [], []
        page.route("**/api/check", lambda route: pending_checks.append(route))
        page.get_by_role("button", name="Generate / check").click()
        page.wait_for_timeout(100)
        assert pending_checks
        page.route("**/api/design", lambda route: pending_designs.append(route))
        node(page, "threshold").get_by_label("Threshold", exact=True).select_option("100")
        page.wait_for_timeout(100)
        assert pending_designs
        page.unroute("**/api/design")
        page.get_by_role("button", name="Remove threshold", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Design failed")
        pending_checks[0].fulfill(response=pending_checks[0].fetch())
        pending_designs[0].fulfill(response=pending_designs[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#cases")).to_be_empty()
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.get_by_role("button", name="Generate / check")).to_be_disabled()
        expect(node(page, "receive").get_by_label("Done destination")).to_have_value("threshold")
        node(page, "receive").get_by_label("Done destination").select_option("ACCEPTED")
        page.unroute("**/api/check")
        check_pass(page)


def test_second_decision_infeasible_scope_cycle_and_catalog_bounds(page, tmp_path):
    with app(tmp_path) as url:
        page.goto(url)
        page.get_by_role("button", name="Add Decision", exact=True).click()
        expect(page.get_by_role("button", name="Add Decision", exact=True)).to_be_disabled()
        node(page, "threshold").get_by_label("Below threshold").select_option("compare_1")
        node(page, "compare_1").get_by_label("Threshold", exact=True).select_option("100")
        expect(page.locator("#infeasible li")).not_to_have_count(0)
        expect(page.locator("#budget")).to_contain_text("Step budget: 3")
        check_pass(page)
        node(page, "compare_1").get_by_label("Below threshold").select_option("receive")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.get_by_role("button", name="Generate / check")).to_be_disabled()
        node(page, "compare_1").get_by_label("Below threshold").select_option("ACCEPTED")
        check_pass(page)
        for _ in range(3):
            page.get_by_role("button", name="Add adjustment", exact=True).click()
        expect(page.locator("#nodes fieldset")).to_have_count(6)
        expect(page.get_by_role("button", name="Add adjustment", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Remove adjust_2", exact=True).click()
        expect(page.get_by_role("button", name="Add adjustment", exact=True)).to_be_enabled()
        page.get_by_role("button", name="Add adjustment", exact=True).click()
        expect(node(page, "adjust_5")).to_be_visible()  # identities are never recycled
        expect(node(page, "adjust_3")).to_be_visible()
