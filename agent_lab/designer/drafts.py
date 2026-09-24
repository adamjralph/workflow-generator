"""Bounded, read-only LinkedIn draft capture. No execution or model clients.

The operator JSON manifest is pinned at construction; capture rereads only the
pinned drafts, guidance and model selections. Evidence contains no profile YAML.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

import yaml

from agent_lab.designer import validate_evidence_root

_AUTHORITY = frozenset((
    "generator_soul guardian_soul generator_skill guardian_skill writing_skill "
    "voice_profile writing_craft brand_index offer audience product content_system "
    "guardian_checklist current_vs_superseded"
).split())
_VERSION = "linkedin-capture-v1"
_DRAFT_LIMIT = 64 * 1024
_GUIDANCE_LIMIT = 128 * 1024
_TOTAL_LIMIT = 512 * 1024
_BUNDLE_LIMIT = 4 * 1024 * 1024


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _read(path: Path, limit: int, *, private: bool = False) -> bytes:
    """Never follow the final symlink or block on a FIFO; bound actual reads."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            # Atomic publication temporarily gives the same private inode two
            # names. Ownership and permissions, not link count, define privacy.
            if private and (info.st_mode & 0o077 or info.st_uid != os.getuid()):
                raise ValueError("Capture bundle must be private and owned by this user")
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError("Expected a bounded regular file")
            data = handle.read(limit + 1)
            if len(data) > limit:
                raise ValueError("File exceeds capture limit")
            return data
    except OSError:
        raise ValueError("Cannot read a regular capture input") from None


def _text(path: Path, limit: int) -> str:
    try:
        return _read(path, limit).decode("utf-8")
    except UnicodeError:
        raise ValueError("Capture input must be UTF-8") from None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate configuration key")
        result[key] = value
    return result


class _StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        keys: set[str] = set()
        for key, _ in node.value:
            if not isinstance(key, yaml.ScalarNode) or key.tag != "tag:yaml.org,2002:str" or key.value in keys:
                raise ValueError("YAML keys must be unique strings")
            keys.add(key.value)
        return super().construct_mapping(node, deep=deep)


# YAML 1.1's yes/no and timestamps must not silently coerce required metadata.
_StrictLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in values
          if tag not in {"tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp"}]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_StrictLoader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(true|false)$"), list("tf"))


def _boolean(loader: _StrictLoader, node: yaml.ScalarNode) -> bool:
    value = loader.construct_scalar(node)
    if value not in ("true", "false"):
        raise ValueError("Explicit true or false boolean required")
    return value == "true"


_StrictLoader.add_constructor("tag:yaml.org,2002:bool", _boolean)


def _yaml(text: str) -> dict[str, Any]:
    try:
        for count, token in enumerate(yaml.scan(text)):
            if count > 16384 or isinstance(token, (yaml.AliasToken, yaml.AnchorToken)):
                raise ValueError("YAML aliases or excessive structure are not supported")
        value = yaml.load(text, Loader=_StrictLoader)
        if not isinstance(value, dict):
            raise ValueError("YAML mapping required")
        return value
    except (yaml.YAMLError, ValueError, TypeError, RecursionError):
        raise ValueError("Invalid or ambiguous YAML mapping") from None


def _metadata(text: str) -> dict[str, Any]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("Draft requires leading YAML frontmatter")
    end = next((i for i, line in enumerate(lines[1:], 1) if line.rstrip("\r\n") == "---"), None)
    if end is None:
        raise ValueError("Draft requires closed YAML frontmatter")
    meta = _yaml("".join(lines[1:end]))
    if type(meta.get("processed")) is not bool:
        raise ValueError("processed must be an explicit true or false boolean")
    if "published" in meta and type(meta["published"]) is not bool:
        raise ValueError("published must be an explicit true or false boolean")
    if "status" in meta and not isinstance(meta["status"], str):
        raise ValueError("status must be a string")
    if meta["processed"] is False:
        created = meta.get("date_created")
        if not isinstance(created, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", created):
            raise ValueError("date_created requires an ISO calendar date YYYY-MM-DD")
        try:
            date.fromisoformat(created)
        except ValueError:
            raise ValueError("date_created requires a valid ISO calendar date") from None
    return meta


def _identifier(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}", value) is None or "://" in value:
        raise ValueError("Model provider and default must be safe nonempty identifiers (max 256 characters)")
    return value


def _shape(value: Any, keys: str) -> None:
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ValueError("Invalid capture bundle structure")


def _bounded_string(value: Any, limit: int) -> None:
    try:
        if not isinstance(value, str) or not value or len(value.encode("utf-8")) > limit:
            raise ValueError("Invalid bounded bundle string")
    except UnicodeError:
        raise ValueError("Capture paths and text must be valid UTF-8") from None


def _verify_bundle(bundle: Any) -> None:
    """No original inputs consulted: validate the persisted contract itself."""
    pinned = "selection_mode" in bundle
    _shape(bundle, "bundle_version instruction_version max_model_calls selected entries guidance models provenance"
           + (" selection_mode" if pinned else ""))
    if pinned and bundle["selection_mode"] != "operator_pin":
        raise ValueError("Invalid capture selection mode")
    if (type(bundle["bundle_version"]) is not int or bundle["bundle_version"] != 1
            or bundle["instruction_version"] != _VERSION
            or type(bundle["max_model_calls"]) is not int or bundle["max_model_calls"] != 2):
        raise ValueError("Unsupported capture bundle version or budget")
    selected = bundle["selected"]
    _shape(selected, "name date_created text digest")
    _bounded_string(selected["name"], 255)
    if Path(selected["name"]).name != selected["name"] or not selected["name"].endswith(".md"):
        raise ValueError("Invalid captured draft name")
    _bounded_string(selected["text"], _DRAFT_LIMIT)
    metadata = _metadata(selected["text"])
    if (metadata["processed"] or metadata.get("published") is True
            or metadata.get("status") == "published" or selected["name"] == "public-copy-bank.md"
            or metadata["date_created"] != selected["date_created"]):
        raise ValueError("Captured draft is not eligible")
    if _digest(selected["text"].encode("utf-8")) != selected["digest"]:
        raise ValueError("Captured text digest mismatch")
    entries = bundle["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 256:
        raise ValueError("Invalid capture entries")
    names = []
    eligible = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid capture entry")
        _shape(entry, "name status reason" + (" date_created" if "date_created" in entry else ""))
        _bounded_string(entry["name"], 255)
        _bounded_string(entry["reason"], 256)
        names.append(entry["name"])
        if entry["status"] not in (("eligible", "excluded", "invalid") if pinned else ("eligible", "excluded")):
            raise ValueError("Invalid capture entry status")
        if entry["status"] == "eligible":
            created = entry.get("date_created")
            if not isinstance(created, str) or date.fromisoformat(created).isoformat() != created:
                raise ValueError("Invalid capture entry date")
            eligible.append((created, entry["name"]))
    selection = (selected["date_created"], selected["name"])
    if (names != sorted(set(names)) or not eligible or
            (selection not in eligible if pinned else min(eligible) != selection)):
        raise ValueError("Invalid captured selection ordering")
    guidance = bundle["guidance"]
    if not isinstance(guidance, list) or len(guidance) != len(_AUTHORITY):
        raise ValueError("Invalid captured guidance set")
    labels = []
    total = len(selected["text"].encode("utf-8"))
    for item in guidance:
        _shape(item, "name path digest text")
        _bounded_string(item["path"], 4096)
        if not isinstance(item["text"], str) or len(item["text"].encode("utf-8")) > _GUIDANCE_LIMIT:
            raise ValueError("Invalid captured guidance text")
        if _digest(item["text"].encode("utf-8")) != item["digest"]:
            raise ValueError("Guidance digest mismatch")
        labels.append(item["name"])
        total += len(item["text"].encode("utf-8"))
    if labels != sorted(_AUTHORITY) or total > _TOTAL_LIMIT:
        raise ValueError("Invalid captured guidance or total size")
    models = bundle["models"]
    if not isinstance(models, list) or len(models) != 2:
        raise ValueError("Invalid captured model selections")
    for role, model in zip(("generator", "guardian"), models):
        _shape(model, "role provider model")
        if model["role"] != role:
            raise ValueError("Invalid captured model role")
        _identifier(model["provider"])
        _identifier(model["model"])
    provenance = bundle["provenance"]
    _shape(provenance, "config drafts_dir profiles source_digests")
    for key in ("config", "drafts_dir"):
        _bounded_string(provenance[key], 4096)
    _shape(provenance["profiles"], "generator guardian")
    for path in provenance["profiles"].values():
        _bounded_string(path, 4096)
    digests = provenance["source_digests"]
    if not isinstance(digests, dict) or not 1 <= len(digests) <= 256:
        raise ValueError("Invalid captured source digests")
    for name, digest in digests.items():
        if name not in names or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid captured source digest")
    if digests.get(selected["name"]) != selected["digest"]:
        raise ValueError("Selected source provenance mismatch")


class DraftSource:
    """Trusted operator paths, never browser-supplied paths."""

    def __init__(self, config_file: Path, evidence_dir: Path,
                 protected_roots: tuple[Path, ...] = ()) -> None:
        self._config = Path(config_file).expanduser().resolve()
        self._protected = protected_roots
        self._root = validate_evidence_root(evidence_dir, protected_roots=protected_roots)
        try:
            config = json.loads(_text(self._config, _DRAFT_LIMIT), object_pairs_hook=_pairs)
        except (ValueError, RecursionError):
            raise ValueError("Invalid capture manifest") from None
        if not isinstance(config, dict) or set(config) not in (
                {"drafts_dir", "guidance", "profiles"},
                {"drafts_dir", "guidance", "profiles", "selected_draft"}):
            raise ValueError("Capture manifest requires drafts_dir, guidance and profiles")
        self._selected_draft = config.get("selected_draft")
        if "selected_draft" in config and (not isinstance(self._selected_draft, str)
                or not self._selected_draft.endswith(".md") or len(self._selected_draft.encode("utf-8")) > 255
                or self._selected_draft in (".", "..") or Path(self._selected_draft).name != self._selected_draft
                or self._selected_draft == "public-copy-bank.md"):
            raise ValueError("selected_draft must be one top-level draft filename")
        if not isinstance(config["guidance"], dict) or set(config["guidance"]) != _AUTHORITY:
            raise ValueError("Capture manifest requires the complete guidance authority set")
        if not isinstance(config["profiles"], dict) or set(config["profiles"]) != {"generator", "guardian"}:
            raise ValueError("Capture manifest requires generator and guardian profiles")

        def path(value: object) -> Path:
            if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
                raise ValueError("Manifest paths must be bounded nonempty strings")
            candidate = Path(value).expanduser()
            return (self._config.parent / candidate).absolute()

        self._drafts = path(config["drafts_dir"]).resolve()
        self._guidance = {label: path(value) for label, value in config["guidance"].items()}
        self._profiles = {role: path(value) for role, value in config["profiles"].items()}
        self._check_overlap()

    def _check_overlap(self) -> None:
        if validate_evidence_root(self._root, protected_roots=self._protected) != self._root:
            raise ValueError("Evidence root changed")
        if self._drafts.resolve() != self._drafts:
            raise ValueError("Pinned draft directory changed")
        inputs = [self._config, self._drafts, *self._guidance.values(), *self._profiles.values()]
        for path in inputs:
            self._input(path)

    def _input(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved.is_relative_to(self._root) or self._root.is_relative_to(resolved):
            raise ValueError("Capture inputs and evidence must be disjoint")
        return resolved

    def _directory(self) -> Path:
        if validate_evidence_root(self._root, protected_roots=self._protected) != self._root:
            raise ValueError("Evidence root changed")
        directory = self._root / "draft-snapshots"
        if directory.resolve() != directory:
            raise ValueError("Snapshot directory must not be a symlink")
        if directory.exists():
            info = directory.stat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise ValueError("Snapshot directory must be private and owned by this user")
        return directory

    def load(self, snapshot: str) -> dict[str, Any]:
        """Verify immutable evidence without reading the original capture inputs."""
        if not isinstance(snapshot, str) or re.fullmatch(r"[0-9a-f]{64}", snapshot) is None:
            raise ValueError("Invalid snapshot digest")
        path = self._directory() / f"{snapshot}.json"
        data = _read(path, _BUNDLE_LIMIT, private=True)
        if _digest(data) != snapshot:
            raise ValueError("Corrupt capture bundle: digest mismatch")
        try:
            bundle = json.loads(data, object_pairs_hook=_pairs)
            _verify_bundle(bundle)
            if _canonical(bundle) != data:
                raise ValueError("Noncanonical capture bundle")
        except (ValueError, TypeError, KeyError, RecursionError):
            raise ValueError("Invalid capture bundle") from None
        return {"succeeded": True, "snapshot": snapshot,
                **{key: bundle[key] for key in ("selected", "entries", "guidance", "models",
                                                "max_model_calls", "instruction_version")},
                **({"selection_mode": bundle["selection_mode"]} if "selection_mode" in bundle else {}),
                "evidence": [str(path)]}

    def capture(self) -> dict[str, Any]:
        """Capture oldest or explicitly pinned eligible draft; never modify inputs."""
        self._check_overlap()
        entries: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        findings: list[dict[str, str]] = []
        total = 0
        source_digests: dict[str, str] = {}
        paths = []
        with os.scandir(self._drafts) as iterator:
            for entry in iterator:
                paths.append(self._drafts / entry.name)
                if len(paths) > 256:
                    raise ValueError("Draft directory exceeds 256 entries")
        for path in sorted(paths):
            reason = ("public_copy_bank" if path.name == "public-copy-bank.md" else
                      "not_markdown" if path.suffix != ".md" else
                      "directory" if stat.S_ISDIR(path.lstat().st_mode) else None)
            if reason:
                entries.append({"name": path.name, "status": "excluded", "reason": reason})
                continue
            try:
                text = _text(path, _DRAFT_LIMIT)
                total += len(text.encode("utf-8"))
                if total > _TOTAL_LIMIT:
                    raise ValueError("Total captured text exceeds 512 KiB")
                source_digests[path.name] = _digest(text.encode("utf-8"))
                meta = _metadata(text)
            except ValueError as exc:
                if total > _TOTAL_LIMIT:
                    raise ValueError("Total captured text exceeds 512 KiB") from None
                entries.append({"name": path.name, "status": "invalid", "reason": str(exc)})
                if self._selected_draft is None or path.name == self._selected_draft:
                    findings.append({"code": "invalid_draft", "path": path.name, "message": str(exc)})
                continue
            if meta["processed"] or meta.get("published") is True or meta.get("status") == "published":
                entries.append({"name": path.name, "status": "excluded", "reason":
                                "processed" if meta["processed"] else "published"})
                continue
            created = str(meta["date_created"])
            entries.append({"name": path.name, "status": "eligible", "reason": "unprocessed",
                            "date_created": created})
            candidates.append({"name": path.name, "date_created": created, "text": text,
                               "digest": _digest(text.encode("utf-8"))})
        pinned = self._selected_draft is not None
        chosen = next((item for item in candidates if item["name"] == self._selected_draft), None) if pinned else None
        if findings or (chosen is None if pinned else not candidates):
            return {"succeeded": False, "snapshot": None, "selected": None, "entries": entries,
                    "findings": findings or [{"code": "no_eligible_draft", "path": "selected_draft" if pinned else "drafts_dir",
                                               "message": "Selected draft is not eligible" if pinned else "No eligible draft found"}],
                    "guidance": [], "models": [], "max_model_calls": 2}
        selected = chosen if chosen is not None else min(candidates, key=lambda item: (item["date_created"], item["name"]))
        guidance = []
        for label, path in sorted(self._guidance.items()):
            resolved = self._input(path)
            text = _text(resolved, _GUIDANCE_LIMIT)
            total += len(text.encode("utf-8"))
            if total > _TOTAL_LIMIT:
                raise ValueError("Total captured text exceeds 512 KiB")
            guidance.append({"name": label, "path": str(resolved), "text": text,
                             "digest": _digest(text.encode("utf-8"))})
        models = []
        profile_paths = {}
        for role, path in sorted(self._profiles.items()):
            resolved = self._input(path)
            profile_paths[role] = str(resolved)
            profile = _yaml(_text(resolved, _GUIDANCE_LIMIT))
            selection = profile.get("model")
            if not isinstance(selection, dict):
                raise ValueError("Profile requires a model mapping")
            models.append({"role": role, "provider": _identifier(selection.get("provider")),
                           "model": _identifier(selection.get("default"))})
        bundle = {"instruction_version": _VERSION, "bundle_version": 1,
                  "selected": selected, "entries": entries, "guidance": guidance,
                  "models": models, "max_model_calls": 2,
                  "provenance": {"config": str(self._config), "drafts_dir": str(self._drafts),
                                  "source_digests": source_digests,
                                  "profiles": profile_paths}}
        if pinned:
            bundle["selection_mode"] = "operator_pin"
        # A successful capture must always satisfy the public load contract,
        # including inventory names and provenance, before publishing anything.
        _verify_bundle(bundle)
        data = _canonical(bundle)
        snapshot = _digest(data)
        self._check_overlap()
        directory = self._directory()
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.mkdir(exist_ok=True, mode=0o700)
        self._directory()
        path = directory / f"{snapshot}.json"
        fd, temporary = tempfile.mkstemp(dir=directory, prefix=".capture-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if _read(path, _BUNDLE_LIMIT, private=True) != data:
                    raise ValueError("Corrupt existing capture bundle") from None
        finally:
            os.unlink(temporary)
        return {"succeeded": True, "snapshot": snapshot, "selected": selected,
                "entries": entries, "guidance": guidance, "models": models,
                "max_model_calls": 2, "instruction_version": _VERSION,
                **({"selection_mode": "operator_pin"} if pinned else {}), "evidence": [str(path)]}
