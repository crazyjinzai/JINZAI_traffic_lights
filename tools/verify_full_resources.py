"""本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。"""

from __future__ import annotations

import argparse
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
MOD_ID = "jinzai_traffic_lights"
RESOURCE_ROOT = ROOT / "src" / "main" / "resources"
ASSET_ROOT = RESOURCE_ROOT / "assets" / MOD_ID
DATA_ROOT = RESOURCE_ROOT / "data" / MOD_ID
ICON_PATH = RESOURCE_ROOT / "icon.png"
TRANSLATION_SOURCE_ROOT = ROOT / "tools" / "translations"
PHASE2_TRANSLATION_SOURCE = TRANSLATION_SOURCE_ROOT / "phase2_names.json"
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

CATEGORIES = ("frame", "indicator", "pole", "annex")
EXPECTED_CATEGORY_COUNTS = {
    "frame": 48,
    "indicator": 55,
    "pole": 48,
    "annex": 10,
}
EXPECTED_ASSET_COUNT = 161
EXPECTED_LANGUAGE_KEY_COUNT = 331
EXPECTED_SOURCE_ELEMENT_COUNT = 2555
EXPECTED_VISIBLE_ELEMENT_COUNT = 2553
EXPECTED_COLLISION_BOX_COUNT = 3206

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

    @property
    def source_model(self) -> Path:
        return ROOT / self.folder / f"{self.source_stem}.bbmodel"

    @property
    def source_texture(self) -> Path:
        return ROOT / self.folder / f"{self.source_stem}.png"


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
        for row in read_xlsx_rows(ROOT / folder / workbook)[1:]:
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

    indicator_rows = read_xlsx_rows(ROOT / "指示灯" / SOURCE_FOLDERS["指示灯"][1])
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
        ROOT / "指示灯（新增）" / SOURCE_FOLDERS["指示灯（新增）"][1]
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
        "category_tooltip_annex",
        "description_templates",
    }
    assert isinstance(locale_source, dict) and set(locale_source) == expected_fields, (
        f"Unexpected phase-two locale fields for {locale}"
    )
    expected_ids = {item.identifier for item in phase2_items}
    names = locale_source["names"]
    assert isinstance(names, dict) and set(names) == expected_ids, (
        f"Phase-two name identifier mismatch for {locale}"
    )
    templates = locale_source["description_templates"]
    assert isinstance(templates, dict) and set(templates) == set(CATEGORIES), (
        f"Phase-two description template mismatch for {locale}"
    )

    values: dict[str, str] = {
        f"itemGroup.{MOD_ID}.annex": locale_source["item_group_annex"],
        f"tooltip.{MOD_ID}.category.annex": locale_source["category_tooltip_annex"],
    }
    for item in phase2_items:
        name = names[item.identifier]
        template = templates[item.category]
        assert isinstance(name, str) and name.strip(), (
            f"Blank phase-two name for {locale}: {item.identifier}"
        )
        assert isinstance(template, str) and template.strip() and "{name}" in template, (
            f"Invalid {item.category} description template for {locale}: {template!r}"
        )
        try:
            description = template.format(name=name)
        except (KeyError, ValueError) as exc:
            raise AssertionError(
                f"Cannot format {item.category} description template for {locale}: {exc}"
            ) from exc
        values[f"block.{MOD_ID}.{item.identifier}"] = name
        values[f"tooltip.{MOD_ID}.{item.identifier}.description"] = description

    assert len(values) == len(phase2_items) * 2 + 2 == 118
    assert all(isinstance(value, str) and value.strip() for value in values.values()), (
        f"Blank phase-two translation value for {locale}"
    )
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


def unit_intervals(start: float, end: float) -> list[tuple[float, float]]:
    length = end - start
    assert length > 0, f"Non-positive source interval: {start}..{end}"
    count = max(1, math.ceil(length - 1e-9))
    step = length / count
    intervals = [
        (start + step * index, end if index + 1 == count else start + step * (index + 1))
        for index in range(count)
    ]
    assert all(0 < high - low <= 1.000000001 for low, high in intervals)
    return intervals


def expected_collision_boxes(element: dict[str, Any]) -> list[list[float | int]]:
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
        unit_intervals(from_pos[first_axis], to_pos[first_axis]),
        unit_intervals(from_pos[second_axis], to_pos[second_axis]),
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
    assert source.get("name") == item.source_stem
    width, height = int(source["resolution"]["width"]), int(source["resolution"]["height"])
    texture_index = referenced_texture_index(source, item.source_stem)
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
        result["display"] = source["display"]
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

    metadata = load_json(RESOURCE_ROOT / "fabric.mod.json")
    assert metadata.get("icon") == "icon.png", "fabric.mod.json does not reference the packaged icon"
    assert metadata.get("authors") == ["Crzay津仔"], "Unexpected release author metadata"
    description = metadata.get("description", "")
    assert "Release credit" not in description
    assert "发布署名" not in description


def verify_resources() -> tuple[list[ExpectedAsset], set[str], int, int, int, int]:
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
    for identifier in identifiers:
        expected_asset_files.update(
            {
                f"models/block/{identifier}.json",
                f"models/item/{identifier}.json",
                f"blockstates/{identifier}.json",
                f"textures/block/{identifier}.png",
            }
        )
        expected_data_files.add(f"loot_tables/blocks/{identifier}.json")
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
    expected_description_keys = {
        f"tooltip.{MOD_ID}.{identifier}.description" for identifier in identifiers
    }
    expected_shared_keys = {
        f"itemGroup.{MOD_ID}.frame",
        f"itemGroup.{MOD_ID}.indicator",
        f"itemGroup.{MOD_ID}.pole",
        f"itemGroup.{MOD_ID}.annex",
        f"tooltip.{MOD_ID}.category.frame",
        f"tooltip.{MOD_ID}.category.indicator",
        f"tooltip.{MOD_ID}.category.pole",
        f"tooltip.{MOD_ID}.category.annex",
        f"tooltip.{MOD_ID}.indicator.automation_limit",
    }
    expected_language_keys = expected_block_keys | expected_description_keys | expected_shared_keys
    assert len(expected_language_keys) == EXPECTED_LANGUAGE_KEY_COUNT, (
        f"Unexpected language key count: {len(expected_language_keys)}"
    )
    assert all(
        set(values) == expected_language_keys for values in translations.values()
    ), "At least one language key set is incomplete"
    for locale, values in translations.items():
        assert all(
            isinstance(value, str) and value.strip() for value in values.values()
        ), f"Blank or non-string translation in {locale}"

    phase1_items = [item for item in items if item.folder in PHASE1_SOURCE_FOLDERS]
    phase2_items = [item for item in items if item.folder not in PHASE1_SOURCE_FOLDERS]
    assert len(phase1_items) == 103 and len(phase2_items) == 58
    phase1_shared_keys = expected_shared_keys - {
        f"itemGroup.{MOD_ID}.annex",
        f"tooltip.{MOD_ID}.category.annex",
    }
    expected_phase1_language_keys = (
        {f"block.{MOD_ID}.{item.identifier}" for item in phase1_items}
        | {f"tooltip.{MOD_ID}.{item.identifier}.description" for item in phase1_items}
        | phase1_shared_keys
    )
    assert len(expected_phase1_language_keys) == 213
    phase2_locale_sources = phase2_translation_locales(phase2_items)
    for locale in EXTRA_LOCALES:
        phase1_source = load_json(TRANSLATION_SOURCE_ROOT / f"{locale}.json")
        assert isinstance(phase1_source, dict) and set(phase1_source) == expected_phase1_language_keys, (
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
        source = {**phase1_source, **phase2_source}
        assert set(source) == expected_language_keys
        assert translations[locale] == source, (
            f"Generated {locale} differs from its merged phase-one/phase-two translation sources"
        )
        changed_from_english = sum(
            source[key] != en_us[key] for key in expected_language_keys
        )
        assert changed_from_english >= 200, (
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
        f"tooltip.{MOD_ID}.category.frame": (
            "支持四向放置，碰撞箱与模型对齐。",
            "Supports four horizontal orientations with model-aligned collision.",
        ),
        f"tooltip.{MOD_ID}.category.indicator": (
            "静态发光，无实体碰撞，可被玩家和实体穿过。",
            "Always lit with no physical collision; players and entities can pass through.",
        ),
        f"tooltip.{MOD_ID}.category.pole": (
            "支持四向放置，精细碰撞箱与模型对齐。",
            "Supports four horizontal orientations with precise model-aligned collision.",
        ),
        f"tooltip.{MOD_ID}.category.annex": (
            "静态发光，无实体碰撞，可被玩家和实体穿过。",
            "Always lit with no physical collision; players and entities can pass through.",
        ),
        f"tooltip.{MOD_ID}.indicator.automation_limit": (
            "不含倒计时、自动切灯或红石控制。",
            "No countdown, automatic cycling, or redstone control.",
        ),
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
    excluded_hidden_elements: list[tuple[str, int]] = []
    simplified_collision_ids: set[str] = set()
    for item in items:
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
        assert zh_cn[key] == item.zh_cn, f"Chinese name does not match XLSX: {item.identifier}"
        assert isinstance(en_us[key], str) and en_us[key].strip(), f"Missing English name: {item.identifier}"
        description_key = f"tooltip.{MOD_ID}.{item.identifier}.description"
        zh_prefix, en_prefix = {
            "frame": ("红绿灯框架装饰部件：", "Decorative traffic-light frame component: "),
            "indicator": ("静态发光指示灯：", "Static illuminated traffic signal: "),
            "pole": ("交通灯杆件装饰部件：", "Decorative traffic-light pole component: "),
            "annex": ("交通灯附属装饰部件：", "Decorative traffic-light accessory: "),
        }[item.category]
        assert zh_cn[description_key] == f"{zh_prefix}{zh_cn[key]}。", f"Chinese tooltip mismatch: {item.identifier}"
        assert en_us[description_key] == f"{en_prefix}{en_us[key]}.", f"English tooltip mismatch: {item.identifier}"

        entry = catalog_by_source[(item.folder, item.source_stem)]
        assert entry["id"] == item.identifier and entry["category"] == item.category
        precise_boxes = [
            box
            for element in exported_source_elements
            for box in expected_collision_boxes(element)
        ]
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
            simplified_collision_ids.add(item.identifier)
        else:
            expected_boxes = precise_boxes
        assert entry["collision_boxes"] == expected_boxes, f"Collision AABB mismatch: {item.identifier}"
        total_collision_boxes += len(entry["collision_boxes"])
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
        archive_files = {name for name in archive.namelist() if not name.endswith("/")}
        assert "icon.png" in archive_files, "JAR does not contain icon.png"
        assert archive.read("icon.png") == ICON_PATH.read_bytes(), "JAR icon differs from verified source icon"
        packed_metadata = json.loads(archive.read("fabric.mod.json").decode("utf-8"))
        assert packed_metadata.get("id") == MOD_ID, "Packaged mod ID is incorrect"
        assert packed_metadata.get("version") == "1.0.32", "Packaged mod version is not 1.0.32"
        assert packed_metadata.get("icon") == "icon.png", "Packaged metadata does not reference icon.png"
        assert "Release credit" not in packed_metadata.get("description", "")
        assert "发布署名" not in packed_metadata.get("description", "")
        manifest = archive.read("META-INF/MANIFEST.MF").decode("utf-8")
        assert "Implementation-Version: 1.0.32" in manifest, (
            "Packaged manifest Implementation-Version is not 1.0.32"
        )
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Verify all {EXPECTED_ASSET_COUNT} generated traffic-light resource chains."
    )
    parser.add_argument("jar", nargs="?", type=Path, help="Optional built JAR to verify byte-for-byte")
    args = parser.parse_args()

    (
        items,
        _,
        total_source_elements,
        total_exported_elements,
        excluded_count,
        total_collision_boxes,
    ) = verify_resources()
    if args.jar is not None:
        verify_jar(args.jar.resolve())
    suffix = f" and JAR {args.jar}" if args.jar is not None else ""
    print(
        f"Verified {len(items)} source/catalog/resource chains, "
        f"{total_exported_elements} visible source/model elements and {total_collision_boxes} collision boxes "
        f"({excluded_count} hidden placeholders excluded from {total_source_elements} raw cubes), "
        f"{len(ALL_LOCALES)} complete languages, a verified 512x512 mod icon, "
        f"texture SHA-256 equality{suffix}."
    )


if __name__ == "__main__":
    main()
