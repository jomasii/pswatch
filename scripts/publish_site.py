"""Copia a página estática para a pasta da branch `data` (servida pelo GitHub Pages)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ASSETS = ("index.html", "app.js")


def publish_site(site_dir: Path, data_dir: Path) -> None:
    for name in ASSETS:
        shutil.copyfile(Path(site_dir) / name, Path(data_dir) / name)


if __name__ == "__main__":
    publish_site(Path(sys.argv[1]), Path(sys.argv[2]))
