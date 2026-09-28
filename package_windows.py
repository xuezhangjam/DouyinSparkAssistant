"""Create a portable ZIP; only the build output is included, never user data."""
import hashlib
from pathlib import Path
import shutil
import zipfile

from windows_core import VERSION

root = Path(__file__).resolve().parent
bundle = root / "dist" / "SparkAssistant-Windows-x64"
archive = root / "dist" / f"SparkAssistant-{VERSION}-Windows-x64.zip"
if not (bundle / "SparkAssistant.exe").is_file():
    raise SystemExit("Build SparkAssistant.spec first")
shutil.copytree(root / "licenses", bundle / "licenses", dirs_exist_ok=True)
shutil.copy2(root / "THIRD_PARTY_NOTICES.md", bundle / "THIRD_PARTY_NOTICES.md")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            output.write(path, path.relative_to(bundle.parent))
with archive.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
print(f"{archive.name}: {archive.stat().st_size / 1024 / 1024:.1f} MiB")
print(f"SHA256: {digest}")
