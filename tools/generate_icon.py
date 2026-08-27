"""Generate the 512px mod icon from the approved supplied traffic-light artwork.

The source JPEG is kept byte-for-byte in ``tools/icon_sources``.  Its digest is
pinned here so rerunning this tool cannot silently build the icon from a
different image.

本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。
发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "icon_sources" / "traffic_light_icon.jpg"
OUTPUT = ROOT / "common" / "src" / "main" / "resources" / "icon.png"
SOURCE_SHA256 = "aba3b970630640d025137801f46b72777659314264f1aaff2f4fb74057e9393f"
OUTPUT_SIZE = (512, 512)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    actual_source_sha256 = sha256(SOURCE)
    if actual_source_sha256 != SOURCE_SHA256:
        raise RuntimeError(
            f"Unexpected icon source SHA-256: {actual_source_sha256}; "
            f"expected {SOURCE_SHA256}"
        )

    with Image.open(SOURCE) as source:
        if source.size != (1024, 1024):
            raise RuntimeError(f"Unexpected icon source size: {source.size}")
        icon = source.convert("RGB").resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)

    # Do not copy the JPEG's ICC profile or other metadata into the packaged PNG.
    icon.info.clear()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    icon.save(OUTPUT, format="PNG", optimize=False, compress_level=9)
    print(
        f"Generated {OUTPUT} ({icon.mode} {icon.width}x{icon.height}) "
        f"from {SOURCE} [{actual_source_sha256}]"
    )


if __name__ == "__main__":
    main()
