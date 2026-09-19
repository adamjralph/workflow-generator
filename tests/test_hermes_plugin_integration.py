"""Optional check against a real Hermes loader, never the operator's live home.

HERMES_PLUGIN_TEST_SOURCE and HERMES_PLUGIN_TEST_PYTHON opt in. The loader's
isolated registration path (also used by Hermes Plugin Doctor) is deliberately
not a claim that the normal config activation gate was bypassed.
"""
import os
import subprocess
from pathlib import Path

import pytest

from test_diagnosis import make_hermes
from test_read_only_boundary import protect_fixture, tree_digest


@pytest.mark.skipif(not os.environ.get("HERMES_PLUGIN_TEST_SOURCE") or
                    not os.environ.get("HERMES_PLUGIN_TEST_PYTHON"),
                    reason="optional real Hermes plugin loader check")
def test_real_hermes_loader_registers_and_invokes_without_config_edits(tmp_path):
    home = make_hermes(tmp_path)
    protect_fixture(home)
    host_home = tmp_path / "loader-home"
    plugin = host_home / "plugins/workflow-diagnosis"
    plugin.parent.mkdir(parents=True)
    plugin.symlink_to(Path(__file__).resolve().parents[1] / "plugins/workflow-diagnosis",
                      target_is_directory=True)
    before = tree_digest(home)
    user = tmp_path / "user"
    user.mkdir()
    bundled = tmp_path / "empty-bundled"
    bundled.mkdir()
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(user), "HERMES_HOME": str(host_home),
        "HERMES_BUNDLED_PLUGINS": str(bundled), "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.environ["HERMES_PLUGIN_TEST_SOURCE"],
    }
    result = subprocess.run(
        [os.environ["HERMES_PLUGIN_TEST_PYTHON"], "-B", "-c", """
import shlex
import sys
from pathlib import Path
from hermes_cli.plugins import PluginManager
from hermes_cli.plugins_discovery import gate_manifest
from hermes_cli.config import ensure_hermes_home
home, store, host_home = map(Path, sys.argv[1:])
# Hermes initializes its own isolated home, including its default SOUL. Snapshot
# after host startup, before plugin registration; diagnosis targets another home.
ensure_hermes_home()
def host_bytes():
    return {str(p.relative_to(host_home)): p.read_bytes()
            for p in host_home.rglob('*') if p.is_file()}
before = host_bytes()
manager = PluginManager()
manifest, = manager._scan_directory(host_home / 'plugins', source='user')
# Explicitly verify the real activation restriction, rather than hiding it.
assert gate_manifest(manifest, set(), set()).action == 'placeholder'
manager._load_plugin(manifest)  # isolated registration, like Hermes Plugin Doctor
loaded = manager._plugins['workflow-diagnosis']
assert loaded.enabled and loaded.error is None, loaded.error
handler = manager._plugin_commands['workflow-diagnose']['handler']
output = handler(shlex.join([str(home), 'stillroom-research', '2', str(store)]))
assert 'Calls/run: 10' in output, output
after = host_bytes()
assert after == before, [key for key in before.keys() | after.keys() if before.get(key) != after.get(key)]
print(output)
""", str(home), str(tmp_path / "artifacts"), str(host_home)],
        env=env, cwd=tmp_path, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Calls/run: 10" in result.stdout
    assert tree_digest(home) == before
