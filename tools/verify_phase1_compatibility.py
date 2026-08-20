"""本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any


MOD_ID = "jinzai_traffic_lights"
PHASE1_VERSIONS = frozenset({"1.0.0", "1.0.1"})
PHASE2_VERSION = "1.0.32"
PHASE1_BLOCK_COUNT = 103
PHASE2_BLOCK_COUNT = 161
PHASE1_LANGUAGE_KEY_COUNT = 213
PHASE2_LANGUAGE_KEY_COUNT = 331
LOCALES = (
    "ar_sa",
    "de_de",
    "en_us",
    "es_es",
    "fr_fr",
    "hi_in",
    "id_id",
    "ja_jp",
    "ko_kr",
    "pt_br",
    "ru_ru",
    "tr_tr",
    "zh_cn",
)
CATALOG_ENTRY = f"assets/{MOD_ID}/block_catalog.json"


def archive_files(archive: zipfile.ZipFile) -> set[str]:
    names = [name for name in archive.namelist() if not name.endswith("/")]
    assert len(names) == len(set(names)), "JAR contains duplicate file entries"
    return set(names)


def archive_json(archive: zipfile.ZipFile, entry: str) -> Any:
    try:
        raw = archive.read(entry)
    except KeyError as exc:
        raise AssertionError(f"Missing JAR entry: {entry}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise AssertionError(f"Invalid JSON in JAR entry {entry}: {exc}") from exc


def verify_metadata(
    archive: zipfile.ZipFile,
    expected_version: str | frozenset[str],
) -> None:
    metadata = archive_json(archive, "fabric.mod.json")
    assert metadata.get("id") == MOD_ID, f"Unexpected mod ID in {archive.filename}"
    actual_version = metadata.get("version")
    matches = (
        actual_version in expected_version
        if isinstance(expected_version, frozenset)
        else actual_version == expected_version
    )
    assert matches, (
        f"Unexpected mod version in {archive.filename}: {metadata.get('version')!r}; "
        f"expected {expected_version!r}"
    )


def catalog_by_id(
    archive: zipfile.ZipFile,
    expected_count: int,
) -> dict[str, dict[str, Any]]:
    document = archive_json(archive, CATALOG_ENTRY)
    assert set(document) == {"schema", "blocks"} and document["schema"] == 1, (
        f"Invalid catalog document in {archive.filename}"
    )
    blocks = document["blocks"]
    assert isinstance(blocks, list) and len(blocks) == expected_count, (
        f"Unexpected catalog size in {archive.filename}: "
        f"{len(blocks) if isinstance(blocks, list) else type(blocks).__name__}"
    )
    result: dict[str, dict[str, Any]] = {}
    for entry in blocks:
        assert isinstance(entry, dict), "Catalog entry is not an object"
        identifier = entry.get("id")
        assert isinstance(identifier, str) and identifier, "Catalog entry has no ID"
        assert identifier not in result, f"Duplicate catalog ID: {identifier}"
        result[identifier] = entry
    return result


def resource_entries(identifier: str) -> tuple[str, ...]:
    return (
        f"assets/{MOD_ID}/models/block/{identifier}.json",
        f"assets/{MOD_ID}/models/item/{identifier}.json",
        f"assets/{MOD_ID}/blockstates/{identifier}.json",
        f"assets/{MOD_ID}/textures/block/{identifier}.png",
        f"data/{MOD_ID}/loot_tables/blocks/{identifier}.json",
    )


def language_entry(locale: str) -> str:
    return f"assets/{MOD_ID}/lang/{locale}.json"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def verify_language_inventory(archive: zipfile.ZipFile) -> None:
    expected = {language_entry(locale) for locale in LOCALES}
    actual = {
        name
        for name in archive_files(archive)
        if name.startswith(f"assets/{MOD_ID}/lang/") and name.endswith(".json")
    }
    assert actual == expected, (
        f"Unexpected language inventory in {archive.filename}: "
        f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
    )


def verify_compatibility(phase1_path: Path, phase2_path: Path) -> None:
    assert phase1_path.is_file(), f"Phase-one JAR not found: {phase1_path}"
    assert phase2_path.is_file(), f"Phase-two JAR not found: {phase2_path}"

    with zipfile.ZipFile(phase1_path) as phase1, zipfile.ZipFile(phase2_path) as phase2:
        phase1_files = archive_files(phase1)
        phase2_files = archive_files(phase2)
        verify_metadata(phase1, PHASE1_VERSIONS)
        verify_metadata(phase2, PHASE2_VERSION)
        verify_language_inventory(phase1)
        verify_language_inventory(phase2)

        phase1_catalog = catalog_by_id(phase1, PHASE1_BLOCK_COUNT)
        phase2_catalog = catalog_by_id(phase2, PHASE2_BLOCK_COUNT)
        phase1_ids = set(phase1_catalog)
        phase2_ids = set(phase2_catalog)
        assert phase1_ids <= phase2_ids, (
            f"Phase two removed phase-one IDs: {sorted(phase1_ids - phase2_ids)}"
        )
        assert len(phase2_ids - phase1_ids) == PHASE2_BLOCK_COUNT - PHASE1_BLOCK_COUNT

        for identifier in sorted(phase1_ids):
            assert canonical_json(phase2_catalog[identifier]) == canonical_json(
                phase1_catalog[identifier]
            ), (
                f"Phase-one catalog entry changed: {identifier}"
            )
            for entry in resource_entries(identifier):
                assert entry in phase1_files, f"Phase-one JAR is missing {entry}"
                assert entry in phase2_files, f"Phase-two JAR is missing phase-one resource {entry}"
                assert phase2.read(entry) == phase1.read(entry), (
                    f"Phase-one resource changed: {entry}"
                )

        preserved_language_values = 0
        for locale in LOCALES:
            entry = language_entry(locale)
            phase1_language = archive_json(phase1, entry)
            phase2_language = archive_json(phase2, entry)
            assert isinstance(phase1_language, dict) and len(phase1_language) == PHASE1_LANGUAGE_KEY_COUNT
            assert isinstance(phase2_language, dict) and len(phase2_language) == PHASE2_LANGUAGE_KEY_COUNT
            assert set(phase1_language) <= set(phase2_language), (
                f"Phase two removed {locale} language keys: "
                f"{sorted(set(phase1_language) - set(phase2_language))}"
            )
            changed = {
                key: (phase1_language[key], phase2_language[key])
                for key in phase1_language
                if phase2_language[key] != phase1_language[key]
            }
            assert not changed, f"Phase-one {locale} language values changed: {changed}"
            preserved_language_values += len(phase1_language)

    print(
        f"Verified phase-one compatibility: {PHASE1_BLOCK_COUNT} catalog entries, "
        f"{PHASE1_BLOCK_COUNT * len(resource_entries('example'))} per-ID resource files, "
        f"and {preserved_language_values} localized key/value pairs are byte/value stable "
        f"from {phase1_path} to {phase2_path}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that a JINZAI Traffic Lights 1.0.32 JAR preserves every "
            "phase-one 1.0.0/1.0.1 catalog entry, per-block resource, and language value."
        )
    )
    parser.add_argument("phase1_jar", type=Path, help="Verified 1.0.0 or 1.0.1 baseline JAR")
    parser.add_argument("phase2_jar", type=Path, help="Candidate 1.0.32 JAR")
    args = parser.parse_args()
    verify_compatibility(args.phase1_jar.resolve(), args.phase2_jar.resolve())


if __name__ == "__main__":
    main()
