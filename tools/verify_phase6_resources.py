"""Independent public-manifest audit; no private spreadsheet or generator import.

Run with Python 3.11+ using only its standard library. An optional old source ZIP
adds strict preservation checks. This verifies resources, not in-game rendering.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import zipfile
import zlib

import verify_full_resources as independent

ROOT = Path(__file__).resolve().parents[1]
MOD = 'jinzai_traffic_lights'
RESOURCES = ROOT/'common/src/main/resources'
ASSETS = RESOURCES/'assets'/MOD
DATA = RESOURCES/'data'/MOD
EXPECTED_CATEGORIES = {'frame': 89, 'indicator': 108, 'pole': 117, 'annex': 20}
REPLACED_IDS = frozenset(
    [f'jinzai_traffic_light_c{x}' for x in (1, 2, 3, 4, 5, 6, 7, 13, 17, 22, 26, 27, 28, 29, 33, 35, 37)]
    + [f'jinzai_traffic_light_h{x}' for x in (8, 9, 10, 11, 12, 14, 15, 16, 18, 19, 20, 21, 30, 31, 32, 34)]
    + [f'jinzai_traffic_ligh_r{x}' for x in (2, 3, 4, 5, 6)]
    + [f'jinzai_traffic_light_{x}' for x in ('r7', 'r7a', 'r8', 'r8a', 's24', 's25')]
)
NEW_ANIMATED = frozenset(f'jinzai_dynamic_light_{x}' for x in ('25', '25a', '26', '26a', '27', '27a'))
INTERNAL_NAMES = {
    'bd_pole_18': 'bd_pole_14',
    'geometric_pole_1': 'geometric_pole-1',
    'geometric_pole_2': 'geometric_pole-2',
    'geometric_pole_2a': 'geometric_pole-2a',
    'jinzai_traffic_light_c26': 'jinzai_traffic_light_c23',
}
TEXTURE_NAMES = {'jinzai_dynamic_light_16a': 'jinzai_daynamic_light_16a', 'height_limit_bar_6b': 'height_limit_bar_6a'}


def load(path: Path):
    return json.loads(path.read_bytes())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def same_numbers(actual, expected, label):
    assert len(actual) == len(expected), f'{label}: box count differs'
    for a, b in zip(actual, expected):
        assert len(a) == len(b) and all(abs(float(x)-float(y)) <= 1.000001e-6 for x, y in zip(a, b)), f'{label}: {a} != {b}'


def decode_png(data: bytes, label: str) -> tuple[int, int]:
    """Validate chunk CRCs and decode every filtered scanline (non-interlaced PNG)."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n', f'Invalid PNG signature: {label}'
    offset = 8
    compressed = bytearray()
    dimensions = None
    ended = False
    palette = False
    while offset < len(data):
        assert offset+12 <= len(data), f'Truncated PNG: {label}'
        length = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset+4:offset+8]
        payload = data[offset+8:offset+8+length]
        assert len(payload) == length and offset+12+length <= len(data)
        crc = struct.unpack_from('>I', data, offset+8+length)[0]
        assert zlib.crc32(kind+payload) & 0xffffffff == crc, f'PNG CRC mismatch: {label}'
        if kind == b'IHDR':
            assert dimensions is None and offset == 8 and length == 13
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            assert width > 0 and height > 0 and width*height <= 64_000_000
            assert compression == filtering == interlace == 0, f'Unsupported PNG compression/interlace: {label}'
            assert color in {0, 2, 3, 4, 6}
            assert depth in ({1, 2, 4, 8, 16} if color == 0 else {1, 2, 4, 8} if color == 3 else {8, 16})
            dimensions = (width, height)
        elif kind == b'IDAT':
            compressed.extend(payload)
        elif kind == b'PLTE':
            assert 0 < length <= 768 and length % 3 == 0
            palette = True
        elif kind == b'IEND':
            assert length == 0
            ended = True
            offset += 12
            break
        offset += 12+length
    assert ended and offset == len(data) and dimensions and compressed
    assert color != 3 or palette
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    stride = (width*channels*depth+7)//8
    bpp = max(1, (channels*depth+7)//8)
    raw = zlib.decompress(compressed)
    assert len(raw) == height*(stride+1), f'PNG scanline length mismatch: {label}'
    previous = bytearray(stride)
    for y in range(height):
        start = y*(stride+1)
        method = raw[start]
        assert method <= 4, f'Invalid PNG filter: {label}'
        row = bytearray(raw[start+1:start+1+stride])
        for x in range(stride):
            left = row[x-bpp] if x >= bpp else 0
            up = previous[x]
            upper_left = previous[x-bpp] if x >= bpp else 0
            if method == 1: predictor = left
            elif method == 2: predictor = up
            elif method == 3: predictor = (left+up)//2
            elif method == 4:
                p = left+up-upper_left
                distances = (abs(p-left), abs(p-up), abs(p-upper_left))
                predictor = (left, up, upper_left)[distances.index(min(distances))]
            else: predictor = 0
            row[x] = (row[x]+predictor) & 255
        previous = row
    return dimensions


def expected_model(source: dict, item: dict, texture_bytes: bytes):
    identifier, stem = item['id'], item['source_stem']
    internal = INTERNAL_NAMES.get(identifier, stem)
    assert source.get('name') == internal, f'Unexpected internal source name: {identifier}'
    assert source.get('meta', {}).get('model_format') == 'java_block'
    texture_index = independent.referenced_texture_index(source, TEXTURE_NAMES.get(identifier, internal))
    embedded = source['textures'][texture_index].get('source', '')
    if item['phase'] >= 3 or identifier in REPLACED_IDS:
        assert embedded.startswith('data:image/png;base64,')
        assert base64.b64decode(embedded.split(',', 1)[1], validate=True) == texture_bytes, f'Embedded PNG differs: {identifier}'
    visible = [e for e in source['elements'] if e.get('type', 'cube') == 'cube' and e.get('export', True) and e.get('visibility', True)]
    assert len(visible) > 0
    assert all(e.get('type', 'cube') == 'cube' for e in source['elements']), f'Mesh is unsupported: {identifier}'
    width, height = source['resolution']['width'], source['resolution']['height']
    model = {'credit': 'Crzay津仔 / Made with Blockbench', 'ambientocclusion': bool(source.get('ambientocclusion', True)),
             'gui_light': 'front' if source.get('front_gui_light', False) else 'side', 'texture_size': [width, height],
             'textures': {'0': f'{MOD}:block/{identifier}', 'particle': f'{MOD}:block/{identifier}'},
             'elements': [independent.expected_element(e, width, height, texture_index) for e in visible]}
    if 'display' in source: model['display'] = copy.deepcopy(source['display'])
    if identifier in independent.GUI_DISPLAY_OVERRIDES:
        model.setdefault('display', {})['gui'] = copy.deepcopy(independent.GUI_DISPLAY_OVERRIDES[identifier])
    return model, visible


def animation_frames(source_path: Path, output_path: Path, size: tuple[int, int], resolution: list[int], identifier: str) -> int:
    assert source_path.read_bytes() == output_path.read_bytes(), f'Animation metadata byte drift: {identifier}'
    value = load(source_path)
    assert set(value) == {'animation'} and isinstance(value['animation'], dict)
    a = value['animation']
    assert set(a) <= {'width', 'height', 'frametime', 'frames', 'interpolate'}
    fw, fh = a.get('width', min(size)), a.get('height', min(size))
    assert [fw, fh] == resolution and fw > 0 and fh > 0
    assert size[0] % fw == size[1] % fh == 0
    count = (size[0]//fw)*(size[1]//fh)
    assert a.get('frametime', 1) == 10, f'Animation should retain 2 FPS: {identifier}'
    assert isinstance(a.get('interpolate', False), bool)
    frames = a.get('frames', list(range(count)))
    assert frames
    for frame in frames:
        index = frame.get('index') if isinstance(frame, dict) else frame
        assert isinstance(index, int) and not isinstance(index, bool) and 0 <= index < count
        if isinstance(frame, dict):
            assert set(frame) <= {'index', 'time'} and isinstance(frame.get('time', 10), int) and frame.get('time', 10) > 0
    expected = 144 if identifier in NEW_ANIMATED else independent.EXPECTED_ANIMATION_FRAME_COUNTS[identifier]
    assert count == expected, f'Frame count mismatch: {identifier}'
    return count


def verify_baseline(path: Path, items: dict, catalog: dict, working_hashes: Path | None = None) -> dict:
    original_hashes = {entry['path']: entry['sha256'] for entry in load(working_hashes)} if working_hashes else None
    line_endings = set()
    working_hash_checks = set()
    def unchanged(current_path: Path, old_bytes: bytes):
        current = current_path.read_bytes()
        relative = current_path.relative_to(ROOT).as_posix()
        if original_hashes is not None:
            assert relative in original_hashes and sha(current) == original_hashes[relative], f'Original working-tree bytes changed: {relative}'
            working_hash_checks.add(relative)
        if current != old_bytes:
            # Historical archive attributes may export different text line endings.
            # Only JSON text line endings may differ; every JSON field stays exact.
            assert current_path.suffix in {'.json', '.mcmeta', '.bbmodel'} and current.replace(b'\r\n', b'\n') == old_bytes.replace(b'\r\n', b'\n'), f'Unrequested baseline bytes changed: {relative}'
            assert json.loads(current) == json.loads(old_bytes)
            line_endings.add(relative)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        suffix = f'common/src/main/resources/assets/{MOD}/block_catalog.json'
        names = [n for n in z.namelist() if n.endswith(suffix)]
        assert len(names) == 1
        prefix = names[0][:-len(suffix)]
        old = {e['id']: e for e in json.loads(z.read(names[0]))['blocks']}
        assert len(old) == 261 and set(old) <= set(catalog)
        assert len(set(catalog)-set(old)) == 73 and REPLACED_IDS <= set(old)
        retained = set(old)-REPLACED_IDS
        for identifier in old:
            current = catalog[identifier]
            if identifier in retained:
                assert current == old[identifier], f'Unrequested old catalog change: {identifier}'
            else:
                assert current['id'] == old[identifier]['id'] and current['category'] == old[identifier]['category']
                assert current.get('light_level', 0) == old[identifier].get('light_level', 0)
            for extension in ('.bbmodel', '.png', '.png.mcmeta'):
                old_source = f"{old[identifier]['source_folder']}/{old[identifier]['source_stem']}{extension}"
                if prefix+old_source in z.namelist() and identifier in retained:
                    new_source = ROOT/items[identifier]['source_folder']/(items[identifier]['source_stem']+extension)
                    unchanged(new_source, z.read(prefix+old_source))
        root = 'common/src/main/resources/'
        language_paths = {f'assets/{MOD}/lang/{locale}.json' for locale in independent.ALL_LOCALES}
        tags = {f'data/{MOD}/tags/blocks/{name}.json' for name in ('all_blocks', 'frames', 'indicators', 'poles', 'annexes')}
        for rel in language_paths:
            before, after = json.loads(z.read(prefix+root+rel)), load(RESOURCES/rel)
            assert all(after.get(key) == value for key, value in before.items()), f'Old localized name changed: {rel}'
        for rel in tags:
            before, after = json.loads(z.read(prefix+root+rel)), load(RESOURCES/rel)
            assert before['replace'] == after['replace'] and set(before['values']) <= set(after['values'])
        changes = {f'assets/{MOD}/models/block/{i}.json' for i in REPLACED_IDS} | {f'assets/{MOD}/textures/block/{i}.png' for i in REPLACED_IDS}
        excluded = changes | language_paths | tags | {f'assets/{MOD}/block_catalog.json'}
        unchanged_count = 0
        for name in z.namelist():
            if name.startswith(prefix+root) and not name.endswith('/'):
                rel = name[len(prefix+root):]
                if rel not in excluded:
                    unchanged(RESOURCES/rel, z.read(name))
                    unchanged_count += 1
    return {'sha256': sha(path.read_bytes()), 'old_ids': 261, 'replaced_ids': 44, 'untouched_catalog_entries': 217,
            'old_resource_files_checked': unchanged_count, 'archive_line_ending_only_paths': sorted(line_endings),
            'original_working_hashes_sha256': sha(working_hashes.read_bytes()) if working_hashes else None,
            'original_working_files_byte_identical': len(working_hash_checks)}


def verify_resources(baseline_source: Path | None = None, baseline_working_hashes: Path | None = None) -> dict:
    manifest = load(ROOT/'tools/block_manifest.json')
    assert manifest['schema'] == 1 and len(manifest['assets']) == 334
    items = {a['id']: a for a in manifest['assets']}
    assert len(items) == 334 and len({(a['source_folder'], a['source_stem']) for a in items.values()}) == 334
    assert dict(Counter(a['category'] for a in items.values())) == EXPECTED_CATEGORIES
    assert len(REPLACED_IDS) == 44
    assert all(re.fullmatch('[a-z0-9._-]+', identifier) for identifier in items)
    provenance = load(ROOT/'tools/phase6_changes.json')
    assert provenance['schema'] == 1 and len(provenance['added']) == 73 and len(provenance['replaced']) == 44
    assert {a['id'] for a in provenance['replaced']} == REPLACED_IDS
    assert {a['id'] for a in provenance['added']} == {identifier for identifier, item in items.items() if item['phase'] == 6} - REPLACED_IDS
    assert len({a['id'] for a in provenance['added']+provenance['replaced']}) == 117
    for changed in provenance['added']+provenance['replaced']:
        item = items[changed['id']]
        assert (changed['source_folder'], changed['source_stem']) == (item['source_folder'], item['source_stem'])
        for suffix, key in (('.bbmodel', 'model_sha256'), ('.png', 'texture_sha256'), ('.png.mcmeta', 'animation_sha256')):
            if key in changed:
                source = ROOT/item['source_folder']/(item['source_stem']+suffix)
                assert sha(source.read_bytes()) == changed[key], f'Customer source hash changed: {changed["id"]}/{suffix}'
    catalog = {a['id']: a for a in load(ASSETS/'block_catalog.json')['blocks']}
    assert len(catalog) == 334 and set(catalog) == set(items)
    locales = {locale: load(ASSETS/'lang'/f'{locale}.json') for locale in independent.ALL_LOCALES}
    language_keys = {f'block.{MOD}.{i}' for i in items} | {f'itemGroup.{MOD}.{c}' for c in EXPECTED_CATEGORIES}
    for locale, values in locales.items():
        assert set(values) == language_keys, f'Incomplete/extraneous language keys: {locale}'
        assert all(isinstance(value, str) and value.strip() for value in values.values())
    expected_assets = {'block_catalog.json'} | {f'lang/{locale}.json' for locale in locales}
    expected_data = {f'tags/blocks/{name}.json' for name in ('all_blocks', 'frames', 'indicators', 'poles', 'annexes')}
    animations, source_pairs = {}, set()
    total_raw = total_visible = total_boxes = single_phase6 = 0
    old_new_ids = set()
    for identifier, item in items.items():
        folder = ROOT/item['source_folder']
        assert folder.resolve().is_relative_to(ROOT.resolve()) and '/' not in item['source_stem'] and '\\' not in item['source_stem']
        source_path = folder/(item['source_stem']+'.bbmodel')
        texture_path = folder/(item['source_stem']+'.png')
        source_pairs.add(source_path.resolve())
        texture_bytes = texture_path.read_bytes()
        png_size = decode_png(texture_bytes, identifier)
        assert (ASSETS/'textures/block'/f'{identifier}.png').read_bytes() == texture_bytes, f'External PNG altered: {identifier}'
        source = load(source_path)
        expected, visible = expected_model(source, item, texture_bytes)
        assert load(ASSETS/'models/block'/f'{identifier}.json') == expected, f'Generated model/UV/display mismatch: {identifier}'
        assert load(ASSETS/'models/item'/f'{identifier}.json') == {'parent': f'{MOD}:block/{identifier}'}
        assert load(ASSETS/'blockstates'/f'{identifier}.json') == independent.expected_blockstate(identifier)
        assert load(DATA/'loot_tables/blocks'/f'{identifier}.json') == independent.expected_loot(identifier)
        for locale in ('zh_cn', 'en_us'):
            assert locales[locale][f'block.{MOD}.{identifier}'] == item[locale], f'Public name mismatch: {identifier}/{locale}'
        entry = catalog[identifier]
        for key in ('source_folder', 'source_stem', 'category'):
            assert entry[key] == item[key], f'Catalog/source mismatch: {identifier}/{key}'
        is_phase6 = item['phase'] == 6 or identifier in REPLACED_IDS
        if item['phase'] == 6 and identifier not in REPLACED_IDS: old_new_ids.add(identifier)
        if is_phase6:
            complete = [independent.rotated_bounds_aabb(*independent.inflated_bounds(e), independent.rotation_parts(e)) for e in visible]
            boxes = independent.expected_enclosing_collision_box(complete)
            single_phase6 += 1
        else:
            cell = 3.0 if identifier in independent.PHASE3_LONG_DIAGONAL_POLE_IDS else 2.0 if item['phase'] == 3 and item['category'] == 'pole' else 1.0
            boxes = [b for e in visible for b in independent.expected_collision_boxes(e, cell)]
            if identifier in independent.SIMPLIFIED_BOUNDING_COLLISION_IDS or identifier in independent.PHASE4_MODIFIED_MODEL_IDS or item['phase'] in (4, 5) or (item['phase'] == 3 and item['category'] != 'pole'):
                boxes = independent.expected_enclosing_collision_box(boxes)
        same_numbers(entry['collision_boxes'], boxes, identifier)
        for box in entry['collision_boxes']:
            assert len(box) == 6 and all(math.isfinite(float(x)) for x in box)
            assert all(box[a] < box[a+3] for a in range(3))
            rotated = box
            for _ in range(4): rotated = independent.rotate_catalog_box_clockwise(rotated)
            same_numbers([rotated], [box], identifier+' four turns')
        expected_light = item.get('light_level', 15 if item['category'] in ('annex', 'indicator') else 0)
        actual_light = entry.get('light_level', 15 if item['category'] in ('annex', 'indicator') else 0)
        assert isinstance(expected_light, int) and not isinstance(expected_light, bool) and 0 <= expected_light <= 15
        assert actual_light == expected_light, f'Light metadata mismatch: {identifier}'
        if identifier in {'jinzai_traffic_annex_7', 'jinzai_traffic_annex_8', 'jinzai_traffic_annex_9', 'jinzai_traffic_annex_9a', 'jinzai_traffic_annex_9b'}:
            assert actual_light == 0
        if identifier == 'jinzai_traffic_annex_6': assert actual_light == 15
        metadata = Path(str(texture_path)+'.mcmeta')
        if metadata.is_file():
            animations[identifier] = animation_frames(metadata, ASSETS/'textures/block'/f'{identifier}.png.mcmeta', png_size, expected['texture_size'], identifier)
            expected_assets.add(f'textures/block/{identifier}.png.mcmeta')
        else:
            assert png_size[0]*expected['texture_size'][1] == png_size[1]*expected['texture_size'][0], f'Static PNG aspect differs from UV canvas: {identifier}'
        expected_assets.update({f'models/block/{identifier}.json', f'models/item/{identifier}.json', f'blockstates/{identifier}.json', f'textures/block/{identifier}.png'})
        expected_data.add(f'loot_tables/blocks/{identifier}.json')
        total_raw += len(source['elements']); total_visible += len(visible); total_boxes += len(boxes)
    assert len(old_new_ids) == 73 and single_phase6 == 117
    assert set(animations) == set(independent.EXPECTED_ANIMATION_FRAME_COUNTS) | NEW_ANIMATED and len(animations) == 37
    assert independent.relative_file_set(ASSETS) == expected_assets, 'Unexpected asset file coverage'
    assert independent.relative_file_set(DATA) == expected_data, 'Unexpected data file coverage'
    for folder in {ROOT/item['source_folder'] for item in items.values()}:
        assert {p.resolve() for p in folder.glob('*.bbmodel')} == {p for p in source_pairs if p.parent == folder.resolve()}, f'Unmapped source model: {folder.name}'
        assert {p.stem for p in folder.glob('*.png')} == {p.stem for p in folder.glob('*.bbmodel')}
    for category, tag_name in {'frame':'frames','indicator':'indicators','pole':'poles','annex':'annexes'}.items():
        values = sorted(f'{MOD}:{i}' for i,a in items.items() if a['category'] == category)
        assert load(DATA/'tags/blocks'/f'{tag_name}.json') == {'replace':False,'values':values}
    assert load(DATA/'tags/blocks/all_blocks.json') == {'replace':False,'values':sorted(f'{MOD}:{i}' for i in items)}
    result = {'result':'PASS','blocks':334,'categories':EXPECTED_CATEGORIES,'new_blocks':73,'replaced_blocks':44,
              'source_elements':total_raw,'visible_elements':total_visible,'collision_boxes':total_boxes,'phase6_single_boxes':single_phase6,
              'decoded_pngs':334,'animated_textures':37,'animation_frames':animations,'locales':13,'keys_per_locale':338,
              'generated_namespace_files':len(expected_assets)+len(expected_data),'public_manifest_sha256':sha((ROOT/'tools/block_manifest.json').read_bytes()),
              'phase6_customer_source_pairs_hash_checked':117,'phase6_provenance_sha256':sha((ROOT/'tools/phase6_changes.json').read_bytes()),
              'scope':'Independent static source/export/resource audit, not runtime or customer performance acceptance.'}
    if baseline_source: result['baseline'] = verify_baseline(baseline_source, items, catalog, baseline_working_hashes)
    return result


def verify_jar(path: Path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist()))
        assert z.read('LICENSE') == (ROOT/'LICENSE').read_bytes()
        assert not any(re.search(r'jinzai_qa|runtime.?probe|(?:^|/)test(?:/|\.)', name, re.I) for name in z.namelist())
        port = '1.21.1' in path.name
        expected = {}
        for namespace in (ASSETS, DATA):
            for source in namespace.rglob('*'):
                if source.is_file():
                    rel = source.relative_to(RESOURCES).as_posix()
                    if port: rel = rel.replace('/loot_tables/', '/loot_table/').replace('/tags/blocks/', '/tags/block/')
                    expected[rel] = source.read_bytes()
        actual = {n for n in z.namelist() if not n.endswith('/') and n.startswith((f'assets/{MOD}/', f'data/{MOD}/'))}
        assert actual == set(expected)
        for name, value in expected.items(): assert z.read(name) == value, f'JAR resource differs: {name}'


def main():
    parser = argparse.ArgumentParser(description='Verify all 334 traffic-light resources without private XLSX files.')
    parser.add_argument('jar', nargs='?', type=Path, help='Optional final JAR byte comparison')
    parser.add_argument('--baseline-source', type=Path, help='Optional clean 2.0.46 source ZIP for strict 261-ID preservation')
    parser.add_argument('--baseline-working-hashes', type=Path, help='Optional pre-edit working-tree path/SHA-256 JSON list; checks exact bytes including line endings')
    parser.add_argument('--report', type=Path, help='Optional JSON result path')
    args = parser.parse_args()
    assert args.baseline_source or not args.baseline_working_hashes, '--baseline-working-hashes requires --baseline-source'
    result = verify_resources(args.baseline_source, args.baseline_working_hashes)
    if args.jar:
        verify_jar(args.jar)
        result['jar_sha256'] = sha(args.jar.read_bytes())
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    summary = {key: value for key, value in result.items() if key not in {'animation_frames', 'baseline'}}
    if 'baseline' in result:
        summary['baseline'] = {key: value for key, value in result['baseline'].items() if key != 'archive_line_ending_only_paths'}
        summary['baseline']['archive_line_ending_only_files'] = len(result['baseline']['archive_line_ending_only_paths'])
    print('PHASE6_VERIFY_PASS: '+json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    main()
