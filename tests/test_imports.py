import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _run(code, tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(APP_DIR)
    env["YT2RSS_CACHE_DIR"] = str(tmp_path / "c")
    env["YT2RSS_TMP_DIR"] = str(tmp_path / "t")
    env["YT2RSS_CACHE_MODE"] = "none"
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)


def test_api_can_be_imported_before_main(tmp_path):
    # Regression guard: the module graph must be acyclic, so importing the
    # routers before the app entrypoint must not raise.
    r = _run("import api; import main; assert main.app; print('ok')", tmp_path)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_main_can_be_imported_first(tmp_path):
    r = _run("import main; import api; assert main.app; print('ok')", tmp_path)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
