"""Verify final 1.21.1 JARs against the single shared content directory.

Art/funding: Crzay津仔. Technical implementation: QiZhang. MIT License.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from collections import Counter
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
REPOSITORY = PORT.parents[1]
SHARED = REPOSITORY / "common/src/main/resources"
MOD = "jinzai_traffic_lights"


def adapted_path(relative: str) -> str:
    parts = relative.split("/")
    if parts[0] != "data" or len(parts) < 3:
        return relative
    singular = {"advancements": "advancement", "functions": "function",
                "item_modifiers": "item_modifier", "loot_tables": "loot_table",
                "predicates": "predicate", "recipes": "recipe", "structures": "structure"}
    tag_names = {"blocks": "block", "items": "item", "fluids": "fluid",
                 "entity_types": "entity_type", "game_events": "game_event", "functions": "function"}
    if parts[2] in singular:
        parts[2] = singular[parts[2]]
    elif parts[2] == "tags" and len(parts) > 3 and parts[3] in tag_names:
        parts[3] = tag_names[parts[3]]
    return "/".join(parts)


def verify(path: Path) -> dict:
    shared_files = [p for p in SHARED.rglob("*") if p.is_file()]
    with zipfile.ZipFile(path) as jar:
        assert jar.testzip() is None, "Corrupt archive"
        names = jar.namelist()
        assert len(names) == len(set(names)), "Duplicate archive paths"
        entries = set(names)
        for source in shared_files:
            relative = source.relative_to(SHARED).as_posix()
            expected = adapted_path(relative)
            assert expected in entries, f"Missing shared resource: {expected}"
            if relative != "pack.mcmeta":
                assert jar.read(expected) == source.read_bytes(), f"Shared content differs: {expected}"
            if expected != relative:
                assert relative not in entries, f"Legacy data path retained: {relative}"
        pack = json.loads(jar.read("pack.mcmeta"))["pack"]
        assert pack["pack_format"] == 34
        assert pack["supported_formats"] == {"min_inclusive": 34, "max_inclusive": 48}
        assert jar.read("LICENSE") == (REPOSITORY / "LICENSE").read_bytes()
        assert jar.read("COPYRIGHT.txt") == (REPOSITORY / "COPYRIGHT.txt").read_bytes()
        catalog = json.loads(jar.read(f"assets/{MOD}/block_catalog.json"))["blocks"]
        assert len(catalog) == 334
        assert Counter(entry["category"] for entry in catalog) == {
            "frame": 89, "indicator": 108, "pole": 117, "annex": 20,
        }
        identifiers = {entry["id"] for entry in catalog}
        assert len(identifiers) == len(catalog)
        assert {entry["category"] for entry in catalog} == {"frame", "indicator", "pole", "annex"}
        for identifier in identifiers:
            for folder, extension in (("models/block", "json"), ("models/item", "json"),
                                      ("blockstates", "json"), ("textures/block", "png")):
                assert f"assets/{MOD}/{folder}/{identifier}.{extension}" in entries
            assert f"data/{MOD}/loot_table/blocks/{identifier}.json" in entries
        languages = [n for n in names if n.startswith(f"assets/{MOD}/lang/") and n.endswith(".json")]
        assert len(languages) == 13
        for name in languages:
            values = json.loads(jar.read(name))
            assert len(values) == len(catalog) + 4
            assert all(not key.startswith("tooltip.") for key in values)
        classes = [n for n in names if n.startswith("cn/crazyjinzai/trafficlights/") and n.endswith(".class")]
        assert classes
        for name in classes:
            data = jar.read(name)
            assert data[:4] == b"\xca\xfe\xba\xbe" and struct.unpack(">H", data[6:8])[0] == 65
            assert b"tooltip." not in data
        if "fabric.mod.json" in entries:
            loader = "Fabric"
            metadata = json.loads(jar.read("fabric.mod.json"))
            assert metadata["version"] == "2.1.50" and metadata["license"] == "MIT"
            assert metadata["depends"]["minecraft"] == "1.21.1"
            assert metadata["depends"]["java"] == ">=21"
            assert metadata["depends"]["architectury"] == ">=13.0.8 <14.0.0"
            assert "META-INF/neoforge.mods.toml" not in entries
        else:
            loader = "NeoForge"
            import tomllib
            metadata = tomllib.loads(jar.read("META-INF/neoforge.mods.toml").decode("utf-8"))
            assert metadata["license"] == "MIT" and metadata["mods"][0]["version"] == "2.1.50"
            dependencies = {d["modId"]: d for d in metadata["dependencies"][MOD]}
            assert dependencies["minecraft"]["versionRange"] == "[1.21.1,1.21.2)"
            assert dependencies["neoforge"]["versionRange"] == "[21.1.248,21.2)"
            assert metadata["features"][MOD]["javaVersion"] == "[21,)"
            assert "META-INF/mods.toml" not in entries
        animations = [n for n in entries if n.startswith(f"assets/{MOD}/textures/") and n.endswith(".png.mcmeta")]
        assert len(animations) == 37
    return {"jar": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "loader": loader, "blocks": len(catalog), "animations": len(animations),
            "shared_resources_identical": len(shared_files) - 1, "java_major": 65,
            "resource_pack_format": 34, "data_pack_format": 48, "result": "PASS"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jars", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = [verify(path) for path in args.jars]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
