"""本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import itertools
import json
import math
import posixpath
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_ROOT = ROOT
MOD_ID = "jinzai_traffic_lights"
MOD_VERSION = "2.0.45"
RESOURCE_ROOT = ROOT / "common" / "src" / "main" / "resources"
ASSET_ROOT = RESOURCE_ROOT / "assets" / MOD_ID
DATA_ROOT = RESOURCE_ROOT / "data" / MOD_ID
ICON_PATH = RESOURCE_ROOT / "icon.png"
GRADLE_PROPERTIES_PATH = ROOT / "gradle.properties"
COMMON_MAIN_PATH = (
    ROOT
    / "common"
    / "src"
    / "main"
    / "java"
    / "cn"
    / "crazyjinzai"
    / "trafficlights"
    / "JinzaiTrafficLights.java"
)
FABRIC_METADATA_PATH = ROOT / "fabric" / "src" / "main" / "resources" / "fabric.mod.json"
FORGE_METADATA_PATH = ROOT / "forge" / "src" / "main" / "resources" / "META-INF" / "mods.toml"
TRANSLATION_SOURCE_ROOT = ROOT / "tools" / "translations"
PHASE2_TRANSLATION_SOURCE = TRANSLATION_SOURCE_ROOT / "phase2_names.json"
PHASE3_TRANSLATION_SOURCE = TRANSLATION_SOURCE_ROOT / "phase3_names.json"
PHASE4_TRANSLATION_SOURCE = TRANSLATION_SOURCE_ROOT / "phase4_names.json"
GUI_DISPLAY_OVERRIDES = json.loads((ROOT / "tools" / "gui_display_overrides.json").read_text(encoding="utf-8"))
EXPECTED_GUI_OVERRIDE_IDS = frozenset({
    "bd_pole_3", "bd_pole_4", "bd_pole_4a", "bd_pole_5a",
    "bd_pole_7", "bd_pole_8", "bd_pole_9", "bd_pole_10",
    "thick_pole_3", "thick_pole_3a", "thick_pole_3b", "thick_pole_3c", "thick_pole_4f", "thick_pole_5",
    "white_pole_3", "white_pole_3a", "white_pole_3b", "white_pole_3c", "white_pole_4d", "white_pole_5",
    "jinzai_traffic_light_h14", "jinzai_traffic_light_h18", "jinzai_traffic_light_h19", "jinzai_traffic_light_h20",
    "jinzai_traffic_light_h23c", "jinzai_traffic_ligh_r6a",
})
PHASE4_INTERNAL_SOURCE_ALIASES = {"bd_pole_18": "bd_pole_14"}
EXTRA_LOCALES = (
    "ar_sa",
    "de_de",
    "es_es",
    "fr_fr",
    "hi_in",
    "id_id",
    "ja_jp",
    "ko_kr",
    "pt_br",
    "ru_ru",
    "tr_tr",
)
ALL_LOCALES = ("zh_cn", "en_us", *EXTRA_LOCALES)

SOURCE_FOLDERS = {
    "杆子": ("pole", "杆子模型名称.xlsx", 46),
    "杆子（新增）": ("pole", "杆子新增方块.xlsx", 2),
    "红绿灯框架": ("frame", "红绿灯框架重置模型名称.xlsx", 27),
    "红绿灯框架（新增）": ("frame", "红绿灯框架（二期）新增方块.xlsx", 21),
    "指示灯": ("indicator", "指示灯重置模型名称.xlsx", 30),
    "指示灯（新增）": ("indicator", "指示灯新增方块名称.xlsx", 25),
    "交通灯附属": ("annex", "交通灯附属新增方块名称.xlsx", 10),
}

PHASE2_SOURCE_FOLDERS = {
    "杆子（新增）",
    "红绿灯框架（新增）",
    "指示灯（新增）",
    "交通灯附属",
}
PHASE3_SOURCE_FOLDERS = {
    "动态指示灯（三期）": ("indicator", 15),
    "杆子（三期新增）": ("pole", 24),
    "红绿灯框架（三期新增）": ("frame", 11),
    "指示灯（三期新增）": ("indicator", 2),
}
PHASE3_EXPECTED_CATEGORY_COUNTS = {
    "frame": 11,
    "indicator": 17,
    "pole": 24,
}
PHASE3_DYNAMIC_FOLDER = "动态指示灯（三期）"
PHASE3_DYNAMIC_IDS = frozenset(
    f"jinzai_dynamic_light_{index}" for index in range(1, 16)
)
EXPECTED_ANIMATION_FRAME_COUNTS = {
    **{f"jinzai_dynamic_light_{index}": 65 for index in (*range(1, 7), 14, 15)},
    **{f"jinzai_dynamic_light_{index}": 8 for index in (*range(7, 12), 13)},
    "jinzai_dynamic_light_12": 11,
}
PHASE3_LONG_DIAGONAL_POLE_IDS = frozenset({"bd_pole_8", "bd_pole_10"})
PHASE4_MODIFIED_MODEL_IDS = frozenset({
    "jinzai_traffic_light_c5", "jinzai_traffic_light_h30", "jinzai_traffic_light_h31",
})

CATEGORIES = ("frame", "indicator", "pole", "annex")
PHASE4_SOURCE_FOLDERS = {
    "红绿灯框架（四期新增）": ("frame", 6),
    "指示灯（四期新增）": ("indicator", 6),
    "杆子（四期新增）": ("pole", 5),
    "交通灯附属（四期新增）": ("annex", 4),
}
EXPECTED_CATEGORY_COUNTS = {
    "frame": 65,
    "indicator": 78,
    "pole": 77,
    "annex": 14,
}
EXPECTED_ASSET_COUNT = 234
EXPECTED_LANGUAGE_KEY_COUNT = 238
EXPECTED_SOURCE_ELEMENT_COUNT = 3627
EXPECTED_VISIBLE_ELEMENT_COUNT = 3624
EXPECTED_COLLISION_BOX_COUNT = 3375
EXPECTED_PHASE3_COLLISION_BOX_COUNT = 237
EXPECTED_PHASE3_POLE_COLLISION_BOX_COUNT = 209
EXPECTED_ANIMATION_METADATA_COUNT = 15

# The phase-two workbooks contain a handful of filename typos.  Keep their
# requested IDs stable while resolving them to the actual supplied source
# pairs on disk.
NEW_FRAME_SOURCE_ALIASES = {
    "jinzai_traffic_light_h23c": "jinzai_traffic_light_h23a",
    "jinzai_traffic_ligh_r2": "jinzai_traffic_light_r2",
    "jinzai_traffic_ligh_r3": "jinzai_traffic_light_r3",
    "jinzai_traffic_ligh_r4": "jinzai_traffic_light_r4",
    "jinzai_traffic_ligh_r5": "jinzai_traffic_light_r5",
    "jinzai_traffic_ligh_r6": "jinzai_traffic_light_r6",
    "jinzai_traffic_ligh_r6a": "jinzai_traffic_light_r6a",
    "jinzai_traffic_ligh_r6b": "jinzai_traffic_light_r6b",
}
SIMPLIFIED_BOUNDING_COLLISION_IDS = frozenset({
    "jinzai_traffic_light_c22",
    "jinzai_traffic_light_c23",
    "jinzai_traffic_light_c26",
    "jinzai_traffic_light_c27",
    "jinzai_traffic_light_h18",
    "jinzai_traffic_light_h19",
    "jinzai_traffic_light_h20",
    "jinzai_traffic_light_h21",
    "jinzai_traffic_light_s24",
    "jinzai_traffic_light_s25",
})
EXPECTED_PRECISE_COLLISION_COUNTS = {
    "jinzai_traffic_light_c22": 121,
    "jinzai_traffic_light_c23": 266,
    "jinzai_traffic_light_c26": 129,
    "jinzai_traffic_light_c27": 137,
    "jinzai_traffic_light_h18": 82,
    "jinzai_traffic_light_h19": 86,
    "jinzai_traffic_light_h20": 82,
    "jinzai_traffic_light_h21": 83,
    "jinzai_traffic_light_s24": 47,
    "jinzai_traffic_light_s25": 63,
}
ANNEX_DEPRECATED_STEMS = {
    "jinzai_traffic_annex_1",
    "jinzai_traffic_annex_1a",
}
PHASE1_SOURCE_FOLDERS = {"杆子", "红绿灯框架", "指示灯"}

_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_RESOURCE_ID_RE = re.compile(r"^[a-z0-9._-]+$")


@dataclass(frozen=True)
class ExpectedAsset:
    folder: str
    source_stem: str
    identifier: str
    category: str
    zh_cn: str
    en_us: str | None = None

    @property
    def source_model(self) -> Path:
        return ROOT / self.folder / f"{self.source_stem}.bbmodel"

    @property
    def source_texture(self) -> Path:
        return ROOT / self.folder / f"{self.source_stem}.png"

    @property
    def source_animation_metadata(self) -> Path:
        return Path(f"{self.source_texture}.mcmeta")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AssertionError(f"Invalid JSON: {path}: {exc}") from exc


def _xlsx_text(node: ET.Element) -> str:
    return "".join(text.text or "" for text in node.iter(f"{{{_SHEET_NS}}}t"))


def read_xlsx_rows(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [_xlsx_text(item) for item in shared_root.findall(f"{{{_SHEET_NS}}}si")]
        sheet = workbook.find(f"{{{_SHEET_NS}}}sheets/{{{_SHEET_NS}}}sheet")
        assert sheet is not None, f"No worksheet in {path}"
        relationship_id = sheet.attrib[f"{{{_DOC_REL_NS}}}id"]
        target = next(
            relationship.attrib["Target"]
            for relationship in rels.findall(f"{{{_PKG_REL_NS}}}Relationship")
            if relationship.attrib.get("Id") == relationship_id
        )
        entry = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        root = ET.fromstring(archive.read(entry))
        result: list[dict[str, str]] = []
        for row in root.findall(f".//{{{_SHEET_NS}}}sheetData/{{{_SHEET_NS}}}row"):
            values: dict[str, str] = {}
            for cell in row.findall(f"{{{_SHEET_NS}}}c"):
                match = re.match(r"([A-Z]+)", cell.attrib.get("r", ""))
                if not match:
                    continue
                column = match.group(1)
                cell_type = cell.attrib.get("t")
                if cell_type == "inlineStr":
                    value = _xlsx_text(cell)
                else:
                    value_node = cell.find(f"{{{_SHEET_NS}}}v")
                    raw = "" if value_node is None else value_node.text or ""
                    value = shared[int(raw)] if cell_type == "s" and raw else raw
                values[column] = value.strip()
            result.append(values)
        return result


def paired_source_stems(folder: str) -> set[str]:
    source_dir = ROOT / folder
    models = {path.stem for path in source_dir.glob("*.bbmodel")}
    textures = {path.stem for path in source_dir.glob("*.png")}
    assert models == textures, (
        f"Unpaired sources in {folder}: models-only={sorted(models - textures)}, "
        f"textures-only={sorted(textures - models)}"
    )
    return models


def discover_phase4_assets() -> list[ExpectedAsset]:
    payload = load_json(PHASE4_TRANSLATION_SOURCE)
    assert isinstance(payload, dict) and set(payload) == {"schema", "assets", "locales"}
    assert payload["schema"] == 1 and isinstance(payload["assets"], list)
    assert len(payload["assets"]) == 21, "Phase four must contain all 21 supplied new models"
    fields = {"source_folder", "source_stem", "id", "category", "zh_cn", "en_us"}
    result: list[ExpectedAsset] = []
    for asset in payload["assets"]:
        assert isinstance(asset, dict) and set(asset) == fields
        assert all(isinstance(asset[key], str) and asset[key].strip() for key in fields)
        folder = asset["source_folder"]
        assert folder in PHASE4_SOURCE_FOLDERS
        assert asset["category"] == PHASE4_SOURCE_FOLDERS[folder][0]
        assert asset["id"] == asset["source_stem"] and _RESOURCE_ID_RE.fullmatch(asset["id"])
        result.append(ExpectedAsset(folder, asset["source_stem"], asset["id"], asset["category"],
                                    asset["zh_cn"], asset["en_us"]))
    for folder, (_, count) in PHASE4_SOURCE_FOLDERS.items():
        stems = {item.source_stem for item in result if item.folder == folder}
        assert len(stems) == count and stems == paired_source_stems(folder), (
            f"Phase-four source inventory mismatch: {folder}"
        )
    return result


def discover_expected_assets() -> list[ExpectedAsset]:
    expected: list[ExpectedAsset] = []

    def add_simple_workbook(
        folder: str,
        *,
        aliases: dict[str, str] | None = None,
        expected_deprecated: set[str] | None = None,
    ) -> None:
        category, workbook, expected_count = SOURCE_FOLDERS[folder]
        resolved: dict[str, tuple[str, str]] = {}
        deprecated: set[str] = set()
        source_aliases = aliases or {}
        for row in read_xlsx_rows(WORKBOOK_ROOT / folder / workbook)[1:]:
            workbook_stem = row.get("A", "")
            if not workbook_stem:
                continue
            if "已废弃" in row.get("C", ""):
                deprecated.add(workbook_stem)
                continue
            source_stem = source_aliases.get(workbook_stem, workbook_stem)
            assert source_stem not in resolved, (
                f"Duplicate corrected source mapping in {folder}: {source_stem}"
            )
            resolved[source_stem] = (workbook_stem.lower(), row.get("B", ""))

        assert deprecated == (expected_deprecated or set()), (
            f"Unexpected deprecated rows in {folder}: {deprecated}"
        )
        assert len(resolved) == expected_count, (
            f"Unexpected mapped count in {folder}: {len(resolved)}; expected {expected_count}"
        )
        actual_stems = paired_source_stems(folder)
        assert set(resolved) == actual_stems, (
            f"{folder} XLSX does not exactly cover paired sources: "
            f"workbook-only={sorted(set(resolved) - actual_stems)}, "
            f"source-only={sorted(actual_stems - set(resolved))}"
        )
        expected.extend(
            ExpectedAsset(folder, source_stem, identifier, category, name)
            for source_stem, (identifier, name) in resolved.items()
        )

    add_simple_workbook(
        "杆子",
        expected_deprecated={"thick_pole_2", "white_pole_2"},
    )
    add_simple_workbook("杆子（新增）")
    add_simple_workbook("红绿灯框架")
    add_simple_workbook(
        "红绿灯框架（新增）",
        aliases=NEW_FRAME_SOURCE_ALIASES,
    )

    indicator_rows = read_xlsx_rows(WORKBOOK_ROOT / "指示灯" / SOURCE_FOLDERS["指示灯"][1])
    indicator_map: dict[str, tuple[str, str]] = {}
    for row_number, row in enumerate(indicator_rows[1:], start=2):
        stem = row.get("A", "")
        identifier = row.get("C", "")
        if not stem or not identifier:
            continue
        if row_number == 31 and stem == "jinzai_traffic_indicator_z3" and identifier.endswith("_ly5"):
            stem = "jinzai_traffic_indicator_z3a"
        requested_name = row.get("D", "")
        zh_cn = row.get("B", "") if requested_name in ("", "[保持原名]") else requested_name
        assert stem not in indicator_map, f"Duplicate corrected indicator source mapping: {stem}"
        indicator_map[stem] = (identifier, zh_cn)
    assert set(indicator_map) == paired_source_stems("指示灯"), "Indicator XLSX does not exactly cover paired sources"
    expected.extend(
        ExpectedAsset("指示灯", stem, identifier, "indicator", name)
        for stem, (identifier, name) in indicator_map.items()
    )

    new_indicator_rows = read_xlsx_rows(
        WORKBOOK_ROOT / "指示灯（新增）" / SOURCE_FOLDERS["指示灯（新增）"][1]
    )
    new_indicator_map: dict[str, tuple[str, str]] = {}
    duplicate_7b_seen = False
    for row in new_indicator_rows[1:]:
        workbook_stem = row.get("A", "")
        if not workbook_stem:
            continue
        source_stem = workbook_stem
        if workbook_stem == "jinzai_traffic_light_7b":
            if duplicate_7b_seen:
                source_stem = "jinzai_traffic_light_7d"
            duplicate_7b_seen = True
        assert source_stem not in new_indicator_map, (
            f"Duplicate corrected phase-two indicator source mapping: {source_stem}"
        )
        new_indicator_map[source_stem] = (source_stem.lower(), row.get("B", ""))
    assert duplicate_7b_seen, "Expected duplicated 7b indicator workbook row"
    assert len(new_indicator_map) == SOURCE_FOLDERS["指示灯（新增）"][2]
    assert set(new_indicator_map) == paired_source_stems("指示灯（新增）"), (
        "Phase-two indicator XLSX does not exactly cover paired sources"
    )
    expected.extend(
        ExpectedAsset("指示灯（新增）", stem, identifier, "indicator", name)
        for stem, (identifier, name) in new_indicator_map.items()
    )

    add_simple_workbook(
        "交通灯附属",
        expected_deprecated=ANNEX_DEPRECATED_STEMS,
    )

    phase3_payload = load_json(PHASE3_TRANSLATION_SOURCE)
    assert isinstance(phase3_payload, dict), "Phase-three translation source must be an object"
    assert set(phase3_payload) == {"schema", "assets", "locales"}, (
        "Unexpected phase-three translation root fields"
    )
    assert phase3_payload["schema"] == 1, "Unsupported phase-three translation schema"
    phase3_assets = phase3_payload["assets"]
    assert isinstance(phase3_assets, list) and len(phase3_assets) == 52, (
        "Phase-three translation source must contain exactly 52 assets"
    )
    expected_phase3_asset_fields = {
        "source_folder",
        "source_stem",
        "id",
        "category",
        "zh_cn",
        "en_us",
    }
    phase3_items: list[ExpectedAsset] = []
    for index, asset in enumerate(phase3_assets):
        assert isinstance(asset, dict) and set(asset) == expected_phase3_asset_fields, (
            f"Unexpected phase-three asset fields at index {index}"
        )
        assert all(
            isinstance(asset[field], str) and asset[field].strip()
            for field in expected_phase3_asset_fields
        ), f"Blank or non-string phase-three asset field at index {index}"
        folder = asset["source_folder"]
        source_stem = asset["source_stem"]
        identifier = asset["id"]
        category = asset["category"]
        assert folder in PHASE3_SOURCE_FOLDERS, (
            f"Unknown phase-three source folder at index {index}: {folder}"
        )
        assert category == PHASE3_SOURCE_FOLDERS[folder][0], (
            f"Wrong phase-three category for {identifier}: {category}"
        )
        assert source_stem == identifier == identifier.lower(), (
            f"Phase-three source/id is not normalized: {source_stem!r} -> {identifier!r}"
        )
        assert _RESOURCE_ID_RE.fullmatch(identifier), (
            f"Invalid phase-three resource ID: {identifier}"
        )
        assert "daynamic" not in source_stem and "daynamic" not in identifier, (
            f"Misspelled phase-three dynamic name remains: {identifier}"
        )
        phase3_items.append(
            ExpectedAsset(
                folder,
                source_stem,
                identifier,
                category,
                asset["zh_cn"],
                asset["en_us"],
            )
        )

    phase3_ids = [item.identifier for item in phase3_items]
    assert len(phase3_ids) == len(set(phase3_ids)), "Duplicate phase-three resource ID"
    for folder, (_, expected_count) in PHASE3_SOURCE_FOLDERS.items():
        mapped_stems = {
            item.source_stem for item in phase3_items if item.folder == folder
        }
        actual_stems = paired_source_stems(folder)
        assert len(mapped_stems) == expected_count, (
            f"Unexpected phase-three mapped count in {folder}: {len(mapped_stems)}"
        )
        assert mapped_stems == actual_stems, (
            f"{folder} JSON does not exactly cover paired sources: "
            f"mapping-only={sorted(mapped_stems - actual_stems)}, "
            f"source-only={sorted(actual_stems - mapped_stems)}"
        )
    phase3_category_counts = {
        category: sum(item.category == category for item in phase3_items)
        for category in PHASE3_EXPECTED_CATEGORY_COUNTS
    }
    assert phase3_category_counts == PHASE3_EXPECTED_CATEGORY_COUNTS, (
        f"Unexpected phase-three category counts: {phase3_category_counts}"
    )
    assert {
        item.identifier for item in phase3_items if item.folder == PHASE3_DYNAMIC_FOLDER
    } == PHASE3_DYNAMIC_IDS, "The 15 normalized animated-light IDs changed"
    assert "jinzai_traffic_light_h34" in phase3_ids, "Corrected h34 frame is missing"
    assert "jinzai_traffic_light_c34" not in phase3_ids, "Obsolete c34 frame ID remains"
    expected.extend(phase3_items)
    expected.extend(discover_phase4_assets())

    category_counts = {
        category: sum(item.category == category for item in expected)
        for category in CATEGORIES
    }
    assert category_counts == EXPECTED_CATEGORY_COUNTS, category_counts
    assert len(expected) == EXPECTED_ASSET_COUNT
    identifiers = [item.identifier for item in expected]
    assert len(set(identifiers)) == EXPECTED_ASSET_COUNT, "Final resource IDs are not unique"
    assert all(_RESOURCE_ID_RE.fullmatch(identifier) for identifier in identifiers), "Invalid resource ID"
    assert all(item.zh_cn.strip() for item in expected), "Blank Chinese asset name"
    by_source = {(item.folder, item.source_stem): item for item in expected}
    assert by_source[("杆子", "Lights_1")].identifier == "lights_1"
    assert by_source[("杆子", "Lights_1a")].identifier == "lights_1a"
    assert by_source[("指示灯", "jinzai_traffic_indicator_z3")].identifier == "jinzai_traffic_light_ly4"
    assert by_source[("指示灯", "jinzai_traffic_indicator_z3a")].identifier == "jinzai_traffic_light_ly5"
    assert by_source[("红绿灯框架（新增）", "jinzai_traffic_light_h23a")].identifier == (
        "jinzai_traffic_light_h23c"
    )
    assert by_source[("红绿灯框架（新增）", "jinzai_traffic_light_r6b")].identifier == (
        "jinzai_traffic_ligh_r6b"
    )
    assert by_source[("指示灯（新增）", "jinzai_traffic_light_7d")].identifier == (
        "jinzai_traffic_light_7d"
    )
    assert by_source[(PHASE3_DYNAMIC_FOLDER, "jinzai_dynamic_light_9")].identifier == (
        "jinzai_dynamic_light_9"
    )
    assert by_source[("红绿灯框架（三期新增）", "jinzai_traffic_light_h34")].identifier == (
        "jinzai_traffic_light_h34"
    )
    return sorted(
        expected,
        key=lambda item: (
            CATEGORIES.index(item.category),
            item.source_stem.lower(),
            item.source_stem,
        ),
    )


def phase2_translation_locales(
    phase2_items: list[ExpectedAsset],
) -> dict[str, dict[str, Any]]:
    payload = load_json(PHASE2_TRANSLATION_SOURCE)
    assert isinstance(payload, dict), "Phase-two translation source must be an object"
    assert set(payload) == {"schema", "phase2_ids", "locales"}, (
        "Unexpected phase-two translation root fields"
    )
    assert payload["schema"] == 1, "Unsupported phase-two translation schema"

    expected_ids = {item.identifier for item in phase2_items}
    supplied_ids = payload["phase2_ids"]
    assert isinstance(supplied_ids, list) and all(
        isinstance(identifier, str) and identifier.strip()
        for identifier in supplied_ids
    ), "phase2_ids must be non-blank strings"
    assert len(supplied_ids) == len(set(supplied_ids)), "phase2_ids contains duplicates"
    assert set(supplied_ids) == expected_ids, (
        f"Phase-two translated identifier mismatch: "
        f"missing={sorted(expected_ids - set(supplied_ids))}, "
        f"extra={sorted(set(supplied_ids) - expected_ids)}"
    )

    locales = payload["locales"]
    assert isinstance(locales, dict), "Phase-two translation locales must be an object"
    assert set(locales) == set(EXTRA_LOCALES), (
        f"Phase-two translation locale mismatch: "
        f"missing={sorted(set(EXTRA_LOCALES) - set(locales))}, "
        f"extra={sorted(set(locales) - set(EXTRA_LOCALES))}"
    )
    return locales


def expected_phase2_locale_values(
    locale: str,
    locale_source: dict[str, Any],
    phase2_items: list[ExpectedAsset],
) -> dict[str, str]:
    expected_fields = {
        "names",
        "item_group_annex",
    }
    assert isinstance(locale_source, dict) and set(locale_source) == expected_fields, (
        f"Unexpected phase-two locale fields for {locale}"
    )
    expected_ids = {item.identifier for item in phase2_items}
    names = locale_source["names"]
    assert isinstance(names, dict) and set(names) == expected_ids, (
        f"Phase-two name identifier mismatch for {locale}"
    )
    values: dict[str, str] = {
        f"itemGroup.{MOD_ID}.annex": locale_source["item_group_annex"],
    }
    for item in phase2_items:
        name = names[item.identifier]
        assert isinstance(name, str) and name.strip(), (
            f"Blank phase-two name for {locale}: {item.identifier}"
        )
        values[f"block.{MOD_ID}.{item.identifier}"] = name

    assert len(values) == len(phase2_items) + 1 == 59
    assert all(isinstance(value, str) and value.strip() for value in values.values()), (
        f"Blank phase-two translation value for {locale}"
    )
    return values


def phase3_translation_locales(
    phase3_items: list[ExpectedAsset],
    source_path: Path = PHASE3_TRANSLATION_SOURCE,
) -> dict[str, dict[str, Any]]:
    payload = load_json(source_path)
    assert isinstance(payload, dict) and set(payload) == {"schema", "assets", "locales"}, (
        "Unexpected phase-three translation root fields"
    )
    assert payload["schema"] == 1, "Unsupported phase-three translation schema"
    supplied_ids = [asset.get("id") for asset in payload["assets"]]
    expected_ids = {item.identifier for item in phase3_items}
    assert len(supplied_ids) == len(set(supplied_ids)) == len(phase3_items), (
        "Phase-three translated identifiers are missing or duplicated"
    )
    assert set(supplied_ids) == expected_ids, "Phase-three translated identifier mismatch"
    locales = payload["locales"]
    assert isinstance(locales, dict) and set(locales) == set(EXTRA_LOCALES), (
        "Phase-three translation locale inventory mismatch"
    )
    return locales


def expected_expansion_locale_values(
    locale: str,
    locale_source: dict[str, Any],
    phase3_items: list[ExpectedAsset],
) -> dict[str, str]:
    assert isinstance(locale_source, dict) and set(locale_source) == {"names"}, (
        f"Unexpected phase-three locale fields for {locale}; no extra creative tab is allowed"
    )
    expected_ids = {item.identifier for item in phase3_items}
    names = locale_source["names"]
    assert isinstance(names, dict) and set(names) == expected_ids, (
        f"Phase-three name identifier mismatch for {locale}"
    )
    values: dict[str, str] = {}
    for item in phase3_items:
        name = names[item.identifier]
        assert isinstance(name, str) and name.strip(), (
            f"Blank phase-three name for {locale}: {item.identifier}"
        )
        values[f"block.{MOD_ID}.{item.identifier}"] = name
    assert len(values) == len(phase3_items)
    return values


def rounded(value: float, digits: int = 6) -> float | int:
    result = round(float(value), digits)
    if math.isclose(result, round(result), abs_tol=10 ** (-digits)):
        return int(round(result))
    return result


def inflated_bounds(element: dict[str, Any]) -> tuple[list[float], list[float]]:
    inflate = float(element.get("inflate", 0) or 0)
    return (
        [float(value) - inflate for value in element["from"]],
        [float(value) + inflate for value in element["to"]],
    )


def rotation_parts(element: dict[str, Any]) -> tuple[str, float, list[float]] | None:
    rotation = element.get("rotation")
    if not rotation or not any(abs(float(value)) > 1e-9 for value in rotation):
        return None
    assert not element.get("rescale", False), "Rotated rescale=true elements are unsupported"
    non_zero = [(axis, float(angle)) for axis, angle in zip("xyz", rotation) if abs(float(angle)) > 1e-9]
    assert len(non_zero) == 1, f"Multi-axis rotation: {rotation}"
    axis, angle = non_zero[0]
    assert angle in (-45.0, -22.5, 22.5, 45.0), f"Illegal Minecraft rotation: {angle}"
    return axis, angle, [float(value) for value in element.get("origin", [8, 8, 8])]


def rotate_point(point: Iterable[float], axis: str, angle: float, origin: Iterable[float]) -> list[float]:
    x, y, z = (float(value) for value in point)
    ox, oy, oz = (float(value) for value in origin)
    x, y, z = x - ox, y - oy, z - oz
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    if axis == "x":
        y, z = y * cosine - z * sine, y * sine + z * cosine
    elif axis == "y":
        x, z = x * cosine + z * sine, -x * sine + z * cosine
    else:
        assert axis == "z"
        x, y = x * cosine - y * sine, x * sine + y * cosine
    return [x + ox, y + oy, z + oz]


def rotated_bounds_aabb(
    from_pos: list[float],
    to_pos: list[float],
    rotation: tuple[str, float, list[float]] | None,
) -> list[float | int]:
    corners = [list(point) for point in itertools.product(*zip(from_pos, to_pos))]
    if rotation is not None:
        axis, angle, origin = rotation
        corners = [rotate_point(point, axis, angle, origin) for point in corners]
    minimum = [min(point[index] for point in corners) for index in range(3)]
    maximum = [max(point[index] for point in corners) for index in range(3)]
    return [rounded(value) for value in minimum + maximum]


def split_intervals(
    start: float,
    end: float,
    maximum_size: float = 1.0,
) -> list[tuple[float, float]]:
    length = end - start
    assert length > 0, f"Non-positive source interval: {start}..{end}"
    assert maximum_size > 0, f"Non-positive maximum interval size: {maximum_size}"
    count = max(1, math.ceil(length / maximum_size - 1e-9))
    step = length / count
    intervals = [
        (start + step * index, end if index + 1 == count else start + step * (index + 1))
        for index in range(count)
    ]
    assert all(0 < high - low <= maximum_size + 1e-9 for low, high in intervals)
    return intervals


def expected_collision_boxes(
    element: dict[str, Any],
    maximum_rotated_cell_size: float = 1.0,
) -> list[list[float | int]]:
    from_pos, to_pos = inflated_bounds(element)
    rotation = rotation_parts(element)
    if rotation is None:
        return [rotated_bounds_aabb(from_pos, to_pos, None)]

    axis, _, _ = rotation
    first_axis, second_axis = {
        "x": (1, 2),
        "y": (0, 2),
        "z": (0, 1),
    }[axis]
    boxes: list[list[float | int]] = []
    for first, second in itertools.product(
        split_intervals(
            from_pos[first_axis],
            to_pos[first_axis],
            maximum_rotated_cell_size,
        ),
        split_intervals(
            from_pos[second_axis],
            to_pos[second_axis],
            maximum_rotated_cell_size,
        ),
    ):
        low = list(from_pos)
        high = list(to_pos)
        low[first_axis], high[first_axis] = first
        low[second_axis], high[second_axis] = second
        boxes.append(rotated_bounds_aabb(low, high, rotation))
    return boxes


def expected_enclosing_collision_box(
    boxes: list[list[float | int]],
) -> list[list[float | int]]:
    assert boxes, "Cannot calculate an enclosing box for an empty model"
    minimum = [min(float(box[index]) for box in boxes) for index in range(3)]
    maximum = [max(float(box[index + 3]) for box in boxes) for index in range(3)]
    return [[rounded(value) for value in minimum + maximum]]


def rotate_catalog_box_clockwise(box: list[float | int]) -> list[float | int]:
    """Mirror CatalogFacingBlock's clockwise rotation in 0..16 model units."""
    return [
        rounded(16.0 - float(box[5])),
        box[1],
        box[0],
        rounded(16.0 - float(box[2])),
        box[4],
        box[3],
    ]


def referenced_texture_index(source: dict[str, Any], stem: str) -> int:
    references: set[int] = set()
    for element in source["elements"]:
        for face in element.get("faces", {}).values():
            if face is not None and face.get("enabled") is not False and face.get("texture") is not None:
                references.add(int(face["texture"]))
    assert len(references) == 1, f"{stem} references {references}"
    index = next(iter(references))
    assert 0 <= index < len(source["textures"]), f"Invalid texture index in {stem}"
    texture = source["textures"][index]
    assert texture["name"] == texture["relative_path"] == f"{stem}.png", f"Texture mismatch in {stem}"
    return index


def phase_of(item: ExpectedAsset) -> int:
    if item.folder in PHASE1_SOURCE_FOLDERS:
        return 1
    if item.folder in PHASE2_SOURCE_FOLDERS:
        return 2
    if item.folder in PHASE4_SOURCE_FOLDERS:
        return 4
    assert item.folder in PHASE3_SOURCE_FOLDERS, f"Unknown source phase: {item.folder}"
    return 3


def verify_phase3_embedded_texture(
    source: dict[str, Any],
    texture_index: int,
    item: ExpectedAsset,
) -> None:
    if phase_of(item) not in (3, 4):
        return
    texture_source = source["textures"][texture_index].get("source")
    prefix = "data:image/png;base64,"
    assert isinstance(texture_source, str) and texture_source.startswith(prefix), (
        f"Phase-three model has no embedded PNG: {item.source_model}"
    )
    try:
        embedded = base64.b64decode(texture_source[len(prefix):], validate=True)
    except (ValueError, binascii.Error) as exception:
        raise AssertionError(
            f"Invalid embedded PNG in {item.source_model}: {exception}"
        ) from exception
    assert embedded == item.source_texture.read_bytes(), (
        f"Embedded/external texture mismatch for phase-three model {item.source_stem}"
    )


def png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert (
        len(header) == 24
        and header[:8] == b"\x89PNG\r\n\x1a\n"
        and header[12:16] == b"IHDR"
    ), f"Invalid PNG header: {path}"
    return struct.unpack(">II", header[16:24])


def verify_animation_metadata(
    item: ExpectedAsset,
    source: dict[str, Any],
) -> int | None:
    generated_metadata = (
        ASSET_ROOT / "textures" / "block" / f"{item.identifier}.png.mcmeta"
    )
    is_animated = item.folder == PHASE3_DYNAMIC_FOLDER
    if not is_animated:
        if phase_of(item) == 3:
            assert not item.source_animation_metadata.exists(), (
                f"Unexpected animation metadata on static phase-three asset: {item.identifier}"
            )
        assert not generated_metadata.exists(), (
            f"Unexpected generated animation metadata: {item.identifier}"
        )
        return None

    assert item.identifier in PHASE3_DYNAMIC_IDS
    assert item.source_animation_metadata.is_file(), (
        f"Missing source animation metadata: {item.identifier}"
    )
    assert generated_metadata.is_file(), (
        f"Missing generated animation metadata: {item.identifier}"
    )
    assert generated_metadata.read_bytes() == item.source_animation_metadata.read_bytes(), (
        f"Generated animation metadata is not byte-identical to its source: {item.identifier}"
    )
    payload = load_json(item.source_animation_metadata)
    assert isinstance(payload, dict) and set(payload) == {"animation"}, (
        f"Animation metadata must contain only 'animation': {item.identifier}"
    )
    animation = payload["animation"]
    assert isinstance(animation, dict), f"Animation entry is not an object: {item.identifier}"
    assert set(animation) <= {"frametime", "interpolate", "frames"}, (
        f"Unexpected animation fields in {item.identifier}: {sorted(animation)}"
    )
    assert isinstance(animation.get("frametime"), int) and not isinstance(
        animation["frametime"], bool
    ), f"Animation frametime is not an integer: {item.identifier}"
    assert animation["frametime"] == 10, (
        f"{item.identifier} must run at 2 FPS (20 ticks / frametime 10)"
    )
    assert math.isclose(20.0 / animation["frametime"], 2.0), (
        f"Unexpected effective animation rate: {item.identifier}"
    )
    if "interpolate" in animation:
        assert isinstance(animation["interpolate"], bool), (
            f"Animation interpolate must be boolean: {item.identifier}"
        )

    frame_width = int(source["resolution"]["width"])
    frame_height = int(source["resolution"]["height"])
    png_width, png_height = png_dimensions(item.source_texture)
    assert png_width == frame_width and png_height % frame_height == 0, (
        f"Animation strip dimensions do not match model frame size for {item.identifier}: "
        f"png={png_width}x{png_height}, frame={frame_width}x{frame_height}"
    )
    frame_count = png_height // frame_height
    assert frame_count == EXPECTED_ANIMATION_FRAME_COUNTS[item.identifier], (
        f"Unexpected animation frame count for {item.identifier}: {frame_count}"
    )
    frames = animation.get("frames")
    if frames is not None:
        assert isinstance(frames, list) and frames, (
            f"Animation frames must be a non-empty list: {item.identifier}"
        )
        for frame in frames:
            if isinstance(frame, dict):
                assert set(frame) in ({"index"}, {"index", "time"}), (
                    f"Unexpected animation frame fields in {item.identifier}: {frame}"
                )
                frame_index = frame["index"]
                if "time" in frame:
                    assert isinstance(frame["time"], int) and not isinstance(
                        frame["time"], bool
                    ) and frame["time"] > 0, (
                        f"Invalid animation frame time in {item.identifier}: {frame}"
                    )
            else:
                frame_index = frame
            assert isinstance(frame_index, int) and not isinstance(frame_index, bool), (
                f"Invalid animation frame entry in {item.identifier}: {frame!r}"
            )
            assert 0 <= frame_index < frame_count, (
                f"Animation frame index out of range in {item.identifier}: {frame_index}"
            )
    return frame_count


def normalized_uv(uv: list[float], width: int, height: int) -> list[float | int]:
    result = [
        rounded(float(uv[0]) * 16 / width),
        rounded(float(uv[1]) * 16 / height),
        rounded(float(uv[2]) * 16 / width),
        rounded(float(uv[3]) * 16 / height),
    ]
    assert all(-1e-6 <= float(value) <= 16.000001 for value in result), (uv, result)
    return result


def expected_element(
    source_element: dict[str, Any],
    width: int,
    height: int,
    texture_index: int,
) -> dict[str, Any]:
    assert source_element.get("type", "cube") == "cube"
    assert source_element.get("export", True) is not False
    assert source_element.get("visibility") is not False
    from_pos, to_pos = inflated_bounds(source_element)
    result: dict[str, Any] = {
        "from": [rounded(value) for value in from_pos],
        "to": [rounded(value) for value in to_pos],
        "shade": bool(source_element.get("shade", True)),
        "faces": {},
    }
    rotation = rotation_parts(source_element)
    if rotation is not None:
        axis, angle, origin = rotation
        result["rotation"] = {
            "origin": [rounded(value) for value in origin],
            "axis": axis,
            "angle": rounded(angle),
            "rescale": bool(source_element.get("rescale", False)),
        }
    for direction, face in source_element.get("faces", {}).items():
        if face is None or face.get("enabled") is False:
            continue
        assert face.get("texture") is not None
        face_texture_index = int(face["texture"])
        assert face_texture_index == texture_index
        expected_face: dict[str, Any] = {
            "uv": normalized_uv(face["uv"], width, height),
            "texture": "#0",
        }
        if "rotation" in face:
            expected_face["rotation"] = int(face["rotation"])
        if face.get("cullface"):
            expected_face["cullface"] = str(face["cullface"])
        tint = face.get("tint", face.get("tintindex"))
        if tint is not None and int(tint) >= 0:
            expected_face["tintindex"] = int(tint)
        result["faces"][direction] = expected_face
    assert result["faces"]
    return result


def expected_model(source: dict[str, Any], item: ExpectedAsset) -> dict[str, Any]:
    assert source.get("meta", {}).get("model_format") == "java_block"
    internal_name = PHASE4_INTERNAL_SOURCE_ALIASES.get(item.identifier, item.source_stem) if phase_of(item) == 4 else item.source_stem
    assert source.get("name") == internal_name
    width, height = int(source["resolution"]["width"]), int(source["resolution"]["height"])
    texture_index = referenced_texture_index(source, internal_name)
    verify_phase3_embedded_texture(source, texture_index, item)
    exported_elements = [
        element
        for element in source["elements"]
        if element.get("type", "cube") == "cube"
        and element.get("export", True) is not False
        and element.get("visibility") is not False
    ]
    result: dict[str, Any] = {
        "credit": "Crzay津仔 / Made with Blockbench",
        "ambientocclusion": bool(source.get("ambientocclusion", True)),
        "gui_light": "front" if source.get("front_gui_light", False) else "side",
        "texture_size": [width, height],
        "textures": {
            "0": f"{MOD_ID}:block/{item.identifier}",
            "particle": f"{MOD_ID}:block/{item.identifier}",
        },
        "elements": [
            expected_element(element, width, height, texture_index)
            for element in exported_elements
        ],
    }
    if "display" in source:
        result["display"] = copy.deepcopy(source["display"])
    if item.identifier in GUI_DISPLAY_OVERRIDES:
        original_gui = source.get("display", {}).get("gui", {})
        override = GUI_DISPLAY_OVERRIDES[item.identifier]
        assert set(override) == {"rotation", "translation", "scale"}
        assert override["rotation"] == original_gui.get("rotation", [0, 0, 0])
        assert override["translation"][2] == original_gui.get("translation", [0, 0, 0])[2]
        ratios = [new / old for new, old in zip(override["scale"], original_gui.get("scale", [1, 1, 1]))]
        assert all(0 < ratio < 1 for ratio in ratios) and max(ratios) - min(ratios) < 1e-7
        result.setdefault("display", {})["gui"] = copy.deepcopy(override)
    return result


def expected_blockstate(identifier: str) -> dict[str, Any]:
    model = f"{MOD_ID}:block/{identifier}"
    return {
        "variants": {
            "facing=north": {"model": model},
            "facing=east": {"model": model, "y": 90},
            "facing=south": {"model": model, "y": 180},
            "facing=west": {"model": model, "y": 270},
        }
    }


def expected_loot(identifier: str) -> dict[str, Any]:
    return {
        "type": "minecraft:block",
        "pools": [
            {
                "rolls": 1,
                "bonus_rolls": 0,
                "entries": [{"type": "minecraft:item", "name": f"{MOD_ID}:{identifier}"}],
                "conditions": [{"condition": "minecraft:survives_explosion"}],
            }
        ],
    }


def relative_file_set(root: Path) -> set[str]:
    assert root.is_dir(), f"Missing generated namespace root: {root}"
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_icon_and_metadata() -> None:
    icon = ICON_PATH.read_bytes()
    assert icon[:8] == b"\x89PNG\r\n\x1a\n", "Mod icon is not a PNG"
    assert icon[12:16] == b"IHDR", "Mod icon has no leading IHDR chunk"
    width, height = struct.unpack(">II", icon[16:24])
    assert (width, height) == (512, 512), f"Unexpected mod icon size: {width}x{height}"

    gradle_properties = GRADLE_PROPERTIES_PATH.read_text(encoding="utf-8")
    version_match = re.search(r"(?m)^mod_version\s*=\s*(\S+)\s*$", gradle_properties)
    assert version_match is not None and version_match.group(1) == MOD_VERSION, (
        f"gradle.properties mod_version is not {MOD_VERSION}"
    )

    common_main = COMMON_MAIN_PATH.read_text(encoding="utf-8")
    category_body_match = re.search(
        r"public\s+enum\s+Category\s*\{(?P<body>.*?)\;",
        common_main,
        flags=re.DOTALL,
    )
    assert category_body_match is not None, "Could not find the Category enum"
    category_pairs = re.findall(
        r"\b([A-Z][A-Z_]*)\(\"([a-z_]+)\"\)",
        category_body_match.group("body"),
    )
    assert category_pairs == [
        ("FRAME", "frame"),
        ("INDICATOR", "indicator"),
        ("POLE", "pole"),
        ("ANNEX", "annex"),
    ], f"Expected exactly four creative categories, found {category_pairs}"
    assert "for (Category category : Category.values())" in common_main
    assert "ITEM_GROUPS.register(" in common_main
    assert f"EXPECTED_CATALOG_ENTRY_COUNT = {EXPECTED_ASSET_COUNT};" in common_main
    for category, count in EXPECTED_CATEGORY_COUNTS.items():
        assert f"case {category.upper()} -> {count};" in common_main
    assert "DYNAMIC_INDICATOR" not in common_main, (
        "Animated indicators must remain in the existing indicator creative tab"
    )

    metadata = load_json(FABRIC_METADATA_PATH)
    assert metadata.get("license") == "MIT", "Fabric metadata must retain the MIT license"
    assert metadata.get("icon") == "icon.png", "fabric.mod.json does not reference the packaged icon"
    assert metadata.get("authors") == ["Crzay津仔"], "Unexpected release author metadata"
    assert metadata.get("depends", {}).get("architectury") == ">=9.0.6 <10.0.0"
    description = metadata.get("description", "")
    assert "Release credit" not in description
    assert "发布署名" not in description
    forge_metadata = FORGE_METADATA_PATH.read_text(encoding="utf-8")
    assert 'license="MIT"' in forge_metadata, "Forge metadata must retain the MIT license"
    assert 'modId="jinzai_traffic_lights"' in forge_metadata
    assert 'authors="Crzay津仔"' in forge_metadata
    assert 'logoFile="icon.png"' in forge_metadata
    assert 'modId="architectury"' in forge_metadata
    assert 'versionRange="[9.0.6,10.0.0)"' in forge_metadata
    assert "Release credit" not in forge_metadata
    assert "发布署名" not in forge_metadata


def verify_resources() -> tuple[list[ExpectedAsset], set[str], int, int, int, int]:
    assert set(GUI_DISPLAY_OVERRIDES) == EXPECTED_GUI_OVERRIDE_IDS, "Unexpected inventory GUI override IDs"
    verify_icon_and_metadata()
    items = discover_expected_assets()
    identifiers = {item.identifier for item in items}

    expected_asset_files = {
        "block_catalog.json",
        *(f"lang/{locale}.json" for locale in ALL_LOCALES),
    }
    expected_data_files = {
        "tags/blocks/frames.json",
        "tags/blocks/indicators.json",
        "tags/blocks/poles.json",
        "tags/blocks/annexes.json",
        "tags/blocks/all_blocks.json",
    }
    for item in items:
        identifier = item.identifier
        expected_asset_files.update(
            {
                f"models/block/{identifier}.json",
                f"models/item/{identifier}.json",
                f"blockstates/{identifier}.json",
                f"textures/block/{identifier}.png",
            }
        )
        if item.folder == PHASE3_DYNAMIC_FOLDER:
            expected_asset_files.add(f"textures/block/{identifier}.png.mcmeta")
        expected_data_files.add(f"loot_tables/blocks/{identifier}.json")
    assert len(expected_asset_files) == 965, (
        f"Unexpected generated asset-file expectation count: {len(expected_asset_files)}"
    )
    assert len(expected_data_files) == 239, (
        f"Unexpected generated data-file expectation count: {len(expected_data_files)}"
    )
    assert relative_file_set(ASSET_ROOT) == expected_asset_files, (
        f"Generated asset file set is not exactly {EXPECTED_ASSET_COUNT} chains"
    )
    assert relative_file_set(DATA_ROOT) == expected_data_files, (
        f"Generated data file set is not exactly {EXPECTED_ASSET_COUNT} chains"
    )

    translations = {
        locale: load_json(ASSET_ROOT / "lang" / f"{locale}.json")
        for locale in ALL_LOCALES
    }
    zh_cn = translations["zh_cn"]
    en_us = translations["en_us"]
    zh_block_keys = {key for key in zh_cn if key.startswith(f"block.{MOD_ID}.")}
    en_block_keys = {key for key in en_us if key.startswith(f"block.{MOD_ID}.")}
    expected_block_keys = {f"block.{MOD_ID}.{identifier}" for identifier in identifiers}
    assert zh_block_keys == en_block_keys == expected_block_keys
    expected_shared_keys = {
        f"itemGroup.{MOD_ID}.frame",
        f"itemGroup.{MOD_ID}.indicator",
        f"itemGroup.{MOD_ID}.pole",
        f"itemGroup.{MOD_ID}.annex",
    }
    expected_language_keys = expected_block_keys | expected_shared_keys
    assert len(expected_language_keys) == EXPECTED_LANGUAGE_KEY_COUNT, (
        f"Unexpected language key count: {len(expected_language_keys)}"
    )
    assert all(
        set(values) == expected_language_keys for values in translations.values()
    ), "At least one language key set is incomplete"
    for locale, values in translations.items():
        item_group_keys = {
            key for key in values if key.startswith(f"itemGroup.{MOD_ID}.")
        }
        assert item_group_keys == expected_shared_keys, (
            f"{locale} must expose exactly the four established creative tabs"
        )
        assert all(
            isinstance(value, str) and value.strip() for value in values.values()
        ), f"Blank or non-string translation in {locale}"

    phase1_items = [item for item in items if item.folder in PHASE1_SOURCE_FOLDERS]
    phase2_items = [item for item in items if item.folder in PHASE2_SOURCE_FOLDERS]
    phase3_items = [item for item in items if item.folder in PHASE3_SOURCE_FOLDERS]
    phase4_items = [item for item in items if item.folder in PHASE4_SOURCE_FOLDERS]
    assert len(phase1_items) == 103 and len(phase2_items) == 58 and len(phase3_items) == 52
    assert len(phase4_items) == 21
    assert len(phase1_items) + len(phase2_items) + len(phase3_items) + len(phase4_items) == len(items)
    phase1_shared_keys = expected_shared_keys - {f"itemGroup.{MOD_ID}.annex"}
    expected_phase1_language_keys = (
        {f"block.{MOD_ID}.{item.identifier}" for item in phase1_items}
        | phase1_shared_keys
    )
    assert len(expected_phase1_language_keys) == 106
    expected_phase2_language_keys = {
        f"block.{MOD_ID}.{item.identifier}" for item in phase2_items
    } | {f"itemGroup.{MOD_ID}.annex"}
    assert len(expected_phase2_language_keys) == 59
    expected_phase3_language_keys = {
        f"block.{MOD_ID}.{item.identifier}" for item in phase3_items
    }
    assert len(expected_phase3_language_keys) == 52
    phase2_locale_sources = phase2_translation_locales(phase2_items)
    phase3_locale_sources = phase3_translation_locales(phase3_items)
    phase4_locale_sources = phase3_translation_locales(phase4_items, PHASE4_TRANSLATION_SOURCE)
    for locale in EXTRA_LOCALES:
        raw_phase1_source = load_json(TRANSLATION_SOURCE_ROOT / f"{locale}.json")
        assert isinstance(raw_phase1_source, dict)
        phase1_source = {
            key: value
            for key, value in raw_phase1_source.items()
            if not key.startswith(f"tooltip.{MOD_ID}.")
        }
        assert set(phase1_source) == expected_phase1_language_keys, (
            f"Phase-one translation source key mismatch for {locale}"
        )
        phase2_source = expected_phase2_locale_values(
            locale,
            phase2_locale_sources[locale],
            phase2_items,
        )
        assert not (set(phase1_source) & set(phase2_source)), (
            f"Phase-one and phase-two translation sources overlap for {locale}"
        )
        assert set(phase2_source) == expected_phase2_language_keys
        phase3_source = expected_expansion_locale_values(
            locale,
            phase3_locale_sources[locale],
            phase3_items,
        )
        assert set(phase3_source) == expected_phase3_language_keys
        assert not (set(phase1_source) & set(phase3_source))
        assert not (set(phase2_source) & set(phase3_source))
        phase4_source = expected_expansion_locale_values(locale, phase4_locale_sources[locale], phase4_items)
        assert not (set(phase4_source) & (set(phase1_source) | set(phase2_source) | set(phase3_source)))
        source = {**phase1_source, **phase2_source, **phase3_source, **phase4_source}
        assert set(source) == expected_language_keys
        assert translations[locale] == source, (
            f"Generated {locale} differs from its merged phase-one/phase-two/phase-three sources"
        )
        changed_from_english = sum(
            source[key] != en_us[key] for key in expected_language_keys
        )
        assert changed_from_english >= 90, (
            f"{locale} appears insufficiently translated: only "
            f"{changed_from_english}/{len(expected_language_keys)} values differ from English"
        )
        assert not any(
            marker in value for value in source.values()
            for marker in ("TODO", "???", "[保持原名]")
        ), f"Placeholder text remains in {locale}"
    expected_shared_values = {
        f"itemGroup.{MOD_ID}.frame": ("红绿灯框架", "Traffic Light Frames"),
        f"itemGroup.{MOD_ID}.indicator": ("指示灯", "Traffic Light Indicators"),
        f"itemGroup.{MOD_ID}.pole": ("杆子", "Traffic Light Poles"),
        f"itemGroup.{MOD_ID}.annex": ("交通灯附属", "Traffic Light Accessories"),
    }
    for key, (expected_zh, expected_en) in expected_shared_values.items():
        assert zh_cn[key] == expected_zh and en_us[key] == expected_en, f"Shared translation mismatch: {key}"

    catalog = load_json(ASSET_ROOT / "block_catalog.json")
    assert set(catalog) == {"schema", "blocks"} and catalog["schema"] == 1
    assert isinstance(catalog["blocks"], list) and len(catalog["blocks"]) == EXPECTED_ASSET_COUNT
    catalog_by_source: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in catalog["blocks"]:
        assert set(entry) == {"id", "category", "source_folder", "source_stem", "collision_boxes"}
        key = (entry["source_folder"], entry["source_stem"])
        assert key not in catalog_by_source, f"Duplicate catalog source: {key}"
        catalog_by_source[key] = entry
    assert set(catalog_by_source) == {(item.folder, item.source_stem) for item in items}
    assert {entry["id"] for entry in catalog["blocks"]} == identifiers

    total_source_elements = 0
    total_exported_elements = 0
    total_collision_boxes = 0
    phase3_collision_boxes = 0
    phase3_pole_collision_boxes = 0
    excluded_hidden_elements: list[tuple[str, int]] = []
    simplified_collision_ids: set[str] = set()
    phase3_enclosing_ids: set[str] = set()
    phase3_pole_ids: set[str] = set()
    phase4_enclosing_ids: set[str] = set()
    animation_frame_counts: dict[str, int] = {}
    for item in items:
        item_phase = phase_of(item)
        source = load_json(item.source_model)
        source_elements = source.get("elements", [])
        exported_source_elements = [
            element
            for element in source_elements
            if element.get("type", "cube") == "cube"
            and element.get("export", True) is not False
            and element.get("visibility") is not False
        ]
        total_source_elements += len(source_elements)
        total_exported_elements += len(exported_source_elements)
        excluded_hidden_elements.extend(
            (item.source_stem, index)
            for index, element in enumerate(source_elements)
            if element.get("visibility") is False
        )

        block_model = load_json(ASSET_ROOT / "models" / "block" / f"{item.identifier}.json")
        assert block_model == expected_model(source, item), f"Model conversion mismatch: {item.identifier}"
        assert len(block_model["elements"]) == len(exported_source_elements)
        for element in block_model["elements"]:
            for face in element["faces"].values():
                assert face["texture"] == "#0"
                assert all(-1e-6 <= float(value) <= 16.000001 for value in face["uv"])

        texture = ASSET_ROOT / "textures" / "block" / f"{item.identifier}.png"
        assert sha256(texture) == sha256(item.source_texture), f"Texture hash mismatch: {item.identifier}"
        frame_count = verify_animation_metadata(item, source)
        if frame_count is not None:
            animation_frame_counts[item.identifier] = frame_count
        assert load_json(ASSET_ROOT / "models" / "item" / f"{item.identifier}.json") == {
            "parent": f"{MOD_ID}:block/{item.identifier}"
        }
        assert load_json(ASSET_ROOT / "blockstates" / f"{item.identifier}.json") == expected_blockstate(
            item.identifier
        )
        assert load_json(DATA_ROOT / "loot_tables" / "blocks" / f"{item.identifier}.json") == expected_loot(
            item.identifier
        )
        key = f"block.{MOD_ID}.{item.identifier}"
        assert zh_cn[key] == item.zh_cn, f"Chinese name does not match source: {item.identifier}"
        assert isinstance(en_us[key], str) and en_us[key].strip(), f"Missing English name: {item.identifier}"
        if item.en_us is not None:
            assert en_us[key] == item.en_us, (
                f"English name does not match phase-three source: {item.identifier}"
            )
        entry = catalog_by_source[(item.folder, item.source_stem)]
        assert entry["id"] == item.identifier and entry["category"] == item.category
        maximum_rotated_cell_size = 1.0
        if item_phase == 3 and item.category == "pole":
            maximum_rotated_cell_size = (
                3.0 if item.identifier in PHASE3_LONG_DIAGONAL_POLE_IDS else 2.0
            )
        precise_boxes = [
            box
            for element in exported_source_elements
            for box in expected_collision_boxes(element, maximum_rotated_cell_size)
        ]
        use_enclosing_box = (
            item.identifier in SIMPLIFIED_BOUNDING_COLLISION_IDS
            or item.identifier in PHASE4_MODIFIED_MODEL_IDS
            or item_phase == 4
            or (item_phase == 3 and item.category != "pole")
        )
        if use_enclosing_box:
            if item.identifier in SIMPLIFIED_BOUNDING_COLLISION_IDS:
                assert len(precise_boxes) == EXPECTED_PRECISE_COLLISION_COUNTS[item.identifier], (
                    f"Unexpected precise collision complexity for {item.identifier}"
                )
            expected_boxes = expected_enclosing_collision_box(precise_boxes)
            rotated_box = expected_boxes[0]
            for _ in range(4):
                rotated_box = rotate_catalog_box_clockwise(rotated_box)
                assert all(
                    float(rotated_box[index]) < float(rotated_box[index + 3])
                    for index in range(3)
                ), f"Rotated enclosing box is invalid: {item.identifier}"
            assert rotated_box == expected_boxes[0], (
                f"Four rotations did not restore the enclosing box: {item.identifier}"
            )
            if item.identifier in SIMPLIFIED_BOUNDING_COLLISION_IDS:
                simplified_collision_ids.add(item.identifier)
            if item_phase == 3:
                assert len(expected_boxes) == 1
                phase3_enclosing_ids.add(item.identifier)
            if item_phase == 4 or item.identifier in PHASE4_MODIFIED_MODEL_IDS:
                assert len(expected_boxes) == 1
                phase4_enclosing_ids.add(item.identifier)
        else:
            expected_boxes = precise_boxes
        assert entry["collision_boxes"] == expected_boxes, f"Collision AABB mismatch: {item.identifier}"
        total_collision_boxes += len(entry["collision_boxes"])
        if item_phase == 3:
            phase3_collision_boxes += len(entry["collision_boxes"])
            if item.category == "pole":
                phase3_pole_ids.add(item.identifier)
                phase3_pole_collision_boxes += len(entry["collision_boxes"])
        for box in entry["collision_boxes"]:
            assert isinstance(box, list) and len(box) == 6
            assert all(isinstance(value, (int, float)) for value in box)
            assert all(math.isfinite(float(value)) for value in box)
            assert all(float(box[index]) < float(box[index + 3]) for index in range(3)), (
                f"Non-positive collision box in {item.identifier}: {box}"
            )

    assert total_source_elements == EXPECTED_SOURCE_ELEMENT_COUNT, (
        f"Unexpected raw source cube count: {total_source_elements}"
    )
    assert set(excluded_hidden_elements) == {
        ("jinzai_traffic_indicator_3a", 0),
        ("jinzai_traffic_indicator_4", 0),
        ("jinzai_dynamic_light_11", 0),
    }, f"Unexpected hidden placeholders: {excluded_hidden_elements}"
    assert total_exported_elements == EXPECTED_VISIBLE_ELEMENT_COUNT, (
        f"Unexpected visible source element count: {total_exported_elements}"
    )
    assert total_collision_boxes == EXPECTED_COLLISION_BOX_COUNT, (
        f"Unexpected collision box count: {total_collision_boxes}"
    )
    assert simplified_collision_ids == set(SIMPLIFIED_BOUNDING_COLLISION_IDS), (
        f"Unexpected simplified-collision IDs: {sorted(simplified_collision_ids)}"
    )
    assert animation_frame_counts == EXPECTED_ANIMATION_FRAME_COUNTS, (
        f"Unexpected animated texture inventory/frame counts: {animation_frame_counts}"
    )
    assert len(animation_frame_counts) == EXPECTED_ANIMATION_METADATA_COUNT
    assert len(phase3_enclosing_ids) == 28, (
        f"Expected all 28 non-pole phase-three models to use one enclosing box: "
        f"{sorted(phase3_enclosing_ids)}"
    )
    assert len(phase3_pole_ids) == 24
    assert phase4_enclosing_ids == ({item.identifier for item in phase4_items} | PHASE4_MODIFIED_MODEL_IDS), (
        "All 21 new and three replaced phase-four models must use one placed-volume bounding box"
    )
    assert PHASE3_LONG_DIAGONAL_POLE_IDS <= phase3_pole_ids
    assert phase3_pole_collision_boxes == EXPECTED_PHASE3_POLE_COLLISION_BOX_COUNT, (
        f"Unexpected phase-three pole collision count: {phase3_pole_collision_boxes}"
    )
    assert phase3_collision_boxes == EXPECTED_PHASE3_COLLISION_BOX_COUNT, (
        f"Unexpected phase-three collision count: {phase3_collision_boxes}"
    )
    assert total_collision_boxes == sum(
        len(entry["collision_boxes"]) for entry in catalog["blocks"]
    ), "Accumulated collision box count is inconsistent"

    by_category = {
        category: sorted(f"{MOD_ID}:{item.identifier}" for item in items if item.category == category)
        for category in CATEGORIES
    }
    tag_names = {
        "frame": "frames",
        "indicator": "indicators",
        "pole": "poles",
        "annex": "annexes",
    }
    for category, values in by_category.items():
        tag = load_json(DATA_ROOT / "tags" / "blocks" / f"{tag_names[category]}.json")
        assert tag == {"replace": False, "values": values}, f"Incorrect {category} tag"
    all_tag = load_json(DATA_ROOT / "tags" / "blocks" / "all_blocks.json")
    assert all_tag == {"replace": False, "values": sorted(value for values in by_category.values() for value in values)}

    return (
        items,
        expected_asset_files | {f"../data/{MOD_ID}/{path}" for path in expected_data_files},
        total_source_elements,
        total_exported_elements,
        len(excluded_hidden_elements),
        total_collision_boxes,
    )


def verify_jar(jar_path: Path) -> None:
    assert jar_path.is_file(), f"JAR not found: {jar_path}"
    local_files = [path for root in (ASSET_ROOT, DATA_ROOT) for path in root.rglob("*") if path.is_file()]
    expected_entries = {
        path.relative_to(RESOURCE_ROOT).as_posix(): path
        for path in local_files
    }
    with zipfile.ZipFile(jar_path) as archive:
        archive_file_list = [name for name in archive.namelist() if not name.endswith("/")]
        assert len(archive_file_list) == len(set(archive_file_list)), (
            "JAR contains duplicate file entries"
        )
        archive_files = set(archive_file_list)
        expected_animation_entries = {
            f"assets/{MOD_ID}/textures/block/{identifier}.png.mcmeta"
            for identifier in PHASE3_DYNAMIC_IDS
        }
        packed_animation_entries = {
            name
            for name in archive_files
            if name.startswith(f"assets/{MOD_ID}/textures/block/")
            and name.endswith(".png.mcmeta")
        }
        assert packed_animation_entries == expected_animation_entries, (
            "JAR must contain exactly the 15 phase-three animation metadata files: "
            f"missing={sorted(expected_animation_entries - packed_animation_entries)}, "
            f"extra={sorted(packed_animation_entries - expected_animation_entries)}"
        )
        assert not any("daynamic" in name for name in archive_files), (
            "JAR contains the obsolete 'daynamic' spelling"
        )
        assert "icon.png" in archive_files, "JAR does not contain icon.png"
        assert archive.read("icon.png") == ICON_PATH.read_bytes(), "JAR icon differs from verified source icon"
        has_fabric_metadata = "fabric.mod.json" in archive_files
        has_forge_metadata = "META-INF/mods.toml" in archive_files
        assert has_fabric_metadata != has_forge_metadata, (
            "JAR must contain exactly one loader metadata file (fabric.mod.json or META-INF/mods.toml)"
        )
        if has_fabric_metadata:
            packed_metadata = json.loads(archive.read("fabric.mod.json").decode("utf-8"))
            assert packed_metadata.get("id") == MOD_ID, "Packaged Fabric mod ID is incorrect"
            assert packed_metadata.get("version") == MOD_VERSION, (
                f"Packaged Fabric mod version is not {MOD_VERSION}"
            )
            assert packed_metadata.get("icon") == "icon.png", "Packaged Fabric metadata does not reference icon.png"
            assert packed_metadata.get("authors") == ["Crzay津仔"], "Unexpected packaged Fabric author metadata"
            assert packed_metadata.get("depends", {}).get("minecraft") == "1.20.1"
            assert packed_metadata.get("depends", {}).get("java") == ">=17"
            assert packed_metadata.get("depends", {}).get("architectury") == ">=9.0.6 <10.0.0"
            description = packed_metadata.get("description", "")
            assert "Release credit" not in description
            assert "发布署名" not in description
        else:
            packed_metadata = archive.read("META-INF/mods.toml").decode("utf-8")
            assert f'modId="{MOD_ID}"' in packed_metadata, "Packaged Forge mod ID is incorrect"
            assert f'version="{MOD_VERSION}"' in packed_metadata, (
                f"Packaged Forge mod version is not {MOD_VERSION}"
            )
            assert 'authors="Crzay津仔"' in packed_metadata, "Unexpected packaged Forge author metadata"
            assert 'logoFile="icon.png"' in packed_metadata, "Packaged Forge metadata does not reference icon.png"
            assert 'modId="minecraft"' in packed_metadata and 'versionRange="[1.20.1,1.20.2)"' in packed_metadata
            assert 'modId="architectury"' in packed_metadata and 'versionRange="[9.0.6,10.0.0)"' in packed_metadata
            assert "Release credit" not in packed_metadata
            assert "发布署名" not in packed_metadata
        manifest = archive.read("META-INF/MANIFEST.MF").decode("utf-8")
        assert f"Implementation-Version: {MOD_VERSION}" in manifest, (
            f"Packaged manifest Implementation-Version is not {MOD_VERSION}"
        )
        own_classes = {
            name: archive.read(name)
            for name in archive_files
            if name.startswith("cn/crazyjinzai/trafficlights/") and name.endswith(".class")
        }
        assert own_classes, "JAR does not contain any traffic-light implementation classes"
        for name, class_bytes in own_classes.items():
            assert class_bytes[:4] == b"\xca\xfe\xba\xbe", f"Invalid class header: {name}"
            major = struct.unpack(">H", class_bytes[6:8])[0]
            assert major == 61, f"Class is not Java 17 bytecode (major 61): {name} -> {major}"
            assert b"tooltip." not in class_bytes, f"Tooltip constant remains in class: {name}"
        namespace_entries = {
            name
            for name in archive_files
            if name.startswith(f"assets/{MOD_ID}/") or name.startswith(f"data/{MOD_ID}/")
        }
        assert namespace_entries == set(expected_entries), (
            f"JAR namespace differs from verified resources: missing={sorted(set(expected_entries) - namespace_entries)}, "
            f"extra={sorted(namespace_entries - set(expected_entries))}"
        )
        for entry, local_path in expected_entries.items():
            assert archive.read(entry) == local_path.read_bytes(), f"JAR entry differs from verified file: {entry}"


def verify_phase4_baseline(baseline_path: Path) -> None:
    """Protect every old ID/name/resource except the explicitly supplied replacements."""
    catalog_path = f"assets/{MOD_ID}/block_catalog.json"
    with zipfile.ZipFile(baseline_path) as baseline:
        if "fabric.mod.json" in baseline.namelist():
            metadata = json.loads(baseline.read("fabric.mod.json"))
            assert metadata["id"] == MOD_ID and metadata["version"] == "2.0.41"
        else:
            metadata = baseline.read("META-INF/mods.toml").decode("utf-8")
            assert f'modId="{MOD_ID}"' in metadata and 'version="2.0.41"' in metadata
        old_catalog = json.loads(baseline.read(catalog_path))
        current_catalog = load_json(RESOURCE_ROOT / catalog_path)
        old_by_id = {entry["id"]: entry for entry in old_catalog["blocks"]}
        current_by_id = {entry["id"]: entry for entry in current_catalog["blocks"]}
        new_ids = {item.identifier for item in discover_phase4_assets()}
        assert len(old_by_id) == 213 and len(current_by_id) == 234
        assert set(current_by_id) == set(old_by_id) | new_ids and not (set(old_by_id) & new_ids)
        for identifier, old_entry in old_by_id.items():
            current_entry = current_by_id[identifier]
            fields = set(old_entry) - ({"collision_boxes"} if identifier in PHASE4_MODIFIED_MODEL_IDS else set())
            assert all(old_entry[key] == current_entry[key] for key in fields), (
                f"Existing catalog entry changed outside the phase-four request: {identifier}"
            )

        language_paths = {f"assets/{MOD_ID}/lang/{locale}.json" for locale in ALL_LOCALES}
        for path in language_paths:
            old_values = json.loads(baseline.read(path))
            current_values = load_json(RESOURCE_ROOT / path)
            assert len(old_values) == 217 and len(current_values) == 238
            assert all(current_values.get(key) == value for key, value in old_values.items()), (
                f"Existing localized name changed: {path}"
            )

        expected_changes = {
            *(f"assets/{MOD_ID}/models/block/{identifier}.json" for identifier in PHASE4_MODIFIED_MODEL_IDS),
            *(f"assets/{MOD_ID}/models/block/{identifier}.json" for identifier in GUI_DISPLAY_OVERRIDES),
            f"assets/{MOD_ID}/textures/block/jinzai_traffic_light_c5.png",
            f"assets/{MOD_ID}/textures/block/jinzai_dynamic_light_1.png.mcmeta",
            f"assets/{MOD_ID}/textures/block/jinzai_dynamic_light_2.png.mcmeta",
        }
        tag_paths = {f"data/{MOD_ID}/tags/blocks/{name}.json" for name in ("all_blocks", "frames", "indicators", "poles", "annexes")}
        old_paths = {name for name in baseline.namelist()
                     if name.startswith((f"assets/{MOD_ID}/", f"data/{MOD_ID}/")) and not name.endswith("/")}
        current_paths = ({f"assets/{MOD_ID}/{name}" for name in relative_file_set(ASSET_ROOT)}
                         | {f"data/{MOD_ID}/{name}" for name in relative_file_set(DATA_ROOT)})
        added_paths = set()
        for identifier in new_ids:
            added_paths.update({
                f"assets/{MOD_ID}/models/block/{identifier}.json",
                f"assets/{MOD_ID}/models/item/{identifier}.json",
                f"assets/{MOD_ID}/blockstates/{identifier}.json",
                f"assets/{MOD_ID}/textures/block/{identifier}.png",
                f"data/{MOD_ID}/loot_tables/blocks/{identifier}.json",
            })
        assert current_paths == old_paths | added_paths, "Unexpected added or removed runtime resource"
        excluded_paths = language_paths | tag_paths | {catalog_path}
        changed_paths = {path for path in old_paths - excluded_paths
                         if baseline.read(path) != (RESOURCE_ROOT / path).read_bytes()}
        assert changed_paths == expected_changes, (
            f"Unexpected old-resource delta: {sorted(changed_paths ^ expected_changes)}"
        )
        for identifier in GUI_DISPLAY_OVERRIDES:
            path = f"assets/{MOD_ID}/models/block/{identifier}.json"
            old_model = json.loads(baseline.read(path))
            current_model = load_json(RESOURCE_ROOT / path)
            assert current_model.get("display", {}).get("gui") == GUI_DISPLAY_OVERRIDES[identifier]
            for model in (old_model, current_model):
                model.setdefault("display", {}).pop("gui", None)
                if not model["display"]:
                    model.pop("display")
            assert old_model == current_model, f"GUI repair changed placed model or other display transforms: {identifier}"
    print("Verified 2.0.41 compatibility: all 213 old IDs/names retained; six requested resource changes and 26 strictly GUI-only icon repairs.")


def main() -> None:
    global WORKBOOK_ROOT
    parser = argparse.ArgumentParser(
        description=f"Verify all {EXPECTED_ASSET_COUNT} generated traffic-light resource chains."
    )
    parser.add_argument("jar", nargs="?", type=Path, help="Optional built JAR to verify byte-for-byte")
    parser.add_argument("--baseline", type=Path, help="Optional 2.0.41 release JAR for phase-four compatibility checks")
    parser.add_argument(
        "--private-input-root", type=Path, default=ROOT,
        help="Private project root containing the original naming workbooks.",
    )
    args = parser.parse_args()
    WORKBOOK_ROOT = args.private_input_root.resolve()

    (
        items,
        _,
        total_source_elements,
        total_exported_elements,
        excluded_count,
        total_collision_boxes,
    ) = verify_resources()
    if args.baseline is not None:
        verify_phase4_baseline(args.baseline.resolve())
    if args.jar is not None:
        verify_jar(args.jar.resolve())
    suffix = f" and JAR {args.jar}" if args.jar is not None else ""
    print(
        f"Verified {len(items)} source/catalog/resource chains, "
        f"{total_exported_elements} visible source/model elements and {total_collision_boxes} collision boxes "
        f"({excluded_count} hidden placeholders excluded from {total_source_elements} raw cubes), "
        f"{EXPECTED_ANIMATION_METADATA_COUNT} synchronized 2 FPS animated textures, "
        f"{len(ALL_LOCALES)} complete languages with exactly four creative tabs, "
        f"a verified 512x512 mod icon, "
        f"texture SHA-256 equality{suffix}."
    )


if __name__ == "__main__":
    main()
