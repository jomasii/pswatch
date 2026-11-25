import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from publish_site import publish_site  # noqa: E402


def test_publish_site_copies_assets_and_keeps_history(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "history.json").write_text('{"keep": true}', encoding="utf-8")

    publish_site(ROOT / "site", data_dir)

    assert (data_dir / "index.html").exists()
    assert (data_dir / "app.js").exists()
    assert (data_dir / "history.json").read_text(encoding="utf-8") == '{"keep": true}'
