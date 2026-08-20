"""本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。"""

from __future__ import annotations

import copy
import itertools
import json
import math
import posixpath
import re
import shutil
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

SOURCE_CONFIG = {
    "杆子": {
        "category": "pole",
        "workbook": "杆子模型名称.xlsx",
        "expected": 46,
    },
    "红绿灯框架": {
        "category": "frame",
        "workbook": "红绿灯框架重置模型名称.xlsx",
        "expected": 27,
    },
    "指示灯": {
        "category": "indicator",
        "workbook": "指示灯重置模型名称.xlsx",
        "expected": 30,
    },
}

PHASE2_SOURCE_CONFIG = {
    "杆子（新增）": {
        "category": "pole",
        "workbook": "杆子新增方块.xlsx",
        "expected": 2,
    },
    "红绿灯框架（新增）": {
        "category": "frame",
        "workbook": "红绿灯框架（二期）新增方块.xlsx",
        "expected": 21,
    },
    "交通灯附属": {
        "category": "annex",
        "workbook": "交通灯附属新增方块名称.xlsx",
        "expected": 10,
    },
    "指示灯（新增）": {
        "category": "indicator",
        "workbook": "指示灯新增方块名称.xlsx",
        "expected": 25,
    },
}

CATEGORY_ORDER = ("frame", "indicator", "pole", "annex")
EXPECTED_CATEGORY_COUNTS = {
    "frame": 48,
    "indicator": 55,
    "pole": 48,
    "annex": 10,
}

# Phase-two frame identifiers intentionally preserve the identifiers supplied in
# the workbook, including its historical spelling.  Only the source file lookup
# is corrected here; changing these identifiers would break the requested IDs.
PHASE2_FRAME_SOURCE_ALIASES = {
    "jinzai_traffic_light_h23c": "jinzai_traffic_light_h23a",
    "jinzai_traffic_ligh_r2": "jinzai_traffic_light_r2",
    "jinzai_traffic_ligh_r3": "jinzai_traffic_light_r3",
    "jinzai_traffic_ligh_r4": "jinzai_traffic_light_r4",
    "jinzai_traffic_ligh_r5": "jinzai_traffic_light_r5",
    "jinzai_traffic_ligh_r6": "jinzai_traffic_light_r6",
    "jinzai_traffic_ligh_r6a": "jinzai_traffic_light_r6a",
    "jinzai_traffic_ligh_r6b": "jinzai_traffic_light_r6b",
}

# These multi-part assemblies previously exposed hundreds of tiny boxes in
# their selection outline.  Minecraft rebuilds/renders that outline while the
# player aims at the block, which caused severe frame drops.  Keep every other
# model precise, but represent these explicitly requested models by the single
# axis-aligned box enclosing their complete placed model volume.
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

_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_RESOURCE_ID_RE = re.compile(r"^[a-z0-9._-]+$")


@dataclass(frozen=True)
class AssetSpec:
    source_folder: str
    source_stem: str
    identifier: str
    category: str
    zh_cn: str
    en_us: str

    @property
    def source_model(self) -> Path:
        return ROOT / self.source_folder / f"{self.source_stem}.bbmodel"

    @property
    def source_texture(self) -> Path:
        return ROOT / self.source_folder / f"{self.source_stem}.png"


def rounded(value: float, digits: int = 6) -> float | int:
    result = round(float(value), digits)
    if math.isclose(result, round(result), abs_tol=10 ** (-digits)):
        return int(round(result))
    return result


def _xlsx_text(node: ET.Element) -> str:
    return "".join(text.text or "" for text in node.iter(f"{{{_SHEET_NS}}}t"))


def read_first_sheet_rows(path: Path) -> list[dict[str, str]]:
    """Read displayed values from the first worksheet using only the XLSX XML."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [_xlsx_text(item) for item in shared_root.findall(f"{{{_SHEET_NS}}}si")]

        first_sheet = workbook.find(f"{{{_SHEET_NS}}}sheets/{{{_SHEET_NS}}}sheet")
        if first_sheet is None:
            raise ValueError(f"Workbook has no sheets: {path}")
        relationship_id = first_sheet.attrib[f"{{{_DOC_REL_NS}}}id"]
        target = None
        for relationship in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship"):
            if relationship.attrib.get("Id") == relationship_id:
                target = relationship.attrib["Target"]
                break
        if target is None:
            raise ValueError(f"Cannot resolve first worksheet in {path}")
        if target.startswith("/"):
            sheet_entry = target.lstrip("/")
        else:
            sheet_entry = posixpath.normpath(posixpath.join("xl", target))
        sheet = ET.fromstring(archive.read(sheet_entry))

        rows: list[dict[str, str]] = []
        for row in sheet.findall(f".//{{{_SHEET_NS}}}sheetData/{{{_SHEET_NS}}}row"):
            values: dict[str, str] = {}
            for cell in row.findall(f"{{{_SHEET_NS}}}c"):
                reference = cell.attrib.get("r", "")
                match = re.match(r"([A-Z]+)", reference)
                if not match:
                    continue
                column = match.group(1)
                cell_type = cell.attrib.get("t")
                if cell_type == "inlineStr":
                    value = _xlsx_text(cell)
                else:
                    value_node = cell.find(f"{{{_SHEET_NS}}}v")
                    raw = "" if value_node is None else value_node.text or ""
                    if cell_type == "s" and raw:
                        value = shared_strings[int(raw)]
                    elif cell_type == "b":
                        value = "TRUE" if raw == "1" else "FALSE"
                    else:
                        value = raw
                values[column] = value.strip()
            rows.append(values)
        return rows


def source_pair_stems(folder: str) -> set[str]:
    source_dir = ROOT / folder
    model_stems = {path.stem for path in source_dir.glob("*.bbmodel")}
    texture_stems = {path.stem for path in source_dir.glob("*.png")}
    if model_stems != texture_stems:
        raise ValueError(
            f"Unpaired sources in {folder}: models-only={sorted(model_stems - texture_stems)}, "
            f"textures-only={sorted(texture_stems - model_stems)}"
        )
    return model_stems


def _pole_english(zh_cn: str, source_stem: str) -> str:
    special = {
        "白杆配件-1": "White Pole Accessory 1",
        "白杆配件-2": "White Pole Accessory 2",
        "红色警示柱": "Red Warning Post",
        "红色警示柱-底部": "Red Warning Post Base",
        "黄色警示柱": "Yellow Warning Post",
        "黄色警示柱-底部": "Yellow Warning Post Base",
        "黑杆配件": "Black Pole Accessory",
    }
    if zh_cn in special:
        return special[zh_cn]
    match = re.match(r"^(细|粗)(白色|黑色|灰色)(横杆|圆杆|延长杆|弯杆|杆)(?:-(.+))?$", zh_cn)
    if not match:
        return "Traffic Light Pole Component " + source_stem.replace("_", " ").title()
    size = {"细": "Thin", "粗": "Thick"}[match.group(1)]
    color = {"白色": "White", "黑色": "Black", "灰色": "Gray"}[match.group(2)]
    kind = {
        "横杆": "Horizontal Pole",
        "圆杆": "Round Pole",
        "延长杆": "Extension Pole",
        "弯杆": "Bent Pole",
        "杆": "Pole",
    }[match.group(3)]
    source_suffix = match.group(4) or ""
    suffix = {
        "": "",
        "接点": "Joint",
        "接点-1": "Joint 1",
        "接点-2": "Joint 2",
        "接点-3": "Joint 3",
        "接点-4": "Joint 4",
        "连接1": "Connector 1",
        "连接2": "Connector 2",
        "沪式连接": "Shanghai-Style Connector",
        "倒T字型": "Inverted-T",
        "T字型": "T-Shaped",
        "底部": "Base",
    }.get(source_suffix, source_suffix.replace("-", " "))
    return " ".join(part for part in (size, color, kind, suffix) if part)


_FRAME_ENGLISH = {
    "无框红绿灯": "Frameless Traffic Light",
    "正框红绿灯": "Square-Framed Traffic Light",
    "圆框红绿灯": "Round-Framed Traffic Light",
    "美式无框红绿灯": "American Frameless Traffic Light",
    "美式有框红绿灯": "American Framed Traffic Light",
    "黑色圆框红绿灯": "Black Round-Framed Traffic Light",
    "广式圆框红绿灯": "Guangzhou-Style Round-Framed Traffic Light",
    "无框横型红绿灯": "Horizontal Frameless Traffic Light",
    "正框横型红绿灯": "Horizontal Square-Framed Traffic Light",
    "圆框横型红绿灯": "Horizontal Round-Framed Traffic Light",
    "黑色圆框横型红绿灯": "Horizontal Black Round-Framed Traffic Light",
    "一体式横型红绿灯": "Integrated Horizontal Traffic Light",
    "一体式红绿灯": "Integrated Traffic Light",
    "框架式红绿灯": "Frame-Mounted Traffic Light",
    "框架式栏杆-1": "Traffic Light Frame Rail 1",
    "框架式栏杆-2": "Traffic Light Frame Rail 2",
    "框架式栏杆-3": "Traffic Light Frame Rail 3",
    "框架式栏杆-4": "Traffic Light Frame Rail 4",
    "框架式栏杆-5": "Traffic Light Frame Rail 5",
    "框架式栏杆-6": "Traffic Light Frame Rail 6",
    "无框人行道红绿灯": "Frameless Pedestrian Traffic Light",
    "框架式人行红绿灯-顶部": "Framed Pedestrian Traffic Light - Top",
    "框架式人行红绿灯-中部": "Framed Pedestrian Traffic Light - Middle",
    "框架式人行红绿灯-底部": "Framed Pedestrian Traffic Light - Bottom",
    "框架式人行红绿灯2-顶部": "Framed Pedestrian Traffic Light 2 - Top",
    "框架式人行红绿灯2-中部": "Framed Pedestrian Traffic Light 2 - Middle",
    "框架式人行红绿灯2-底部": "Framed Pedestrian Traffic Light 2 - Bottom",
    "台北横型红绿灯-1": "Taipei Horizontal Traffic Light 1",
    "台北横型红绿灯-2": "Taipei Horizontal Traffic Light 2",
    "台北竖型红绿灯": "Taipei Vertical Traffic Light",
    "台北四孔红绿灯": "Taipei Four-Lens Traffic Light",
    "无框四孔红绿灯": "Frameless Four-Lens Traffic Light",
    "正框四孔红绿灯": "Square-Framed Four-Lens Traffic Light",
    "复古四孔红绿灯": "Vintage Four-Lens Traffic Light",
    "双组合无框红绿灯": "Dual Frameless Traffic Light",
    "双组合正框红绿灯": "Dual Square-Framed Traffic Light",
    "双组合圆框红绿灯": "Dual Round-Framed Traffic Light",
    "移动式红绿灯": "Portable Traffic Light",
    "移动式红绿灯底座": "Portable Traffic Light Base",
    "太阳能警示灯": "Solar Warning Light",
    "太阳能双警示灯": "Dual Solar Warning Light",
    "新版无框人行道红绿灯": "New Frameless Pedestrian Traffic Light",
    "正框人行道红绿灯": "Square-Framed Pedestrian Traffic Light",
    "无框人行道红绿灯-2": "Frameless Pedestrian Traffic Light 2",
    "台北人行道红绿灯": "Taipei Pedestrian Traffic Light",
    "白色一体式人行道红绿灯-顶部": "White Integrated Pedestrian Traffic Light - Top",
    "白色一体式人行道红绿灯-中部": "White Integrated Pedestrian Traffic Light - Middle",
    "白色一体式人行道红绿灯-底部": "White Integrated Pedestrian Traffic Light - Bottom",
}


_PHASE2_INDICATOR_ENGLISH = {
    "四孔型红灯": "Four-Lens Red Signal",
    "四孔型黄灯": "Four-Lens Yellow Signal",
    "四孔型绿灯-直行和左转": "Four-Lens Green Signal - Straight and Left Turn",
    "四孔型混合灯-红灯和左转": "Four-Lens Mixed Signal - Red and Left Turn",
    "四孔型混合灯-红灯和直行": "Four-Lens Mixed Signal - Red and Straight",
    "双组合红灯-直行和左转": "Dual Red Signal - Straight and Left Turn",
    "双组合黄灯-直行和左转": "Dual Yellow Signal - Straight and Left Turn",
    "双组合绿灯-直行和左转": "Dual Green Signal - Straight and Left Turn",
    "双组合混合灯1-直行和左转": "Dual Mixed Signal 1 - Straight and Left Turn",
    "双组合混合灯2-直行和左转": "Dual Mixed Signal 2 - Straight and Left Turn",
    "移动式红灯": "Portable Red Signal",
    "移动式黄灯": "Portable Yellow Signal",
    "移动式绿灯": "Portable Green Signal",
    "移动式绿灯-直行": "Portable Green Signal - Straight",
    "移动式混合灯-红灯和左转": "Portable Mixed Signal - Red and Left Turn",
    "新版人行道绿灯": "New Pedestrian Green Signal",
    "新版人行道红灯": "New Pedestrian Red Signal",
    "带计时人行道绿灯": "Timed Pedestrian Green Signal",
    "带计时人行道红灯": "Timed Pedestrian Red Signal",
    "旧版人行道绿灯": "Legacy Pedestrian Green Signal",
    "旧版人行道红灯": "Legacy Pedestrian Red Signal",
    "框架式人行道绿灯": "Framed Pedestrian Green Signal",
    "框架式提示语绿灯": "Framed Message Green Signal",
    "框架式人行道红灯": "Framed Pedestrian Red Signal",
    "框架式提示语红灯": "Framed Message Red Signal",
}


_ANNEX_ENGLISH = {
    "地面式交通灯-绿灯": "Ground Traffic Light - Green",
    "地面式交通灯-红灯": "Ground Traffic Light - Red",
    "LED竖型交通灯条-红灯（细杆）": "Vertical LED Traffic Light Strip - Red (Thin Pole)",
    "LED竖型交通灯条-绿灯（细杆）": "Vertical LED Traffic Light Strip - Green (Thin Pole)",
    "LED竖型交通灯条-红灯（粗杆）": "Vertical LED Traffic Light Strip - Red (Thick Pole)",
    "LED竖型交通灯条-绿灯（粗杆）": "Vertical LED Traffic Light Strip - Green (Thick Pole)",
    "LED横型交通灯条-红灯（细杆）": "Horizontal LED Traffic Light Strip - Red (Thin Pole)",
    "LED横型交通灯条-绿灯（细杆）": "Horizontal LED Traffic Light Strip - Green (Thin Pole)",
    "LED横型交通灯条-红灯（粗杆）": "Horizontal LED Traffic Light Strip - Red (Thick Pole)",
    "LED横型交通灯条-绿灯（粗杆）": "Horizontal LED Traffic Light Strip - Green (Thick Pole)",
}


def _indicator_english(zh_cn: str) -> str:
    if zh_cn in _PHASE2_INDICATOR_ENGLISH:
        return _PHASE2_INDICATOR_ENGLISH[zh_cn]
    non_motor = {
        "非机动车道绿灯-直行": "Non-Motor-Vehicle Green Signal - Straight",
        "非机动车道绿灯-左转": "Non-Motor-Vehicle Green Signal - Left Turn",
        "非机动车道黄灯": "Non-Motor-Vehicle Yellow Signal",
        "非机动车道红灯": "Non-Motor-Vehicle Red Signal",
    }
    if zh_cn in non_motor:
        return non_motor[zh_cn]
    orientation = ""
    remainder = zh_cn
    for prefix, translated in (
        ("横竖共用", "Horizontal/Vertical"),
        ("竖型", "Vertical"),
        ("横型", "Horizontal"),
    ):
        if remainder.startswith(prefix):
            orientation = translated
            remainder = remainder[len(prefix) :]
            break
    color = "Signal"
    for token, translated in (("黄灯", "Yellow Signal"), ("红灯", "Red Signal"), ("绿灯", "Green Signal")):
        if remainder.startswith(token):
            color = translated
            remainder = remainder[len(token) :]
            break
    detail = remainder.lstrip("-")
    detail = {
        "圆框": "Circle",
        "直行": "Straight",
        "左转": "Left Turn",
        "右转": "Right Turn",
        "掉头": "U-Turn",
        "": "",
    }.get(detail, detail)
    return " - ".join(part for part in (" ".join(part for part in (orientation, color) if part), detail) if part)


def english_name(category: str, zh_cn: str, source_stem: str) -> str:
    if category == "pole":
        return _pole_english(zh_cn, source_stem)
    if category == "frame":
        return _FRAME_ENGLISH.get(zh_cn, "Traffic Light Frame " + source_stem.replace("_", " ").title())
    if category == "indicator":
        return _indicator_english(zh_cn)
    if category == "annex":
        return _ANNEX_ENGLISH.get(
            zh_cn,
            "Traffic Light Accessory " + source_stem.replace("_", " ").title(),
        )
    raise ValueError(category)


def localized_description(spec: AssetSpec) -> tuple[str, str]:
    if spec.category == "frame":
        return (
            f"红绿灯框架装饰部件：{spec.zh_cn}。",
            f"Decorative traffic-light frame component: {spec.en_us}.",
        )
    if spec.category == "indicator":
        return (
            f"静态发光指示灯：{spec.zh_cn}。",
            f"Static illuminated traffic signal: {spec.en_us}.",
        )
    if spec.category == "pole":
        return (
            f"交通灯杆件装饰部件：{spec.zh_cn}。",
            f"Decorative traffic-light pole component: {spec.en_us}.",
        )
    if spec.category == "annex":
        return (
            f"交通灯附属装饰部件：{spec.zh_cn}。",
            f"Decorative traffic-light accessory: {spec.en_us}.",
        )
    raise ValueError(spec.category)


def discover_asset_specs() -> list[AssetSpec]:
    specs: list[AssetSpec] = []

    pole_rows = read_first_sheet_rows(ROOT / "杆子" / SOURCE_CONFIG["杆子"]["workbook"])
    pole_mapping: dict[str, str] = {}
    deprecated: set[str] = set()
    for row in pole_rows[1:]:
        stem = row.get("A", "")
        if not stem:
            continue
        if "已废弃" in row.get("C", ""):
            deprecated.add(stem)
            continue
        pole_mapping[stem] = row.get("B", "")
    actual_poles = source_pair_stems("杆子")
    if set(pole_mapping) != actual_poles:
        raise ValueError(
            f"Pole workbook/source mismatch: workbook-only={sorted(set(pole_mapping) - actual_poles)}, "
            f"source-only={sorted(actual_poles - set(pole_mapping))}"
        )
    if deprecated != {"thick_pole_2", "white_pole_2"}:
        raise ValueError(f"Unexpected deprecated pole rows: {sorted(deprecated)}")
    for stem, zh_cn in pole_mapping.items():
        identifier = stem.lower()
        specs.append(
            AssetSpec("杆子", stem, identifier, "pole", zh_cn, english_name("pole", zh_cn, stem))
        )

    frame_rows = read_first_sheet_rows(ROOT / "红绿灯框架" / SOURCE_CONFIG["红绿灯框架"]["workbook"])
    frame_mapping = {row.get("A", ""): row.get("B", "") for row in frame_rows[1:] if row.get("A")}
    actual_frames = source_pair_stems("红绿灯框架")
    if set(frame_mapping) != actual_frames:
        raise ValueError(
            f"Frame workbook/source mismatch: workbook-only={sorted(set(frame_mapping) - actual_frames)}, "
            f"source-only={sorted(actual_frames - set(frame_mapping))}"
        )
    for stem, zh_cn in frame_mapping.items():
        identifier = stem.lower()
        specs.append(
            AssetSpec(
                "红绿灯框架", stem, identifier, "frame", zh_cn, english_name("frame", zh_cn, stem)
            )
        )

    indicator_rows = read_first_sheet_rows(ROOT / "指示灯" / SOURCE_CONFIG["指示灯"]["workbook"])
    indicator_mapping: dict[str, tuple[str, str]] = {}
    actual_indicators = source_pair_stems("指示灯")
    for row_number, row in enumerate(indicator_rows[1:], start=2):
        stem = row.get("A", "")
        identifier = row.get("C", "")
        if not stem or not identifier:
            continue
        # The source workbook repeats z3 in row 31.  The paired source and row order prove this is z3a.
        if row_number == 31 and stem == "jinzai_traffic_indicator_z3" and identifier.endswith("_ly5"):
            stem = "jinzai_traffic_indicator_z3a"
        requested_name = row.get("D", "")
        zh_cn = row.get("B", "") if requested_name in ("", "[保持原名]") else requested_name
        if stem in indicator_mapping:
            raise ValueError(f"Duplicate indicator source mapping at XLSX row {row_number}: {stem}")
        indicator_mapping[stem] = (identifier, zh_cn)
    if set(indicator_mapping) != actual_indicators:
        raise ValueError(
            f"Indicator workbook/source mismatch: workbook-only={sorted(set(indicator_mapping) - actual_indicators)}, "
            f"source-only={sorted(actual_indicators - set(indicator_mapping))}"
        )
    for stem, (identifier, zh_cn) in indicator_mapping.items():
        specs.append(
            AssetSpec(
                "指示灯",
                stem,
                identifier,
                "indicator",
                zh_cn,
                english_name("indicator", zh_cn, stem),
            )
        )

    phase1_counts = {
        category: sum(spec.category == category for spec in specs)
        for category in ("pole", "frame", "indicator")
    }
    expected_phase1_counts = {
        config["category"]: config["expected"] for config in SOURCE_CONFIG.values()
    }
    if phase1_counts != expected_phase1_counts:
        raise ValueError(
            f"Unexpected phase-one mapped counts: {phase1_counts}; "
            f"expected {expected_phase1_counts}"
        )
    if len(specs) != 103:
        raise ValueError(f"Expected 103 phase-one assets, found {len(specs)}")

    phase2_pole_folder = "杆子（新增）"
    phase2_pole_rows = read_first_sheet_rows(
        ROOT / phase2_pole_folder / PHASE2_SOURCE_CONFIG[phase2_pole_folder]["workbook"]
    )
    phase2_pole_mapping = {
        row.get("A", ""): row.get("B", "")
        for row in phase2_pole_rows[1:]
        if row.get("A")
    }
    actual_phase2_poles = source_pair_stems(phase2_pole_folder)
    if set(phase2_pole_mapping) != actual_phase2_poles:
        raise ValueError(
            "Phase-two pole workbook/source mismatch: "
            f"workbook-only={sorted(set(phase2_pole_mapping) - actual_phase2_poles)}, "
            f"source-only={sorted(actual_phase2_poles - set(phase2_pole_mapping))}"
        )
    for stem, zh_cn in phase2_pole_mapping.items():
        specs.append(
            AssetSpec(
                phase2_pole_folder,
                stem,
                stem.lower(),
                "pole",
                zh_cn,
                english_name("pole", zh_cn, stem),
            )
        )

    phase2_frame_folder = "红绿灯框架（新增）"
    phase2_frame_rows = read_first_sheet_rows(
        ROOT / phase2_frame_folder / PHASE2_SOURCE_CONFIG[phase2_frame_folder]["workbook"]
    )
    phase2_frame_mapping: dict[str, tuple[str, str]] = {}
    for row_number, row in enumerate(phase2_frame_rows[1:], start=2):
        identifier = row.get("A", "")
        if not identifier:
            continue
        if identifier in phase2_frame_mapping:
            raise ValueError(
                f"Duplicate phase-two frame identifier at XLSX row {row_number}: {identifier}"
            )
        source_stem = PHASE2_FRAME_SOURCE_ALIASES.get(identifier, identifier)
        phase2_frame_mapping[identifier] = (source_stem, row.get("B", ""))
    if not set(PHASE2_FRAME_SOURCE_ALIASES).issubset(phase2_frame_mapping):
        raise ValueError(
            "Phase-two frame aliases are absent from the workbook: "
            f"{sorted(set(PHASE2_FRAME_SOURCE_ALIASES) - set(phase2_frame_mapping))}"
        )
    mapped_phase2_frame_stems = {
        source_stem for source_stem, _ in phase2_frame_mapping.values()
    }
    actual_phase2_frames = source_pair_stems(phase2_frame_folder)
    if mapped_phase2_frame_stems != actual_phase2_frames:
        raise ValueError(
            "Phase-two frame workbook/source mismatch after aliases: "
            f"workbook-only={sorted(mapped_phase2_frame_stems - actual_phase2_frames)}, "
            f"source-only={sorted(actual_phase2_frames - mapped_phase2_frame_stems)}"
        )
    for identifier, (source_stem, zh_cn) in phase2_frame_mapping.items():
        specs.append(
            AssetSpec(
                phase2_frame_folder,
                source_stem,
                identifier.lower(),
                "frame",
                zh_cn,
                english_name("frame", zh_cn, source_stem),
            )
        )

    phase2_indicator_folder = "指示灯（新增）"
    phase2_indicator_rows = read_first_sheet_rows(
        ROOT
        / phase2_indicator_folder
        / PHASE2_SOURCE_CONFIG[phase2_indicator_folder]["workbook"]
    )
    phase2_indicator_mapping: dict[str, str] = {}
    for row_number, row in enumerate(phase2_indicator_rows[1:], start=2):
        stem = row.get("A", "")
        if not stem:
            continue
        # The second 7b entry in the supplied workbook describes the paired 7d source.
        if row_number == 11 and stem == "jinzai_traffic_light_7b":
            stem = "jinzai_traffic_light_7d"
        if stem in phase2_indicator_mapping:
            raise ValueError(
                f"Duplicate phase-two indicator source at XLSX row {row_number}: {stem}"
            )
        phase2_indicator_mapping[stem] = row.get("B", "")
    actual_phase2_indicators = source_pair_stems(phase2_indicator_folder)
    if set(phase2_indicator_mapping) != actual_phase2_indicators:
        raise ValueError(
            "Phase-two indicator workbook/source mismatch: "
            f"workbook-only={sorted(set(phase2_indicator_mapping) - actual_phase2_indicators)}, "
            f"source-only={sorted(actual_phase2_indicators - set(phase2_indicator_mapping))}"
        )
    for stem, zh_cn in phase2_indicator_mapping.items():
        specs.append(
            AssetSpec(
                phase2_indicator_folder,
                stem,
                stem.lower(),
                "indicator",
                zh_cn,
                english_name("indicator", zh_cn, stem),
            )
        )

    annex_folder = "交通灯附属"
    annex_rows = read_first_sheet_rows(
        ROOT / annex_folder / PHASE2_SOURCE_CONFIG[annex_folder]["workbook"]
    )
    annex_mapping: dict[str, str] = {}
    deprecated_annexes: set[str] = set()
    for row_number, row in enumerate(annex_rows[1:], start=2):
        stem = row.get("A", "")
        if not stem:
            continue
        if "已废弃" in row.get("C", ""):
            deprecated_annexes.add(stem)
            continue
        if stem in annex_mapping:
            raise ValueError(f"Duplicate annex source at XLSX row {row_number}: {stem}")
        annex_mapping[stem] = row.get("B", "")
    expected_deprecated_annexes = {
        "jinzai_traffic_annex_1",
        "jinzai_traffic_annex_1a",
    }
    if deprecated_annexes != expected_deprecated_annexes:
        raise ValueError(
            f"Unexpected deprecated annex rows: {sorted(deprecated_annexes)}; "
            f"expected {sorted(expected_deprecated_annexes)}"
        )
    actual_annexes = source_pair_stems(annex_folder)
    if set(annex_mapping) != actual_annexes:
        raise ValueError(
            "Annex workbook/source mismatch: "
            f"workbook-only={sorted(set(annex_mapping) - actual_annexes)}, "
            f"source-only={sorted(actual_annexes - set(annex_mapping))}"
        )
    for stem, zh_cn in annex_mapping.items():
        specs.append(
            AssetSpec(
                annex_folder,
                stem,
                stem.lower(),
                "annex",
                zh_cn,
                english_name("annex", zh_cn, stem),
            )
        )

    counts = {
        category: sum(spec.category == category for spec in specs)
        for category in CATEGORY_ORDER
    }
    if counts != EXPECTED_CATEGORY_COUNTS:
        raise ValueError(
            f"Unexpected mapped counts: {counts}; expected {EXPECTED_CATEGORY_COUNTS}"
        )
    if len(specs) != 161:
        raise ValueError(f"Expected 161 assets, found {len(specs)}")
    identifiers = [spec.identifier for spec in specs]
    if len(set(identifiers)) != len(identifiers):
        duplicates = sorted({identifier for identifier in identifiers if identifiers.count(identifier) > 1})
        raise ValueError(f"Duplicate final resource identifiers: {duplicates}")
    for spec in specs:
        if not _RESOURCE_ID_RE.fullmatch(spec.identifier):
            raise ValueError(f"Invalid Minecraft resource identifier: {spec.identifier}")
        if not spec.zh_cn or not spec.en_us:
            raise ValueError(f"Missing translation for {spec.identifier}")
    return sorted(
        specs,
        key=lambda spec: (
            CATEGORY_ORDER.index(spec.category),
            1 if spec.source_folder in PHASE2_SOURCE_CONFIG else 0,
            spec.source_stem.lower(),
            spec.source_stem,
        ),
    )


def _inflated_bounds(element: dict[str, Any]) -> tuple[list[float], list[float]]:
    inflate = float(element.get("inflate", 0) or 0)
    from_pos = [float(value) - inflate for value in element["from"]]
    to_pos = [float(value) + inflate for value in element["to"]]
    return from_pos, to_pos


def _rotation_parts(element: dict[str, Any]) -> tuple[str, float, list[float]] | None:
    rotation = element.get("rotation")
    if not rotation or not any(abs(float(value)) > 1e-9 for value in rotation):
        return None
    if element.get("rescale", False):
        raise ValueError("Rotated elements with rescale=true are not supported by collision generation")
    non_zero = [(axis, float(angle)) for axis, angle in zip("xyz", rotation) if abs(float(angle)) > 1e-9]
    if len(non_zero) != 1:
        raise ValueError(f"Unsupported multi-axis element rotation: {rotation}")
    axis, angle = non_zero[0]
    if angle not in (-45.0, -22.5, 22.5, 45.0):
        raise ValueError(f"Unsupported Minecraft element angle: {angle}")
    return axis, angle, [float(value) for value in element.get("origin", [8, 8, 8])]


def _rotate_point(point: Iterable[float], axis: str, angle: float, origin: Iterable[float]) -> list[float]:
    x, y, z = (float(value) for value in point)
    ox, oy, oz = (float(value) for value in origin)
    x -= ox
    y -= oy
    z -= oz
    radians = math.radians(angle)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    if axis == "x":
        y, z = y * cosine - z * sine, y * sine + z * cosine
    elif axis == "y":
        x, z = x * cosine + z * sine, -x * sine + z * cosine
    elif axis == "z":
        x, y = x * cosine - y * sine, x * sine + y * cosine
    else:
        raise ValueError(axis)
    return [x + ox, y + oy, z + oz]


def _aabb_for_rotated_bounds(
    from_pos: list[float],
    to_pos: list[float],
    rotation: tuple[str, float, list[float]] | None,
) -> list[float | int]:
    corners = [list(point) for point in itertools.product(*zip(from_pos, to_pos))]
    if rotation is not None:
        axis, angle, origin = rotation
        corners = [_rotate_point(point, axis, angle, origin) for point in corners]
    minimum = [min(point[index] for point in corners) for index in range(3)]
    maximum = [max(point[index] for point in corners) for index in range(3)]
    return [rounded(value) for value in minimum + maximum]


def _split_interval(start: float, end: float, maximum_size: float = 1.0) -> list[tuple[float, float]]:
    length = end - start
    if length <= 0:
        raise ValueError(f"Cannot split a non-positive interval: {start}..{end}")
    segment_count = max(1, math.ceil(length / maximum_size - 1e-9))
    segment_size = length / segment_count
    return [
        (start + segment_size * index, end if index + 1 == segment_count else start + segment_size * (index + 1))
        for index in range(segment_count)
    ]


def collision_boxes(element: dict[str, Any]) -> list[list[float | int]]:
    """Approximate a rotated cuboid with <=1-model-unit cells in its rotation plane."""
    from_pos, to_pos = _inflated_bounds(element)
    rotation = _rotation_parts(element)
    if rotation is None:
        return [_aabb_for_rotated_bounds(from_pos, to_pos, None)]

    axis, _, _ = rotation
    plane_axes = {
        "x": (1, 2),
        "y": (0, 2),
        "z": (0, 1),
    }[axis]
    intervals = [
        _split_interval(from_pos[index], to_pos[index])
        for index in plane_axes
    ]

    boxes: list[list[float | int]] = []
    for first_interval, second_interval in itertools.product(*intervals):
        sub_from = list(from_pos)
        sub_to = list(to_pos)
        sub_from[plane_axes[0]], sub_to[plane_axes[0]] = first_interval
        sub_from[plane_axes[1]], sub_to[plane_axes[1]] = second_interval
        boxes.append(_aabb_for_rotated_bounds(sub_from, sub_to, rotation))
    return boxes


def enclosing_collision_box(
    boxes: list[list[float | int]],
) -> list[list[float | int]]:
    if not boxes:
        raise ValueError("Cannot build an enclosing collision box from an empty model")
    minimum = [min(float(box[index]) for box in boxes) for index in range(3)]
    maximum = [max(float(box[index + 3]) for box in boxes) for index in range(3)]
    return [[rounded(value) for value in minimum + maximum]]


def scaled_uv(uv: list[float], width: int, height: int) -> list[float | int]:
    if len(uv) != 4:
        raise ValueError(f"Invalid face UV: {uv}")
    result = [
        rounded(float(uv[0]) * 16 / width),
        rounded(float(uv[1]) * 16 / height),
        rounded(float(uv[2]) * 16 / width),
        rounded(float(uv[3]) * 16 / height),
    ]
    if any(float(value) < -1e-6 or float(value) > 16.000001 for value in result):
        raise ValueError(f"Normalized UV outside 0..16: source={uv}, result={result}")
    return result


def _referenced_texture_index(source: dict[str, Any], source_stem: str) -> int:
    references: set[int] = set()
    for element in source.get("elements", []):
        for face in element.get("faces", {}).values():
            if face is None or face.get("enabled") is False or face.get("texture") is None:
                continue
            references.add(int(face["texture"]))
    if len(references) != 1:
        raise ValueError(f"{source_stem} must reference exactly one texture, found {sorted(references)}")
    index = next(iter(references))
    textures = source.get("textures", [])
    if index < 0 or index >= len(textures):
        raise ValueError(f"Invalid texture array index {index} in {source_stem}")
    texture = textures[index]
    expected_name = f"{source_stem}.png"
    if texture.get("name") != expected_name or texture.get("relative_path") != expected_name:
        raise ValueError(
            f"Referenced texture mismatch in {source_stem}: "
            f"name={texture.get('name')!r}, path={texture.get('relative_path')!r}"
        )
    return index


def export_element(
    element: dict[str, Any],
    width: int,
    height: int,
    referenced_texture_index: int,
) -> dict[str, Any]:
    if (
        element.get("type", "cube") != "cube"
        or element.get("export", True) is False
        or element.get("visibility") is False
    ):
        raise ValueError("Every source element must be an exported cube")
    from_pos, to_pos = _inflated_bounds(element)
    output: dict[str, Any] = {
        "from": [rounded(value) for value in from_pos],
        "to": [rounded(value) for value in to_pos],
        "shade": bool(element.get("shade", True)),
        "faces": {},
    }
    rotation = _rotation_parts(element)
    if rotation is not None:
        axis, angle, origin = rotation
        output["rotation"] = {
            "origin": [rounded(value) for value in origin],
            "axis": axis,
            "angle": rounded(angle),
            "rescale": bool(element.get("rescale", False)),
        }

    for direction, face in element.get("faces", {}).items():
        if face is None or face.get("enabled") is False:
            continue
        if face.get("texture") is None:
            raise ValueError("A visible source face has no texture assignment")
        face_texture_index = int(face["texture"])
        if face_texture_index != referenced_texture_index:
            raise ValueError(f"A face unexpectedly references texture index {face_texture_index}")
        exported_face: dict[str, Any] = {
            "uv": scaled_uv(face["uv"], width, height),
            "texture": "#0",
        }
        if "rotation" in face:
            exported_face["rotation"] = int(face["rotation"])
        if face.get("cullface"):
            exported_face["cullface"] = str(face["cullface"])
        tint = face.get("tint", face.get("tintindex"))
        if tint is not None and int(tint) >= 0:
            exported_face["tintindex"] = int(tint)
        output["faces"][direction] = exported_face
    if not output["faces"]:
        raise ValueError("Exported cube has no enabled textured faces")
    return output


def export_model(
    spec: AssetSpec,
) -> tuple[dict[str, Any], list[list[float | int]], int, int]:
    source = json.loads(spec.source_model.read_text(encoding="utf-8"))
    meta = source.get("meta", {})
    if meta.get("model_format") != "java_block":
        raise ValueError(f"{spec.source_model.name} is not a java_block model")
    if source.get("name") != spec.source_stem:
        raise ValueError(f"Model name/file mismatch: {spec.source_model}")
    width = int(source["resolution"]["width"])
    height = int(source["resolution"]["height"])
    texture_index = _referenced_texture_index(source, spec.source_stem)
    source_elements = source.get("elements", [])
    exported_source_elements = [
        element
        for element in source_elements
        if element.get("type", "cube") == "cube"
        and element.get("export", True) is not False
        and element.get("visibility") is not False
    ]
    elements = [
        export_element(element, width, height, texture_index)
        for element in exported_source_elements
    ]
    boxes = [
        box
        for element in exported_source_elements
        for box in collision_boxes(element)
    ]
    if spec.identifier in SIMPLIFIED_BOUNDING_COLLISION_IDS:
        boxes = enclosing_collision_box(boxes)
    if len(elements) != len(exported_source_elements):
        raise AssertionError(f"Element export count mismatch for {spec.source_stem}")

    model: dict[str, Any] = {
        "credit": "Crzay津仔 / Made with Blockbench",
        "ambientocclusion": bool(source.get("ambientocclusion", True)),
        "gui_light": "front" if source.get("front_gui_light", False) else "side",
        "texture_size": [width, height],
        "textures": {
            "0": f"{MOD_ID}:block/{spec.identifier}",
            "particle": f"{MOD_ID}:block/{spec.identifier}",
        },
        "elements": elements,
    }
    if "display" in source:
        model["display"] = copy.deepcopy(source["display"])
    return model, boxes, len(source_elements), len(source_elements) - len(exported_source_elements)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_phase2_spec(spec: AssetSpec) -> bool:
    return spec.source_folder in PHASE2_SOURCE_CONFIG


def load_phase2_translation_source(phase2_specs: list[AssetSpec]) -> dict[str, Any]:
    if not PHASE2_TRANSLATION_SOURCE.is_file():
        raise ValueError(f"Missing phase-two translation source: {PHASE2_TRANSLATION_SOURCE}")
    try:
        payload = json.loads(PHASE2_TRANSLATION_SOURCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        raise ValueError(
            f"Invalid phase-two translation source {PHASE2_TRANSLATION_SOURCE}: {exception}"
        ) from exception
    if not isinstance(payload, dict):
        raise ValueError("Phase-two translation source must be a JSON object")
    expected_root_fields = {"schema", "phase2_ids", "locales"}
    if set(payload) != expected_root_fields:
        raise ValueError(
            "Phase-two translation root fields differ: "
            f"missing={sorted(expected_root_fields - set(payload))}, "
            f"extra={sorted(set(payload) - expected_root_fields)}"
        )
    if payload.get("schema") != 1:
        raise ValueError(
            f"Unsupported phase-two translation schema: {payload.get('schema')!r}"
        )

    expected_ids = {spec.identifier for spec in phase2_specs}
    supplied_ids = payload.get("phase2_ids")
    if not isinstance(supplied_ids, list) or any(
        not isinstance(identifier, str) or not identifier.strip()
        for identifier in supplied_ids
    ):
        raise ValueError("phase2_ids must be a list of non-blank strings")
    if len(supplied_ids) != len(set(supplied_ids)):
        raise ValueError("phase2_ids contains duplicate identifiers")
    if set(supplied_ids) != expected_ids:
        raise ValueError(
            "Phase-two translated identifier mismatch: "
            f"missing={sorted(expected_ids - set(supplied_ids))}, "
            f"extra={sorted(set(supplied_ids) - expected_ids)}"
        )

    locales = payload.get("locales")
    if not isinstance(locales, dict):
        raise ValueError("Phase-two translation locales must be an object")
    if set(locales) != set(EXTRA_LOCALES):
        raise ValueError(
            "Phase-two translation locale mismatch: "
            f"missing={sorted(set(EXTRA_LOCALES) - set(locales))}, "
            f"extra={sorted(set(locales) - set(EXTRA_LOCALES))}"
        )
    return locales


def phase2_locale_values(
    locale: str,
    locale_source: Any,
    phase2_specs: list[AssetSpec],
) -> dict[str, str]:
    if not isinstance(locale_source, dict):
        raise ValueError(f"Phase-two locale {locale} must be an object")
    expected_fields = {
        "names",
        "item_group_annex",
        "category_tooltip_annex",
        "description_templates",
    }
    if set(locale_source) != expected_fields:
        raise ValueError(
            f"Phase-two locale fields differ for {locale}: "
            f"missing={sorted(expected_fields - set(locale_source))}, "
            f"extra={sorted(set(locale_source) - expected_fields)}"
        )

    expected_ids = {spec.identifier for spec in phase2_specs}
    names = locale_source.get("names")
    if not isinstance(names, dict) or set(names) != expected_ids:
        supplied_name_ids = set(names) if isinstance(names, dict) else set()
        raise ValueError(
            f"Phase-two name identifier mismatch for {locale}: "
            f"missing={sorted(expected_ids - supplied_name_ids)}, "
            f"extra={sorted(supplied_name_ids - expected_ids)}"
        )
    templates = locale_source.get("description_templates")
    expected_template_categories = set(CATEGORY_ORDER)
    if not isinstance(templates, dict) or set(templates) != expected_template_categories:
        supplied_template_categories = set(templates) if isinstance(templates, dict) else set()
        raise ValueError(
            f"Phase-two description template mismatch for {locale}: "
            f"missing={sorted(expected_template_categories - supplied_template_categories)}, "
            f"extra={sorted(supplied_template_categories - expected_template_categories)}"
        )

    values: dict[str, str] = {
        f"itemGroup.{MOD_ID}.annex": locale_source.get("item_group_annex"),
        f"tooltip.{MOD_ID}.category.annex": locale_source.get("category_tooltip_annex"),
    }
    for spec in phase2_specs:
        translated_name = names[spec.identifier]
        if not isinstance(translated_name, str) or not translated_name.strip():
            raise ValueError(
                f"Blank or non-string phase-two name for {locale}: {spec.identifier}"
            )
        template = templates[spec.category]
        if not isinstance(template, str) or not template.strip() or "{name}" not in template:
            raise ValueError(
                f"Invalid {spec.category} description template for {locale}: {template!r}"
            )
        try:
            translated_description = template.format(name=translated_name)
        except (KeyError, ValueError) as exception:
            raise ValueError(
                f"Cannot format {spec.category} description template for {locale}: {exception}"
            ) from exception
        values[f"block.{MOD_ID}.{spec.identifier}"] = translated_name
        values[f"tooltip.{MOD_ID}.{spec.identifier}.description"] = translated_description

    invalid_values = [
        key for key, value in values.items()
        if not isinstance(value, str) or not value.strip()
    ]
    if invalid_values:
        raise ValueError(f"Blank or non-string phase-two translations for {locale}: {invalid_values}")
    expected_value_count = len(phase2_specs) * 2 + 2
    if len(values) != expected_value_count:
        raise ValueError(
            f"Expected {expected_value_count} phase-two translations for {locale}, "
            f"found {len(values)}"
        )
    return values


def _blockstate(identifier: str) -> dict[str, Any]:
    model = f"{MOD_ID}:block/{identifier}"
    return {
        "variants": {
            "facing=north": {"model": model},
            "facing=east": {"model": model, "y": 90},
            "facing=south": {"model": model, "y": 180},
            "facing=west": {"model": model, "y": 270},
        }
    }


def _loot_table(identifier: str) -> dict[str, Any]:
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


def main() -> None:
    specs = discover_asset_specs()
    identifiers = {spec.identifier for spec in specs}
    if not SIMPLIFIED_BOUNDING_COLLISION_IDS <= identifiers:
        raise ValueError(
            "Unknown simplified-collision IDs: "
            f"{sorted(SIMPLIFIED_BOUNDING_COLLISION_IDS - identifiers)}"
        )

    # These namespace roots are entirely generated by this script.
    for generated_root in (ASSET_ROOT, DATA_ROOT):
        if generated_root.exists():
            shutil.rmtree(generated_root)

    block_models = ASSET_ROOT / "models" / "block"
    item_models = ASSET_ROOT / "models" / "item"
    blockstates = ASSET_ROOT / "blockstates"
    textures = ASSET_ROOT / "textures" / "block"
    loot_tables = DATA_ROOT / "loot_tables" / "blocks"

    zh_cn: dict[str, str] = {
        f"itemGroup.{MOD_ID}.frame": "红绿灯框架",
        f"itemGroup.{MOD_ID}.indicator": "指示灯",
        f"itemGroup.{MOD_ID}.pole": "杆子",
        f"itemGroup.{MOD_ID}.annex": "交通灯附属",
        f"tooltip.{MOD_ID}.category.frame": "支持四向放置，碰撞箱与模型对齐。",
        f"tooltip.{MOD_ID}.category.indicator": "静态发光，无实体碰撞，可被玩家和实体穿过。",
        f"tooltip.{MOD_ID}.category.pole": "支持四向放置，精细碰撞箱与模型对齐。",
        f"tooltip.{MOD_ID}.category.annex": "静态发光，无实体碰撞，可被玩家和实体穿过。",
        f"tooltip.{MOD_ID}.indicator.automation_limit": "不含倒计时、自动切灯或红石控制。",
    }
    en_us: dict[str, str] = {
        f"itemGroup.{MOD_ID}.frame": "Traffic Light Frames",
        f"itemGroup.{MOD_ID}.indicator": "Traffic Light Indicators",
        f"itemGroup.{MOD_ID}.pole": "Traffic Light Poles",
        f"itemGroup.{MOD_ID}.annex": "Traffic Light Accessories",
        f"tooltip.{MOD_ID}.category.frame": "Supports four horizontal orientations with model-aligned collision.",
        f"tooltip.{MOD_ID}.category.indicator": "Always lit with no physical collision; players and entities can pass through.",
        f"tooltip.{MOD_ID}.category.pole": "Supports four horizontal orientations with precise model-aligned collision.",
        f"tooltip.{MOD_ID}.category.annex": "Always lit with no physical collision; players and entities can pass through.",
        f"tooltip.{MOD_ID}.indicator.automation_limit": "No countdown, automatic cycling, or redstone control.",
    }
    catalog_entries: list[dict[str, Any]] = []
    category_values: dict[str, list[str]] = {
        "frame": [],
        "indicator": [],
        "pole": [],
        "annex": [],
    }
    total_elements = 0
    total_collision_boxes = 0
    total_source_elements = 0
    total_excluded_elements = 0

    for spec in specs:
        model, boxes, source_count, excluded_count = export_model(spec)
        total_elements += len(model["elements"])
        total_collision_boxes += len(boxes)
        total_source_elements += source_count
        total_excluded_elements += excluded_count
        write_json(block_models / f"{spec.identifier}.json", model)
        write_json(item_models / f"{spec.identifier}.json", {"parent": f"{MOD_ID}:block/{spec.identifier}"})
        write_json(blockstates / f"{spec.identifier}.json", _blockstate(spec.identifier))
        write_json(loot_tables / f"{spec.identifier}.json", _loot_table(spec.identifier))
        textures.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec.source_texture, textures / f"{spec.identifier}.png")

        translation_key = f"block.{MOD_ID}.{spec.identifier}"
        zh_cn[translation_key] = spec.zh_cn
        en_us[translation_key] = spec.en_us
        description_key = f"tooltip.{MOD_ID}.{spec.identifier}.description"
        zh_description, en_description = localized_description(spec)
        zh_cn[description_key] = zh_description
        en_us[description_key] = en_description
        category_values[spec.category].append(f"{MOD_ID}:{spec.identifier}")
        catalog_entries.append(
            {
                "id": spec.identifier,
                "category": spec.category,
                "source_folder": spec.source_folder,
                "source_stem": spec.source_stem,
                "collision_boxes": boxes,
            }
        )

    translations: dict[str, dict[str, str]] = {
        "zh_cn": zh_cn,
        "en_us": en_us,
    }
    expected_translation_keys = set(en_us)
    if set(zh_cn) != expected_translation_keys:
        raise ValueError("Generated Chinese and English translation keys differ")
    phase2_specs = [spec for spec in specs if is_phase2_spec(spec)]
    if len(phase2_specs) != 58:
        raise ValueError(f"Expected 58 phase-two assets, found {len(phase2_specs)}")
    phase2_translation_keys = {
        f"itemGroup.{MOD_ID}.annex",
        f"tooltip.{MOD_ID}.category.annex",
    }
    for spec in phase2_specs:
        phase2_translation_keys.add(f"block.{MOD_ID}.{spec.identifier}")
        phase2_translation_keys.add(f"tooltip.{MOD_ID}.{spec.identifier}.description")
    phase1_translation_keys = expected_translation_keys - phase2_translation_keys
    if len(phase1_translation_keys) != 213:
        raise ValueError(
            f"Expected 213 phase-one translation keys, found {len(phase1_translation_keys)}"
        )
    if len(phase2_translation_keys) != 118:
        raise ValueError(
            f"Expected 118 phase-two translation keys, found {len(phase2_translation_keys)}"
        )
    if len(expected_translation_keys) != 331:
        raise ValueError(
            f"Expected 331 complete translation keys, found {len(expected_translation_keys)}"
        )
    phase2_translation_locales = load_phase2_translation_source(phase2_specs)
    for locale in EXTRA_LOCALES:
        source_path = TRANSLATION_SOURCE_ROOT / f"{locale}.json"
        if not source_path.is_file():
            raise ValueError(f"Missing translation source: {source_path}")
        try:
            translated = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exception:
            raise ValueError(f"Invalid translation source {source_path}: {exception}") from exception
        if not isinstance(translated, dict):
            raise ValueError(f"Translation source must be an object: {source_path}")
        if set(translated) != phase1_translation_keys:
            raise ValueError(
                f"Phase-one translation key mismatch for {locale}: "
                f"missing={sorted(phase1_translation_keys - set(translated))}, "
                f"extra={sorted(set(translated) - phase1_translation_keys)}"
            )
        invalid_values = [
            key for key, value in translated.items()
            if not isinstance(value, str) or not value.strip()
        ]
        if invalid_values:
            raise ValueError(f"Blank or non-string {locale} translations: {invalid_values}")
        phase2_translated = phase2_locale_values(
            locale,
            phase2_translation_locales[locale],
            phase2_specs,
        )
        overlapping_keys = set(translated) & set(phase2_translated)
        if overlapping_keys:
            raise ValueError(
                f"Phase-one/phase-two translation overlap for {locale}: "
                f"{sorted(overlapping_keys)}"
            )
        translated.update(phase2_translated)
        if set(translated) != expected_translation_keys:
            raise ValueError(
                f"Complete translation key mismatch for {locale}: "
                f"missing={sorted(expected_translation_keys - set(translated))}, "
                f"extra={sorted(set(translated) - expected_translation_keys)}"
            )
        translations[locale] = translated

    for locale, values in translations.items():
        write_json(ASSET_ROOT / "lang" / f"{locale}.json", dict(sorted(values.items())))
    write_json(ASSET_ROOT / "block_catalog.json", {"schema": 1, "blocks": catalog_entries})

    tag_names = {
        "frame": "frames",
        "indicator": "indicators",
        "pole": "poles",
        "annex": "annexes",
    }
    all_values: list[str] = []
    for category, values in category_values.items():
        values = sorted(values)
        all_values.extend(values)
        write_json(
            DATA_ROOT / "tags" / "blocks" / f"{tag_names[category]}.json",
            {"replace": False, "values": values},
        )
    write_json(
        DATA_ROOT / "tags" / "blocks" / "all_blocks.json",
        {"replace": False, "values": sorted(all_values)},
    )

    counts = {category: len(values) for category, values in category_values.items()}
    print(
        f"Generated {len(specs)} complete blocks ({counts['frame']} frame, "
        f"{counts['indicator']} indicator, {counts['pole']} pole, "
        f"{counts['annex']} annex), "
        f"{total_elements} visible source/model elements and {total_collision_boxes} collision boxes "
        f"({total_excluded_elements} hidden placeholders excluded from "
        f"{total_source_elements} raw cubes), {len(translations)} complete languages."
    )


if __name__ == "__main__":
    main()
