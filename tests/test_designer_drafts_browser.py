"""Capture-only behavior through Chromium and the actual loopback server."""
import json
import pytest

from playwright.sync_api import expect
from test_designer_browser import app, page  # noqa: F401
from tests.test_designer_drafts import draft, operator  # noqa: F401


def open_drafts(page, url):
    page.goto(url)
    page.locator("#mode").select_option("drafts", timeout=2000)


def capture_draft(page):
    page.locator("#draft-capture-button").click()
    expect(page.locator("#draft-status")).to_contain_text("Captured input")


def test_capture_previews_exact_input_guidance_models_and_no_execution(page, tmp_path, operator):
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    original = selected.read_bytes()
    draft(folder, "new.md", "processed: false\ndate_created: 2026-02-01")
    (folder / "public-copy-bank.md").write_text("Reference without frontmatter")
    with app(tmp_path, draft_config=config) as url:
        open_drafts(page, url)
        expect(page.locator("#draft-availability")).to_contain_text("available")
        assert not evidence.exists()
        capture_draft(page)
        expect(page.locator("#draft-preview")).to_contain_text("old.md")
        expect(page.locator("#draft-preview")).to_contain_text("2026-01-01")
        expect(page.locator("#draft-preview")).to_contain_text("Synthetic body.")
        expect(page.locator("#draft-preview")).to_contain_text("generator-model")
        expect(page.locator("#draft-preview")).to_contain_text("guardian-model")
        expect(page.locator("#draft-preview")).to_contain_text("Synthetic generator_soul")
        expect(page.locator("#draft-preview")).to_contain_text("public-copy-bank.md")
        expect(page.locator("#draft-policy")).to_contain_text("at most two generation attempts")
        expect(page.locator("#draft-policy")).to_contain_text("one Generator and one independent Guardian review")
        expect(page.locator("#draft-policy")).to_contain_text("Capture makes no model calls")
        expect(page.locator("#draft-run")).to_be_enabled()
        expect(page.locator("#draft-run-status")).to_contain_text("Not run")
        assert not list(tmp_path.rglob("claimed.json"))
        expect(page.locator("#run")).not_to_be_visible()
        expect(page.locator("#check")).not_to_be_visible()
        expect(page.locator("body")).not_to_contain_text("TOP_SECRET")
        assert selected.read_bytes() == original
        bundle = next((evidence / "draft-snapshots").glob("*.json"))
        assert bundle.is_file()


def test_operator_pinned_capture_is_labelled_and_does_not_hide_invalid_inventory(page, tmp_path, operator):
    config, folder, evidence = operator
    draft(folder, "older.md", "processed: false\ndate_created: 2026-09-08")
    draft(folder, "chosen.md", "processed: false\ndate_created: 2026-09-23")
    (folder / "review.md").write_text("# Not a draft")
    manifest = json.loads(config.read_text())
    manifest["selected_draft"] = "chosen.md"
    config.write_text(json.dumps(manifest))
    with app(tmp_path, draft_config=config) as url:
        open_drafts(page, url)
        capture_draft(page)
        expect(page.locator("#draft-preview")).to_contain_text("chosen.md · 2026-09-23")
        expect(page.locator("#draft-preview")).to_contain_text("Operator-selected, not oldest")
        expect(page.locator("#draft-preview")).to_contain_text("review.md: invalid")
        expect(page.locator("#draft-run")).to_be_enabled()
        assert list((evidence / "draft-snapshots").glob("*.json"))
        assert not list(tmp_path.rglob("claimed.json"))


def test_source_and_profile_edits_require_explicit_recapture(page, tmp_path, operator):
    config, folder, evidence = operator
    source = draft(folder, "only.md")
    with app(tmp_path, draft_config=config) as url:
        open_drafts(page, url)
        capture_draft(page)
        old_snapshot = next((evidence / "draft-snapshots").glob("*.json"))
        original_bundle = old_snapshot.read_bytes()
        source.write_text(source.read_text().replace("Synthetic body.", "Changed source."))
        (config.parent / "generator.yaml").write_text("model:\n  provider: changed\n  default: new-model\n")
        expect(page.locator("#draft-preview")).to_contain_text("Synthetic body.")
        expect(page.locator("#draft-preview")).not_to_contain_text("new-model")
        capture_draft(page)
        expect(page.locator("#draft-preview")).to_contain_text("Changed source.")
        expect(page.locator("#draft-preview")).to_contain_text("changed / new-model")
        assert len(list((evidence / "draft-snapshots").glob("*.json"))) == 2
        assert old_snapshot.read_bytes() == original_bundle


@pytest.mark.parametrize("problem", ["invalid", "empty", "missing", "guidance"])
def test_failed_recapture_clears_old_preview(page, tmp_path, operator, problem):
    config, folder, evidence = operator
    source = draft(folder, "only.md")
    with app(tmp_path, draft_config=config) as url:
        open_drafts(page, url)
        capture_draft(page)
        if problem == "invalid":
            source.write_text("---\nprocessed: false\n---\nMissing date")
        elif problem == "guidance":
            (config.parent / "generator_soul.md").unlink()
        else:
            source.unlink()
            if problem == "missing":
                folder.rmdir()
        page.locator("#draft-capture-button").click()
        expect(page.locator("#draft-status")).to_contain_text(
            "Capture blocked" if problem in ("invalid", "empty") else "Capture failed")
        expect(page.locator("#draft-preview")).not_to_contain_text("Snapshot:")
        expect(page.locator("#draft-preview")).not_to_contain_text("Synthetic body.")
        if problem == "invalid":
            expect(page.locator("#draft-preview")).to_contain_text("only.md: invalid")
            expect(page.locator("#draft-preview")).to_contain_text("date_created")
        assert len(list((evidence / "draft-snapshots").glob("*.json"))) == 1


def test_unconfigured_capture_and_existing_offline_modes(page, tmp_path):
    with app(tmp_path) as url:
        open_drafts(page, url)
        expect(page.locator("#draft-availability")).to_contain_text("not configured")
        expect(page.locator("#draft-capture-button")).to_be_disabled()
        expect(page.locator("#run")).to_be_disabled()
        expect(page.locator("#check")).to_be_disabled()
        page.locator("#mode").select_option("roles")
        expect(page.locator("#check")).to_be_enabled()
        page.locator("#check").click()
        expect(page.locator("#result")).to_contain_text("PASS — listed cases only")
        page.locator("#mode").select_option("drafts")
        expect(page.locator("#result")).to_be_empty()
        expect(page.locator("#draft-preview")).to_be_empty()


@pytest.mark.parametrize("response_kind", ["success", "blocked", "failure"])
@pytest.mark.parametrize("change", ["recapture", "mode"])
def test_late_draft_responses_cannot_restore_stale_state(page, tmp_path, operator, response_kind, change):
    config, folder, evidence = operator
    source = draft(folder, "only.md")
    with app(tmp_path, draft_config=config) as url:
        open_drafts(page, url)
        capture_draft(page)
        held = []
        page.route("**/api/drafts/capture", lambda route: route.continue_() if held else held.append(route))
        if response_kind == "blocked":
            source.write_text("---\nprocessed: false\n---\n")
        elif response_kind == "failure":
            source.unlink()
            folder.rmdir()
        page.locator("#draft-capture-button").click()
        expect(page.locator("#draft-status")).to_have_text("Capturing…")
        expect(page.locator("#draft-preview")).to_be_empty()
        assert held
        response = held[0].fetch()
        assert response.ok == (response_kind != "failure")
        folder.mkdir(exist_ok=True)
        source = draft(folder, "only.md")
        source.write_text(source.read_text().replace("Synthetic body.", "New captured text"))
        if change == "recapture":
            capture_draft(page)
        else:
            page.locator("#mode").select_option("roles")
            expect(page.locator("#status")).to_contain_text("Current design ready")
        held[0].fulfill(response=response)
        page.wait_for_timeout(100)
        expect(page.locator("#draft-status")).not_to_contain_text("failed")
        expect(page.locator("#draft-status")).not_to_contain_text("blocked")
        if change == "recapture":
            expect(page.locator("#draft-preview")).to_contain_text("New captured text")
            expect(page.locator("#draft-preview")).not_to_contain_text("Synthetic body.")
        else:
            expect(page.locator("#draft-preview")).to_be_empty()
            page.locator("#mode").select_option("drafts")
            expect(page.locator("#draft-status")).to_contain_text("No captured input")


def test_source_names_text_and_authority_render_as_inert_text(page, tmp_path, operator):
    config, folder, evidence = operator
    payload = '<img src=x onerror="window.injected=1">'
    source = draft(folder, payload + ".md")
    source.write_text(source.read_text() + payload)
    (config.parent / "generator_soul.md").write_text(payload)
    with app(tmp_path, draft_config=config) as url:
        open_drafts(page, url)
        capture_draft(page)
        page.locator("#draft-preview summary").filter(has_text="generator_soul").click()
        expect(page.locator("#draft-preview")).to_contain_text(payload)
        expect(page.locator("#draft-preview img")).to_have_count(0)
        assert page.evaluate("window.injected") is None
