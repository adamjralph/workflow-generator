"""Capture-only contract at the temporary operator configuration seam."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from agent_lab.designer.drafts import DraftSource

LABELS = (
    "generator_soul guardian_soul generator_skill guardian_skill writing_skill "
    "voice_profile writing_craft brand_index offer audience product content_system "
    "guardian_checklist current_vs_superseded"
).split()


@pytest.fixture
def operator(tmp_path: Path) -> tuple[Path, Path, Path]:
    folder = tmp_path / "operator"
    folder.mkdir()
    drafts = folder / "content-drafts"
    drafts.mkdir()
    guidance = {}
    for label in LABELS:
        path = folder / f"{label}.md"
        path.write_bytes(f"Synthetic {label}\r\n".encode())
        guidance[label] = path.name
    profiles = {}
    for role in ("generator", "guardian"):
        path = folder / f"{role}.yaml"
        path.write_text(f"model:\n  provider: synthetic\n  default: {role}-model\nauth: TOP_SECRET\n")
        profiles[role] = path.name
    config = folder / "capture.json"
    config.write_text(json.dumps({"drafts_dir": "content-drafts", "guidance": guidance,
                                  "profiles": profiles}))
    return config, drafts, tmp_path / "evidence"


def draft(folder: Path, name: str, metadata: str = "processed: false\ndate_created: 2026-01-01") -> Path:
    path = folder / name
    path.write_bytes(f"---\r\n{metadata.replace(chr(10), chr(13) + chr(10))}\r\n---\r\nSynthetic body.\r\n".encode())
    return path


def test_oldest_eligible_capture_preserves_exact_text_and_omits_secrets(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "new.md", "processed: false\ndate_created: 2026-02-01")
    selected = draft(folder, "old.md")
    source = DraftSource(config, evidence)
    result = source.capture()
    assert result["succeeded"] is True
    assert result["selected"]["name"] == "old.md"
    assert result["selected"]["text"].encode() == selected.read_bytes()
    assert result["models"] == [
        {"role": "generator", "provider": "synthetic", "model": "generator-model"},
        {"role": "guardian", "provider": "synthetic", "model": "guardian-model"},
    ]
    assert len(result["guidance"]) == 14
    assert result["max_model_calls"] == 2
    assert result["instruction_version"] == "linkedin-capture-v1"
    assert b"TOP_SECRET" not in Path(result["evidence"][0]).read_bytes()
    assert source.capture() == result


def test_folder_eligibility_exclusions_and_exact_filename_tie(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "z.md")
    draft(folder, "A.md")
    draft(folder, "a.md")
    draft(folder, "done.md", "processed: true")
    draft(folder, "live.md", "processed: false\npublished: true\ndate_created: 2020-01-01")
    draft(folder, "status.md", "processed: false\nstatus: published\ndate_created: 2020-01-01")
    (folder / "public-copy-bank.md").write_text("No frontmatter")
    (folder / "notes.txt").write_text("not a draft")
    for name in ("inbox", "published"):
        (folder / name).mkdir()
        draft(folder / name, "ignored.md", "broken: [")
    result = DraftSource(config, evidence).capture()
    assert result["succeeded"] is True
    assert result["selected"]["name"] == "A.md"
    entries = {entry["name"]: entry for entry in result["entries"]}
    assert all(entries[name]["status"] == "excluded" for name in (
        "done.md", "live.md", "status.md", "public-copy-bank.md", "notes.txt", "inbox", "published"))
    assert "ignored.md" not in entries


@pytest.mark.parametrize("metadata", [
    "date_created: 2026-01-01", 'processed: "false"\ndate_created: 2026-01-01',
    "processed: no\ndate_created: 2026-01-01", "processed: 0\ndate_created: 2026-01-01",
    "processed: false", "processed: false\ndate-created: 2026-01-01",
    "processed: false\ndate_created: 2026-02-30", "processed: false\ndate_created: 20260101",
    "processed: false\ndate_created: 2026-01-01T00:00:00Z",
    "processed: true\nprocessed: false\ndate_created: 2026-01-01",
    "processed: false\ndate_created: 2026-01-01\nnested: {x: 1, x: 2}",
    "processed: [SECRET_YAML", "!!python/object:SECRET {}", "- processed: false",
    "processed: false\ndate_created: 2026-01-01\npublished: 'false'",
    "processed: false\ndate_created: 2026-01-01\nstatus: [published]",
])
def test_invalid_potential_draft_blocks_selection_visibly(operator: tuple[Path, Path, Path], metadata: str) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    draft(folder, "invalid.md", metadata)
    result = DraftSource(config, evidence).capture()
    assert result["succeeded"] is False
    assert result["selected"] is None and result["snapshot"] is None
    assert result["guidance"] == result["models"] == []
    assert result["findings"][0]["path"] == "invalid.md"
    assert result["findings"][0]["code"] == "invalid_draft"
    assert "SECRET" not in json.dumps(result)
    assert not evidence.exists()


@pytest.mark.parametrize("kind", ["symlink", "broken_symlink", "fifo", "utf8", "no_frontmatter", "unclosed"])
def test_unsafe_potential_drafts_fail_without_following_or_blocking(operator: tuple[Path, Path, Path], kind: str) -> None:
    config, folder, evidence = operator
    good = draft(folder, "valid.md")
    bad = folder / "unsafe.md"
    if kind == "symlink":
        bad.symlink_to(good)
    elif kind == "broken_symlink":
        bad.symlink_to(folder / "missing")
    elif kind == "fifo":
        os.mkfifo(bad)
    else:
        bad.write_bytes({"utf8": b"\xff", "no_frontmatter": b"text", "unclosed": b"---\nprocessed: false"}[kind])
    result = DraftSource(config, evidence).capture()
    assert result["succeeded"] is False
    assert any(f["path"] == "unsafe.md" for f in result["findings"])
    assert not evidence.exists()


@pytest.mark.parametrize("kind", ["entries", "draft", "guidance", "total"])
def test_capture_limits_fail_closed(operator: tuple[Path, Path, Path], kind: str) -> None:
    config, folder, evidence = operator
    chosen = draft(folder, "valid.md")
    if kind == "entries":
        for i in range(256):
            (folder / f"{i}.txt").touch()
    elif kind == "draft":
        chosen.write_bytes(chosen.read_bytes() + b"x" * (64 * 1024))
    elif kind == "guidance":
        (config.parent / "offer.md").write_bytes(b"x" * (128 * 1024 + 1))
    else:
        for label in LABELS[:4]:
            (config.parent / f"{label}.md").write_bytes(b"x" * (128 * 1024))
    try:
        result = DraftSource(config, evidence).capture()
    except ValueError:
        pass
    else:
        assert result["succeeded"] is False
    assert not evidence.exists()


@pytest.mark.parametrize("yaml_text", [
    "model: {provider: synthetic}", "model: {provider: synthetic, default: ''}",
    "model: {provider: synthetic, default: 123}", "model: {provider: true, default: model}",
    "model: {provider: synthetic, default: 'https://SECRET@host/model'}",
    "model: {provider: synthetic, default: model, default: other}",
    "model: {provider: synthetic, default: model}\nauth: [SECRET",
    "model: {provider: synthetic, default: '" + "x" * 257 + "'}",
])
def test_profile_selection_errors_are_sanitized(operator: tuple[Path, Path, Path], yaml_text: str) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    (config.parent / "generator.yaml").write_text(yaml_text)
    with pytest.raises(ValueError) as caught:
        DraftSource(config, evidence).capture()
    assert "SECRET" not in str(caught.value)
    assert not evidence.exists()


def test_load_is_immutable_and_does_not_need_original_inputs(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    chosen = draft(folder, "valid.md")
    source = DraftSource(config, evidence)
    captured = source.capture()
    chosen.unlink()
    for path in config.parent.glob("*.md"):
        path.unlink()
    for path in config.parent.glob("*.yaml"):
        path.unlink()
    config.unlink()
    assert source.load(captured["snapshot"]) == captured
    bundle = Path(captured["evidence"][0])
    assert bundle.stat().st_mode & 0o777 == 0o600
    assert bundle.parent.stat().st_mode & 0o777 == 0o700
    bundle.write_bytes(bundle.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest"):
        source.load(captured["snapshot"])


@pytest.mark.parametrize("change", ["version", "budget", "unknown", "text_digest", "guidance", "model", "entries", "size"])
def test_load_rejects_invalid_digest_bound_bundles(operator: tuple[Path, Path, Path], change: str) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    source = DraftSource(config, evidence)
    captured = source.capture()
    path = Path(captured["evidence"][0])
    bundle = json.loads(path.read_bytes())
    if change == "version":
        bundle["instruction_version"] = "future"
    elif change == "budget":
        bundle["max_model_calls"] = 200
    elif change == "unknown":
        bundle["credentials"] = "SECRET"
    elif change == "text_digest":
        bundle["selected"]["text"] = "different"
    elif change == "guidance":
        bundle["guidance"].pop()
    elif change == "model":
        bundle["models"][0]["provider"] = ""
    elif change == "entries":
        bundle["entries"] *= 257
    else:
        bundle["selected"]["text"] = "x" * (64 * 1024 + 1)
    data = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    snapshot = hashlib.sha256(data).hexdigest()
    forged = path.parent / f"{snapshot}.json"
    forged.write_bytes(data)
    forged.chmod(0o600)
    with pytest.raises(ValueError):
        source.load(snapshot)


@pytest.mark.parametrize("destination", ["drafts", "config", "guidance", "profile", "ancestor", "protected"])
def test_source_and_protected_destinations_are_rejected(operator: tuple[Path, Path, Path], destination: str) -> None:
    config, folder, evidence = operator
    locations = {"drafts": folder / "output", "config": config, "guidance": config.parent / "offer.md",
                 "profile": config.parent / "generator.yaml", "ancestor": config.parent,
                 "protected": evidence / "protected"}
    with pytest.raises(ValueError):
        DraftSource(config, locations[destination], protected_roots=(evidence,))
    assert not evidence.exists()


def test_guidance_symlinks_bind_resolved_provenance_and_recheck_overlap(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    link = config.parent / "writing_skill.md"
    link.unlink()
    target = config.parent / "installed-skill.md"
    target.write_bytes(b"Synthetic installed skill\r\n")
    link.symlink_to(target)
    source = DraftSource(config, evidence)
    captured = source.capture()
    skill = next(g for g in captured["guidance"] if g["name"] == "writing_skill")
    assert skill["path"] == str(target.resolve())
    assert skill["text"] == "Synthetic installed skill\r\n"
    link.unlink()
    link.symlink_to(Path(captured["evidence"][0]))
    with pytest.raises(ValueError, match="disjoint"):
        source.capture()
    assert source.load(captured["snapshot"]) == captured


def test_replaced_draft_directory_is_not_followed(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    source = DraftSource(config, evidence)
    moved = folder.with_name("moved")
    folder.rename(moved)
    folder.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError):
        source.capture()
    assert not evidence.exists()


@pytest.mark.parametrize("change", ["draft", "guidance", "model", "other_draft"])
def test_recapture_binds_changed_inputs_without_mutating_old_capture(operator: tuple[Path, Path, Path], change: str) -> None:
    config, folder, evidence = operator
    selected = draft(folder, "valid.md")
    later = draft(folder, "later.md", "processed: false\ndate_created: 2026-02-01")
    source = DraftSource(config, evidence)
    original = source.capture()
    if change == "model":
        (config.parent / "generator.yaml").write_text("model: {provider: synthetic, default: other}")
    else:
        path = {"draft": selected, "guidance": config.parent / "offer.md", "other_draft": later}[change]
        path.write_bytes(path.read_bytes() + b" changed")
    updated = source.capture()
    assert updated["snapshot"] != original["snapshot"]
    assert source.load(original["snapshot"]) == original


def test_manifest_is_pinned_and_credentials_do_not_affect_capture(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    source = DraftSource(config, evidence)
    original = source.capture()
    config.write_text("not a manifest anymore")
    profile = config.parent / "generator.yaml"
    profile.write_text(profile.read_text().replace("TOP_SECRET", "DIFFERENT_SECRET"))
    assert source.capture() == original


def test_capture_preserves_readonly_source_bytes_modes_and_mtimes(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    paths = [p for p in config.parent.rglob("*") if p.is_file()]
    for path in paths:
        path.chmod(0o400)
    before = {p: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in paths}
    assert DraftSource(config, evidence).capture()["succeeded"] is True
    assert before == {p: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in paths}


def test_corrupt_existing_bundle_is_never_overwritten(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    source = DraftSource(config, evidence)
    original = source.capture()
    path = Path(original["evidence"][0])
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Corrupt"):
        source.capture()
    assert path.read_bytes() == b"corrupt"
    assert list(path.parent.glob(".capture-*")) == []


def test_existing_public_snapshot_directory_is_rejected(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    directory = evidence / "draft-snapshots"
    directory.mkdir(parents=True)
    directory.chmod(0o755)
    with pytest.raises(ValueError, match="private"):
        DraftSource(config, evidence).capture()
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize("kind", ["unknown", "duplicate", "missing_guidance", "missing_profile", "bad_path"])
def test_manifest_requires_strict_complete_authority(operator: tuple[Path, Path, Path], kind: str) -> None:
    config, _, evidence = operator
    manifest = json.loads(config.read_text())
    if kind == "unknown":
        manifest["secret"] = "SECRET"
    elif kind == "missing_guidance":
        del manifest["guidance"]["offer"]
    elif kind == "missing_profile":
        del manifest["profiles"]["guardian"]
    elif kind == "bad_path":
        manifest["drafts_dir"] = 42
    config.write_text(json.dumps(manifest))
    if kind == "duplicate":
        config.write_text(config.read_text().replace('{', '{"drafts_dir":"SECRET",', 1))
    with pytest.raises(ValueError) as caught:
        DraftSource(config, evidence)
    assert "SECRET" not in str(caught.value)
    assert not evidence.exists()


@pytest.mark.parametrize("operation", ["load", "capture"])
def test_public_bundle_permissions_fail_closed(operator: tuple[Path, Path, Path], operation: str) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md")
    source = DraftSource(config, evidence)
    captured = source.capture()
    Path(captured["evidence"][0]).chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        if operation == "load":
            source.load(captured["snapshot"])
        else:
            source.capture()


def test_explicit_yaml_bool_tag_cannot_coerce_no(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    draft(folder, "valid.md", "processed: !!bool no\ndate_created: 2026-01-01")
    assert DraftSource(config, evidence).capture()["succeeded"] is False


def test_exact_approved_size_and_entry_limits_are_accepted(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    selected = draft(folder, "valid.md")
    selected.write_bytes(selected.read_bytes().ljust(64 * 1024, b"x"))
    for i in range(255):
        (folder / f"{i}.txt").touch()
    for label in LABELS:
        (config.parent / f"{label}.md").write_bytes(b"")
    for label in LABELS[:3]:
        (config.parent / f"{label}.md").write_bytes(b"x" * (128 * 1024))
    (config.parent / f"{LABELS[3]}.md").write_bytes(b"x" * (64 * 1024))
    source = DraftSource(config, evidence)
    result = source.capture()
    assert result["succeeded"] is True
    assert len(result["entries"]) == 256
    assert source.load(result["snapshot"]) == result


@pytest.mark.parametrize("snapshot", ["", "../escape", "A" * 64, "a" * 63])
def test_load_rejects_non_digest_identifiers(operator: tuple[Path, Path, Path], snapshot: str) -> None:
    config, _, evidence = operator
    with pytest.raises(ValueError, match="digest"):
        DraftSource(config, evidence).load(snapshot)
    assert not evidence.exists()


def test_total_draft_text_limit_is_a_bounded_capture_error(operator: tuple[Path, Path, Path]) -> None:
    config, folder, evidence = operator
    for index in range(9):
        path = draft(folder, f"{index}.md")
        path.write_bytes(path.read_bytes().ljust(64 * 1024, b"x"))
    with pytest.raises(ValueError, match="Total captured text"):
        DraftSource(config, evidence).capture()
    assert not evidence.exists()


def test_empty_source_is_not_success(operator: tuple[Path, Path, Path]) -> None:
    config, _, evidence = operator
    result = DraftSource(config, evidence).capture()
    assert result["succeeded"] is False
    assert result["findings"][0]["code"] == "no_eligible_draft"
    assert not evidence.exists()
