"""Build the Windows executable and a GitHub Releases ZIP."""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
VERSION = "1.0.0"


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def copy_dependency_licenses(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "unknown").replace("/", "-").replace("\\", "-")
        for entry in dist.files or ():
            leaf = Path(str(entry)).name.lower()
            if not leaf.startswith(("license", "copying", "notice")):
                continue
            source = Path(dist.locate_file(entry))
            if source.is_file():
                target = destination / name / Path(str(entry)).name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(source, target)


def main() -> None:
    run("-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "auto-clicker", "--icon", str(ROOT / "assets" / "auto_clicker.ico"),
        str(ROOT / "auto_clicker_interactive.py"))
    stage = DIST / "auto-clicker"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, stage / name)
    copy_dependency_licenses(stage / "THIRD_PARTY_LICENSES")
    shutil.copy2(DIST / "auto-clicker.exe", stage / "auto-clicker.exe")
    archive = DIST / f"auto-clicker-v{VERSION}-windows-x64.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in sorted(stage.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(stage.parent))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"Release: {archive}")
    print(f"SHA-256: {checksum}")


if __name__ == "__main__":
    main()
