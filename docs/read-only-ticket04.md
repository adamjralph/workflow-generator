# Ticket 04 — read-only boundary and local plugin

User authorized ticket 04, the diagnosis/adapter/plugin seams, and review baseline
`c3260ab95ecb80d37e0fd7546b288ea07dd6da52`. No tickets 05–06 are included.

## Acceptance

**Accepted and closed** at Adam's explicit approval. Installation without
protected edits satisfies the plugin criterion. Activation remains a separate,
explicit Hermes config opt-in; acceptance authorizes neither config changes nor
bypassing the host activation gate. The verification and review below record the
original implementation evidence.

## Read-only measurement

A regression reproduced a write from the ticket-03 reader: connecting with
SQLite `mode=ro` to a database with a committed WAL and no shared-memory file
creates `state.db-shm` in Hermes. `query_only` does not prevent that.

The fresh-process adapter now copies the DB and, when present, WAL using ordinary
read-only file access. SQLite opens **only the temporary copy**, still with
`mode=ro` and `query_only`. It creates any shared-memory bookkeeping outside
Hermes. The temporary directory is removed on success and failure. It contains
potentially sensitive database contents, has private permissions, and is not a
persisted artifact. Process termination can strand a temporary directory; this
is not secure deletion or crash-durable cleanup.

Before/after device, inode, size, mtime and ctime checks reject copies observed
changing. Three failed attempts produce an explicit retry error, never a zero
measurement. Nonempty rollback journals are conservatively refused: let Hermes
recover/checkpoint its own database, then retry. We do not recover live databases.

This is an observation of each database, not a cross-database transaction or a
snapshot of the eventual completed run. Metadata checks assume an ordinary local
filesystem and cooperative SQLite writers, not adversarial timestamp manipulation
or concurrently malicious symlink replacement. Copying large databases increases
I/O; the existing 30-second reader timeout can fail explicitly on large/busy homes.
Do **not** use `immutable=1` against a live database: it can ignore committed WAL data.

Snapshots use `TMPDIR`, then `TEMP`, then `TMP`, otherwise `/tmp` (local POSIX
integration). An unsafe/nonexistent/unwritable location fails rather than silently
falling back. The path is checked **before** allocation; `tempfile.gettempdir()`
was itself reproduced writing a probe into a protected directory and is not used.
Default/configured/selected Hermes homes, source roots and the source DB directory
are protected. Adapter subprocesses disable Python bytecode writes.

`DiagnosisStore` now also protects this tool's source checkout. For a separately
installed Hermes source tree, the terminal accepts repeatable
`--protected-root /path/to/hermes-agent`. Pass those same roots to adapters and
the store when using the Python API. No heuristic can discover every arbitrary
source checkout: callers must name additional protected roots. The plugin derives
the running Hermes installation from its already-loaded `hermes_cli` module.

## Local plugin installation (not a distribution decision)

`plugins/workflow-diagnosis/` is a native Hermes directory plugin: `plugin.yaml`
plus `register(ctx)`. It registers a slash command and runs the existing terminal
front door through this checkout's `.venv/bin/python`. It contains no duplicate
measurement implementation, model calls, dependency installer or config writer.

After the README's local environment setup, **manually** install by symlink:

```bash
mkdir -p "$HERMES_HOME/plugins"
ln -s /absolute/path/to/workflow-generator/plugins/workflow-diagnosis \
  "$HERMES_HOME/plugins/workflow-diagnosis"
```

Set `HERMES_HOME` explicitly first. Do not overwrite an existing plugin. The
symlink is important: this is a local-checkout integration, not a relocatable
copied bundle. No installation was made into the operator's live Hermes home.
Packaging, distribution and community support remain undecided.

When already enabled by the host, the command is:

```text
/workflow-diagnose /path/to/hermes-home stillroom-research 2 "/path/to/project/artifacts"
```

**Activation constraint — accepted installation/activation distinction:** the inspected Hermes
revision `5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04` requires new standalone plugins
in `plugins.enabled`. Its project-plugin environment switch only enables
*discovery*, not activation. Installation does not edit config, but normal
activation of a newly installed plugin cannot currently be promised without
changing config. We did not enable it, invent an environment override, mislabel it
as an auto-loaded backend, or bypass this gate in production. Adam accepted this
distinction and closed the ticket; config-free normal activation is not claimed.
The standalone terminal remains usable without this gate.

## Proof and verification

- `tests/test_read_only_boundary.py` digests all entries in a fresh fixture Hermes
  home, including source/config/auth/profile sentinels and board/profile SQLite
  files. Diagnosis succeeds without pre-existing tool state. A committed WAL
  changes the expected calls from 10 to **13**, proving WAL data is not ignored.
- An active SQLite writer connection remains open during adapter checks. A child
  process audit guard denies protected write opens/mutations and **all** SQLite
  connections into Hermes (including read-only ones). Both read operations work;
  an unknown write operation is refused. Negative controls prove the guard
  actually denies file writes and live SQLite access. This is a regression guard,
  not a production OS sandbox.
- Missing/unstable/journal-bearing sources fail without creating live database
  files or leaving temporary copies. Separate source-root and unsafe temporary
  directory guards are covered. Ticket-03 tests continue to exercise store escapes.
- The offline plugin seam test installs a symlink in a fixture home, registers
  through a stand-in for the external Hermes SDK, invokes the real diagnosis,
  and checks protected bytes before/after installation and invocation.
- `tests/test_hermes_plugin_integration.py` optionally uses the **real Hermes
  loader** to discover, register and invoke the plugin. Like Hermes Plugin Doctor,
  it uses isolated registration machinery, **not normal config-gated activation**.
  It asserts the activation gate refuses an unenabled plugin. Hermes initializes
  a separate temporary host home before the registration snapshot; the diagnosed
  home is distinct and remains byte-identical. The production home is never used.

Reproduce:

```bash
.venv/bin/python -m pytest -q tests/test_read_only_boundary.py tests/test_diagnosis.py
.venv/bin/python -m mypy agent_lab
HERMES_PLUGIN_TEST_SOURCE=/path/to/hermes-agent \
HERMES_PLUGIN_TEST_PYTHON=/path/to/hermes-agent/venv/bin/python \
  .venv/bin/python -m pytest -q tests/test_hermes_plugin_integration.py
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

Targeted boundary tests: **10 passed**; existing diagnosis tests: **20 passed**;
real-loader check: **1 passed** on the revision above. Mypy retains the same
**11 inherited errors in 3 files**; the diagnosis code adds none. The plugin
source also passes mypy when checked as a script (the discovery directory has a
hyphen, not a Python package name).

The final full suite, with `AGENT_LAB_JUDGMENT=stub` and the real-loader opt-in
variables above, reports **106 passed, 2 optional live-Jev skips**. Without the
Hermes opt-in, the real-loader check is also skipped. Typechecking was repeated
throughout and at the end with the same inherited errors, unsuppressed.

## Standards

Independent parallel review of `git diff c3260ab...HEAD` at `6271106` found
**no documented-standard violations**. Failure-path inspection found no live
SQLite connections or protected-tree writes. Timeout/termination leftovers and
the activation limitation are disclosed, not bypassed.

One **nonblocking judgment call — possible Duplicated Code**: `_read_db` and
`DiagnosisStore.__init__` each assemble the default/configured/caller-supplied
protected roots. A future common root-policy helper could prevent drift while
retaining snapshot-specific roots and separate admission checks. Retained for
this bounded ticket; this is not an ADR-0002 violation.

## Spec

Independent parallel review found **one acknowledged partial requirement**:
“The tool is installable as a Hermes plugin without editing Hermes source,
configuration, or authentication,” alongside the parent spec's “plug-and-play.”
The native directory plugin is compatible with the real loader and its registered
command works, but normal activation still requires the host config opt-in. The
test explicitly demonstrates this gate and uses isolated registration, not
config-free normal activation. The criterion was open at review time; Adam has
since accepted installation separately from activation, resolving acceptance
without changing the implementation or claiming config-free activation.

No scope creep or additional incorrect implementation was identified. Reviewers
used only repository code/fixtures, not live Hermes state.

**Review summary:** Standards: 0 violations, 1 nonblocking duplication heuristic;
Spec: 1 partial activation requirement, no additional defects.
