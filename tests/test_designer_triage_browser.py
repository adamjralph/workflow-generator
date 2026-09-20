"""Required real Chromium ticket-15 browser-to-core evidence."""
import pytest
from playwright.sync_api import expect

from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult

from test_designer_browser import app, page
from test_designer_triage import EXPECTED


def triage(page, url):
    page.goto(url)
    page.get_by_label("Workflow mode").select_option("triage")
    expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()


def test_browser_triage_displays_six_real_results_and_changed_behavior(page, tmp_path):
    with app(tmp_path) as url:
        triage(page, url)
        expect(page.locator("#nodes fieldset")).to_have_count(8)
        # Triage's larger graph stays readable rather than shrinking all text.
        assert page.locator("#graph svg").bounding_box()["width"] >= 2000
        expect(page.locator("#cases li")).to_have_count(6)
        expect(page.locator("#graph")).to_contain_text("Assign team: billing")
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        for expected in EXPECTED:
            row = page.locator(f'[data-case="{expected[0]}"]')
            expect(row).to_contain_text(expected[6])
            expect(row).to_contain_text(" → ".join(expected[7]) + " → COMPLETED")
            expect(page.locator("#cases")).to_contain_text(expected[3])
        page.locator('[data-node="billing_team"]').get_by_label("Team", exact=True).select_option("technical")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#graph")).to_contain_text("Assign team: technical")
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("B-N: technical team; normal priority. Invoice copy requested")
        expect(page.locator("#cases li")).to_have_count(6)
        expect(page.locator("#scope")).to_contain_text("not correctness or free-text coverage")


def node(page, identity):
    return page.locator(f'[data-node="{identity}"]')


@pytest.mark.parametrize("decision,labels", [("category", ["billing", "technical", "general"]), ("urgency", ["normal", "urgent"])])
def test_browser_add_remove_reconnect_and_bound_catalog(page, tmp_path, decision, labels):
    with app(tmp_path) as url:
        triage(page, url)
        page.get_by_role("button", name="Add handling summary", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.locator("#cases li")).to_have_count(6)
        for identity in ["normal_priority", "urgent_priority"]:
            node(page, identity).get_by_label("Done destination").select_option("summarize_1")
        page.get_by_role("button", name="Remove summary", exact=True).click()
        expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()
        page.get_by_role("button", name=f"Add {decision} Decision", exact=True).click()
        for label in labels:
            node(page, f"{decision}_2").get_by_label(f"{label} destination", exact=True).select_option("summarize_1")
        for identity in ["normal_priority", "urgent_priority"]:
            node(page, identity).get_by_label("Done destination").select_option(f"{decision}_2")
        expect(page.get_by_role("button", name="Add category Decision", exact=True)).to_be_disabled()
        expect(page.get_by_role("button", name="Add urgency Decision", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        expect(page.locator("#result")).to_contain_text(f"{decision}_2 → summarize_1 → COMPLETED")
        page.get_by_role("button", name=f"Remove {decision}_2", exact=True).click()
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#graph")).to_contain_text(f"Missing: {decision}_2")
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.locator("#cases li")).to_have_count(6)
        for identity in ["normal_priority", "urgent_priority"]:
            node(page, identity).get_by_label("Done destination").select_option("summarize_1")
        expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()
        # All trusted operation kinds can be added; the UI stops at twelve nodes.
        for name in ["Add team assignment", "Add priority assignment", "Add handling summary", "Add team assignment"]:
            page.get_by_role("button", name=name, exact=True).click()
        expect(page.locator("#nodes fieldset")).to_have_count(12)
        for name in ["Add team assignment", "Add priority assignment", "Add handling summary", "Add category Decision", "Add urgency Decision"]:
            expect(page.get_by_role("button", name=name, exact=True)).to_be_disabled()
        page.get_by_role("button", name="Remove assign_team_6", exact=True).click()
        expect(page.get_by_role("button", name="Add team assignment", exact=True)).to_be_enabled()


def test_triage_late_responses_cannot_restore_invalid_draft_or_previous_mode(page, tmp_path):
    with app(tmp_path) as url:
        triage(page, url)
        checks, designs = [], []
        page.route("**/api/check", lambda route: checks.append(route))
        page.get_by_role("button", name="Generate / check").click()
        page.wait_for_timeout(100)
        assert checks
        page.route("**/api/design", lambda route: designs.append(route))
        node(page, "billing_team").get_by_label("Team", exact=True).select_option("technical")
        page.wait_for_timeout(100)
        assert designs
        page.unroute("**/api/design")
        page.get_by_role("button", name="Remove summary", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Design failed")
        checks[0].fulfill(response=checks[0].fetch())
        designs[0].fulfill(response=designs[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#cases li")).to_have_count(6)
        expect(page.get_by_role("button", name="Generate / check")).to_be_disabled()
        page.get_by_label("Workflow mode").select_option("score")
        expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()
        expect(page.locator("#cases")).to_contain_text("score")
        expect(page.locator("#result")).to_be_empty()


@pytest.mark.parametrize("failure", ["altered", "generation", "execution", "checking", "evidence"])
def test_browser_triage_failures_cannot_show_pass(page, tmp_path, failure):
    def candidate(design):
        if failure == "generation":
            raise RuntimeError("generation unavailable")
        if failure == "checking":
            return object()
        bindings = dict(design.bindings)
        bindings["billing_team"] = (lambda state: 123) if failure == "execution" else (
            lambda state: TransformResult(state.model_copy(update={"team": "general"}), "done"))
        return generate_graph(design.spec, state_type=design.state_type, bindings=bindings).candidate
    with app(tmp_path, **({} if failure == "evidence" else {"candidate_factory": candidate})) as url:
        triage(page, url)
        if failure == "evidence":
            (tmp_path / "evidence").write_text("blocked")
        page.get_by_role("button", name="Generate / check").click()
        expect(page.locator("#result")).to_contain_text("FAIL")
        expect(page.locator("#result")).not_to_contain_text("PASS")
        expect(page.locator("#cases li")).to_have_count(6)
        if failure == "altered":
            expect(page.locator("#result")).to_contain_text("B-N: general team; normal priority. Invoice copy requested")
        if failure == "execution":
            expect(page.locator("#result")).to_contain_text("FAILED_VALIDATION")


def test_entry_and_mode_edits_invalidate_inflight_checks(page, tmp_path):
    with app(tmp_path) as url:
        triage(page, url)
        checks = []
        page.route("**/api/check", lambda route: checks.append(route))
        page.get_by_role("button", name="Generate / check").click()
        page.wait_for_timeout(100)
        assert checks
        page.get_by_label("Entry node", exact=True).select_option("billing_team")
        expect(page.locator("#status")).to_contain_text("Design failed")
        expect(page.locator("#cases li")).to_have_count(6)
        page.get_by_label("Workflow mode").select_option("score")
        expect(page.get_by_role("button", name="Generate / check")).to_be_enabled()
        checks[0].fulfill(response=checks[0].fetch())
        page.wait_for_timeout(100)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#cases")).to_contain_text("score")
