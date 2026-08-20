"""Verify that the 1.0.32 JAR only extends the 1.0.31 collision hotfix.

本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。
发布署名仅为"Crzay津仔"，美术素材版权归"Crzay津仔"所有，
模组代码/配置版权归"QiZhang"所有。
"""

from __future__ import annotations

import argparse
import json
import math
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


MOD_ID = "jinzai_traffic_lights"
BASELINE_VERSION = "1.0.31"
CANDIDATE_VERSION = "1.0.32"
CATALOG_ENTRY = f"assets/{MOD_ID}/block_catalog.json"
EXPECTED_BLOCK_COUNT = 161
EXPECTED_BASELINE_COLLISION_COUNT = 3643
EXPECTED_CANDIDATE_COLLISION_COUNT = 3206
EXPECTED_CATEGORY_COUNTS = {
    "frame": 48,
    "indicator": 55,
    "pole": 48,
    "annex": 10,
}

# These are the six additional high-complexity phase-two frames shown by the
# user. The value is the exact number of detailed boxes in the verified 1.0.31
# baseline catalog. The four targets already simplified in 1.0.31 are not in
# this set, so the non-target equality checks also lock that earlier hotfix.
TARGET_OLD_BOX_COUNTS = {
    "jinzai_traffic_light_h18": 82,
    "jinzai_traffic_light_h19": 86,
    "jinzai_traffic_light_h20": 82,
    "jinzai_traffic_light_h21": 83,
    "jinzai_traffic_light_s24": 47,
    "jinzai_traffic_light_s25": 63,
}

# These entries legitimately carry the release version or release notes.  All
# other JAR files must remain byte-for-byte identical to the 1.0.31 baseline,
# except for the catalog whose semantic delta is checked below.
ALLOWED_DIFFERENT_ENTRIES = {
    CATALOG_ENTRY,
    "fabric.mod.json",
    "README.md",
    "META-INF/MANIFEST.MF",
}


def archive_files(archive: zipfile.ZipFile) -> set[str]:
    names = [name for name in archive.namelist() if not name.endswith("/")]
    assert len(names) == len(set(names)), (
        f"JAR contains duplicate file entries: {archive.filename}"
    )
    return set(names)


def archive_json(archive: zipfile.ZipFile, entry: str) -> Any:
    try:
        raw = archive.read(entry)
    except KeyError as exception:
        raise AssertionError(f"Missing JAR entry: {entry}") from exception
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise AssertionError(f"Invalid JSON in {entry}: {exception}") from exception


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def catalog_by_id(
    archive: zipfile.ZipFile,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    document = archive_json(archive, CATALOG_ENTRY)
    assert isinstance(document, dict), "Catalog root is not an object"
    assert set(document) == {"schema", "blocks"} and document["schema"] == 1, (
        f"Invalid catalog document in {archive.filename}"
    )
    blocks = document["blocks"]
    assert isinstance(blocks, list) and len(blocks) == EXPECTED_BLOCK_COUNT, (
        f"Unexpected catalog size in {archive.filename}: "
        f"{len(blocks) if isinstance(blocks, list) else type(blocks).__name__}"
    )

    by_id: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(blocks):
        assert isinstance(entry, dict), f"Catalog entry {index} is not an object"
        assert set(entry) == {
            "id",
            "category",
            "source_folder",
            "source_stem",
            "collision_boxes",
        }, f"Unexpected fields in catalog entry {index}: {sorted(entry)}"
        identifier = entry["id"]
        assert isinstance(identifier, str) and identifier, (
            f"Catalog entry {index} has no valid ID"
        )
        assert identifier not in by_id, f"Duplicate catalog ID: {identifier}"
        by_id[identifier] = entry
    return blocks, by_id


def validated_boxes(entry: dict[str, Any]) -> list[list[int | float]]:
    identifier = entry["id"]
    raw_boxes = entry.get("collision_boxes")
    assert isinstance(raw_boxes, list) and raw_boxes, (
        f"{identifier} has no collision boxes"
    )
    boxes: list[list[int | float]] = []
    for index, raw in enumerate(raw_boxes):
        assert isinstance(raw, list) and len(raw) == 6, (
            f"{identifier} collision box {index} must contain six coordinates"
        )
        assert all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in raw
        ), f"{identifier} collision box {index} contains an invalid coordinate"
        assert all(float(raw[axis]) < float(raw[axis + 3]) for axis in range(3)), (
            f"{identifier} collision box {index} has non-positive volume: {raw}"
        )
        boxes.append(raw)
    return boxes


def envelope(boxes: list[list[int | float]]) -> list[int | float]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        min(box[2] for box in boxes),
        max(box[3] for box in boxes),
        max(box[4] for box in boxes),
        max(box[5] for box in boxes),
    ]


def assert_same_box(
    actual: list[int | float],
    expected: list[int | float],
    identifier: str,
) -> None:
    assert len(actual) == len(expected) == 6
    differences = [
        (index, actual_value, expected_value)
        for index, (actual_value, expected_value) in enumerate(zip(actual, expected))
        if not math.isclose(
            float(actual_value),
            float(expected_value),
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
    ]
    assert not differences, (
        f"{identifier} hotfix box is not the exact 1.0.31 model envelope: "
        f"actual={actual}, expected={expected}, differences={differences}"
    )


def collision_count(blocks: list[dict[str, Any]]) -> int:
    return sum(len(validated_boxes(entry)) for entry in blocks)


def verify_metadata(
    baseline: zipfile.ZipFile,
    candidate: zipfile.ZipFile,
) -> None:
    baseline_metadata = archive_json(baseline, "fabric.mod.json")
    candidate_metadata = archive_json(candidate, "fabric.mod.json")
    assert baseline_metadata.get("id") == candidate_metadata.get("id") == MOD_ID
    assert baseline_metadata.get("version") == BASELINE_VERSION, (
        f"Baseline JAR version is not {BASELINE_VERSION}"
    )
    assert candidate_metadata.get("version") == CANDIDATE_VERSION, (
        f"Candidate JAR version is not {CANDIDATE_VERSION}"
    )

    # Version and prose/notes may change, but identity, ownership, entrypoints,
    # dependencies and environment compatibility may not drift in this hotfix.
    stable_metadata_fields = {
        "schemaVersion",
        "id",
        "name",
        "icon",
        "authors",
        "contact",
        "license",
        "environment",
        "entrypoints",
        "depends",
    }
    for field in sorted(stable_metadata_fields):
        assert candidate_metadata.get(field) == baseline_metadata.get(field), (
            f"fabric.mod.json field changed outside the version/description allowance: {field}"
        )
    assert candidate_metadata.get("authors") == ["Crzay津仔"], (
        "Published author must remain Crzay津仔"
    )
    assert candidate_metadata.get("depends", {}).get("java") == ">=17", (
        "Candidate no longer declares Java 17 or newer"
    )

    baseline_manifest = baseline.read("META-INF/MANIFEST.MF").decode("utf-8")
    candidate_manifest = candidate.read("META-INF/MANIFEST.MF").decode("utf-8")
    assert f"Implementation-Version: {BASELINE_VERSION}" in baseline_manifest
    assert f"Implementation-Version: {CANDIDATE_VERSION}" in candidate_manifest


def verify_collision_delta(
    baseline: zipfile.ZipFile,
    candidate: zipfile.ZipFile,
) -> tuple[int, int]:
    baseline_blocks, baseline_catalog = catalog_by_id(baseline)
    candidate_blocks, candidate_catalog = catalog_by_id(candidate)
    assert list(baseline_catalog) == list(candidate_catalog), (
        "Catalog ordering or identifier inventory changed"
    )
    assert set(TARGET_OLD_BOX_COUNTS) <= set(baseline_catalog), (
        "The 1.0.31 baseline is missing one or more collision hotfix targets"
    )

    category_counts = Counter(entry["category"] for entry in candidate_blocks)
    assert dict(category_counts) == EXPECTED_CATEGORY_COUNTS, (
        f"Creative/category counts changed: {dict(category_counts)}"
    )
    annex_ids = {
        entry["id"] for entry in candidate_blocks if entry["category"] == "annex"
    }
    baseline_annex_ids = {
        entry["id"] for entry in baseline_blocks if entry["category"] == "annex"
    }
    assert annex_ids == baseline_annex_ids and len(annex_ids) == 10, (
        "The independent 10-item traffic-light annex category changed"
    )

    unchanged_count = 0
    for identifier, baseline_entry in baseline_catalog.items():
        candidate_entry = candidate_catalog[identifier]
        if identifier not in TARGET_OLD_BOX_COUNTS:
            assert canonical_json(candidate_entry) == canonical_json(baseline_entry), (
                f"Non-target catalog entry changed: {identifier}"
            )
            unchanged_count += 1
            continue

        baseline_without_boxes = {
            key: value for key, value in baseline_entry.items() if key != "collision_boxes"
        }
        candidate_without_boxes = {
            key: value for key, value in candidate_entry.items() if key != "collision_boxes"
        }
        assert canonical_json(candidate_without_boxes) == canonical_json(
            baseline_without_boxes
        ), f"Target metadata changed outside collision_boxes: {identifier}"
        assert baseline_entry["category"] == "frame", (
            f"Hotfix target is no longer a frame: {identifier}"
        )

        old_boxes = validated_boxes(baseline_entry)
        new_boxes = validated_boxes(candidate_entry)
        assert len(old_boxes) == TARGET_OLD_BOX_COUNTS[identifier], (
            f"Unexpected 1.0.31 baseline box count for {identifier}: {len(old_boxes)}"
        )
        assert len(new_boxes) == 1, (
            f"{identifier} must contain exactly one whole-model bounding box, "
            f"found {len(new_boxes)}"
        )
        expected_envelope = envelope(old_boxes)
        assert_same_box(new_boxes[0], expected_envelope, identifier)
        assert canonical_json(new_boxes) != canonical_json(old_boxes), (
            f"Target collision_boxes did not change: {identifier}"
        )
        print(
            f"  {identifier}: {len(old_boxes)} -> 1, envelope={expected_envelope}"
        )

    assert unchanged_count == EXPECTED_BLOCK_COUNT - len(TARGET_OLD_BOX_COUNTS), (
        f"Unexpected unchanged catalog count: {unchanged_count}"
    )

    baseline_total = collision_count(baseline_blocks)
    candidate_total = collision_count(candidate_blocks)
    assert baseline_total == EXPECTED_BASELINE_COLLISION_COUNT, (
        f"Unexpected 1.0.31 total collision count: {baseline_total}"
    )
    expected_candidate_total = baseline_total - sum(
        TARGET_OLD_BOX_COUNTS.values()
    ) + len(TARGET_OLD_BOX_COUNTS)
    assert candidate_total == expected_candidate_total, (
        f"Unexpected candidate collision count: {candidate_total}; "
        f"expected {expected_candidate_total}"
    )
    assert candidate_total == EXPECTED_CANDIDATE_COLLISION_COUNT, (
        f"Candidate total differs from the locked 1.0.32 count: {candidate_total}"
    )
    return baseline_total, candidate_total


def verify_archive_delta(
    baseline: zipfile.ZipFile,
    candidate: zipfile.ZipFile,
) -> tuple[int, int]:
    baseline_files = archive_files(baseline)
    candidate_files = archive_files(candidate)
    assert baseline_files == candidate_files, (
        "JAR file inventory changed: "
        f"removed={sorted(baseline_files - candidate_files)}, "
        f"added={sorted(candidate_files - baseline_files)}"
    )
    assert ALLOWED_DIFFERENT_ENTRIES <= baseline_files, (
        "One or more expected metadata/catalog entries are missing"
    )

    baseline_namespace = {
        name
        for name in baseline_files
        if name.startswith(f"assets/{MOD_ID}/")
        or name.startswith(f"data/{MOD_ID}/")
    }
    candidate_namespace = {
        name
        for name in candidate_files
        if name.startswith(f"assets/{MOD_ID}/")
        or name.startswith(f"data/{MOD_ID}/")
    }
    assert baseline_namespace == candidate_namespace
    stable_namespace = baseline_namespace - {CATALOG_ENTRY}
    for entry in sorted(stable_namespace):
        assert candidate.read(entry) == baseline.read(entry), (
            f"Namespace resource changed outside block_catalog.json: {entry}"
        )

    class_entries = sorted(name for name in baseline_files if name.endswith(".class"))
    assert class_entries, "Baseline JAR contains no class files"
    assert class_entries == sorted(
        name for name in candidate_files if name.endswith(".class")
    )
    for entry in class_entries:
        baseline_bytes = baseline.read(entry)
        candidate_bytes = candidate.read(entry)
        assert candidate_bytes == baseline_bytes, f"Class bytecode changed: {entry}"
        assert baseline_bytes[:4] == b"\xca\xfe\xba\xbe", (
            f"Invalid class file header: {entry}"
        )
        major_version = int.from_bytes(baseline_bytes[6:8], "big")
        assert major_version == 61, (
            f"{entry} is not Java 17 bytecode (class major={major_version})"
        )

    # Compare every other packed file, not only the mod namespace.  ZIP entry
    # timestamps/compression are intentionally ignored; the uncompressed bytes
    # are authoritative for release-content stability.
    for entry in sorted(baseline_files - ALLOWED_DIFFERENT_ENTRIES):
        assert candidate.read(entry) == baseline.read(entry), (
            f"Unexpected packed-file change: {entry}"
        )
    return len(stable_namespace), len(class_entries)


def verify_hotfix(baseline_path: Path, candidate_path: Path) -> None:
    assert baseline_path.is_file(), f"Baseline JAR not found: {baseline_path}"
    assert candidate_path.is_file(), f"Candidate JAR not found: {candidate_path}"
    assert baseline_path.resolve() != candidate_path.resolve(), (
        "Baseline and candidate must be different JAR files"
    )

    with zipfile.ZipFile(baseline_path) as baseline, zipfile.ZipFile(
        candidate_path
    ) as candidate:
        verify_metadata(baseline, candidate)
        baseline_total, candidate_total = verify_collision_delta(
            baseline, candidate
        )
        stable_namespace_count, class_count = verify_archive_delta(
            baseline, candidate
        )

    print(
        "Verified collision hotfix delta: "
        f"{len(TARGET_OLD_BOX_COUNTS)} target frames, "
        f"{EXPECTED_BLOCK_COUNT - len(TARGET_OLD_BOX_COUNTS)} unchanged catalog entries, "
        f"{baseline_total} -> {candidate_total} total collision boxes, "
        f"{stable_namespace_count} unchanged namespace resources, and "
        f"{class_count} byte-identical Java 17 class files."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the verified 1.0.31 JAR with a 1.0.32 collision-hotfix JAR "
            "and reject every unrelated runtime change."
        )
    )
    parser.add_argument("baseline_jar", type=Path, help="Verified 1.0.31 baseline JAR")
    parser.add_argument("candidate_jar", type=Path, help="Candidate 1.0.32 JAR")
    arguments = parser.parse_args()
    verify_hotfix(arguments.baseline_jar.resolve(), arguments.candidate_jar.resolve())


if __name__ == "__main__":
    main()
