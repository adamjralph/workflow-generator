"""Controlled-source contract through real Chromium and the actual local server."""
import json

import pytest
from playwright.sync_api import expect
from test_designer_browser import app, page  # noqa: F401
from test_designer_roles_browser import open_roles

BRIEF = {"request_id": "browser-brief", "text": "A local brief", "evidence_labels": ["local-note"]}


def select_source(page, url):
    open_roles(page, url)
    page.locator("#role-input").select_option("source", timeout=2000)


def capture(page):
    page.locator("#capture").click()
    expect(page.locator("#source-status")).to_contain_text("Captured")
    expect(page.locator("#run")).to_be_enabled()


def test_preview_run_check_replay_and_explicit_recapture(page, tmp_path):
    source = tmp_path / "private.json"
    original = json.dumps(BRIEF).encode()
    source.write_bytes(original)
    source.chmod(0o444)
    with app(tmp_path, source_file=source) as url:
        select_source(page, url)
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#check")).to_be_disabled()
        capture(page)
        expect(page.locator("#source-preview")).to_contain_text("A local brief")
        expect(page.locator("body")).not_to_contain_text(str(source))
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text('"evidence_count": 1')
        expect(page.locator("#run-result")).to_contain_text("evidence_present")
        expect(page.locator("#run-result")).to_contain_text("Snapshot:")
        expect(page.locator("#result")).to_be_empty()
        assert source.read_bytes() == original
        assert source.stat().st_mode & 0o222 == 0
        source.unlink()
        source.write_text(json.dumps({**BRIEF, "evidence_labels": []}))
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS — captured input only")
        expect(page.locator("#result")).to_contain_text("captured_input")
        expect(page.locator("#result")).to_contain_text("evidence_present")
        expect(page.locator("#result")).not_to_contain_text("with_evidence")
        capture(page)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#run-result")).to_be_empty()
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("evidence_missing")
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("evidence_missing")


def test_unconfigured_source_is_visible_and_fixtures_still_work(page, tmp_path):
    with app(tmp_path) as url:
        select_source(page, url)
        expect(page.locator("#source-availability")).to_contain_text("Source not configured")
        expect(page.locator("#capture")).to_be_disabled()
        expect(page.locator("#run")).to_be_disabled()
        page.locator("#role-input").select_option("fixture")
        expect(page.locator("#check")).to_be_enabled()
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")


def test_recapture_clears_displayed_results_before_response(page, tmp_path):
    source = tmp_path / "brief.json"
    source.write_text(json.dumps(BRIEF))
    with app(tmp_path, source_file=source) as url:
        select_source(page, url)
        capture(page)
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("Run completed")
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS")
        held = []
        page.route("**/api/source/capture", lambda route: held.append(route))
        page.locator("#capture").click()
        expect(page.locator("#source-status")).to_have_text("Capturing…")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#check")).to_be_disabled()
        held[0].fulfill(response=held[0].fetch())
        expect(page.locator("#source-status")).to_contain_text("Captured")


@pytest.mark.parametrize("invalid", ['{', '{"request_id":"x","text":"ok","evidence_labels":[],"extra":1}'])
def test_invalid_recapture_clears_success_and_blocks_execution(page, tmp_path, invalid):
    source = tmp_path / "brief.json"
    source.write_text(json.dumps(BRIEF))
    with app(tmp_path, source_file=source) as url:
        select_source(page, url)
        capture(page)
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS")
        source.write_text(invalid)
        page.locator("#capture").click()
        expect(page.locator("#source-status")).to_contain_text("Capture failed")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#source-preview")).to_be_empty()
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#check")).to_be_disabled()


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_damaged_snapshot_never_reports_run_or_check_success(page, tmp_path, damage):
    source = tmp_path / "brief.json"
    source.write_text(json.dumps(BRIEF))
    with app(tmp_path, source_file=source) as url:
        select_source(page, url)
        capture(page)
        snapshot = next((tmp_path / "evidence" / "snapshots").glob("*.json"))
        if damage == "missing":
            snapshot.unlink()
        else:
            snapshot.write_text("{}")
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("Run failed")
        expect(page.locator("#run-result")).not_to_contain_text("Run completed")
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("FAIL")
        expect(page.locator("#result")).not_to_contain_text("PASS")


def test_source_text_is_inert_in_preview_run_and_conformance(page, tmp_path):
    source = tmp_path / "brief.json"
    payload = '<img src=x onerror="window.injected=1">'
    source.write_text(json.dumps({**BRIEF, "text": payload, "evidence_labels": [payload]}))
    with app(tmp_path, source_file=source) as url:
        select_source(page, url)
        capture(page)
        page.locator("#run").click()
        expect(page.locator("#run-result")).to_contain_text("Run completed")
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS")
        for area in ("source-preview", "run-result", "result"):
            expect(page.locator(f"#{area}")).to_contain_text("<img src=x")
            expect(page.locator(f"#{area} img")).to_have_count(0)
        assert page.evaluate("window.injected") is None


@pytest.mark.parametrize("endpoint", ["capture", "run", "check"])
@pytest.mark.parametrize("change", ["recapture", "design", "mode", "input"])
@pytest.mark.parametrize("failure", [False, True])
def test_late_source_responses_are_inert(page, tmp_path, endpoint, change, failure):
    source = tmp_path / "brief.json"
    source.write_text(json.dumps(BRIEF))
    with app(tmp_path, source_file=source) as url:
        select_source(page, url)
        capture(page)
        held = []
        pattern = f"**/api/source/{endpoint}"
        page.route(pattern, lambda route: route.continue_() if held else held.append(route))
        page.locator(f"#{endpoint}").click()
        page.wait_for_timeout(100)
        assert held
        # Obtain the actual old response now, before recapture changes the source.
        if failure:
            if endpoint == "capture":
                source.unlink()
            else:
                next((tmp_path / "evidence" / "snapshots").glob("*.json")).unlink()
        response = held[0].fetch()
        assert response.ok != failure
        if change == "recapture":
            source.write_text(json.dumps({**BRIEF, "text": "New captured text", "evidence_labels": []}))
            capture(page)
        elif change == "design":
            page.locator("#role-consumer").select_option("studio_producer")
            expect(page.locator("#status")).to_contain_text("Incompatible")
        elif change == "mode":
            page.locator("#mode").select_option("score")
            expect(page.locator("#status")).to_contain_text("Current design ready")
        else:
            page.locator("#role-input").select_option("fixture")
            expect(page.locator("#status")).to_contain_text("Current design ready")
        held[0].fulfill(response=response)
        page.wait_for_timeout(100)
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#run-result")).to_be_empty()
        expect(page.locator("#source-status")).not_to_contain_text("failed")
        expect(page.locator("#status")).not_to_contain_text("Check finished")
        expect(page.locator("#status")).not_to_contain_text("Check failed")
        if change == "recapture":
            expect(page.locator("#source-preview")).to_contain_text("New captured text")
        else:
            expect(page.locator("#source-preview")).to_be_empty()
