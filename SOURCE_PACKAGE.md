# Source Package / 源代码包

This curated, rebuildable source package contains JINZAI Traffic Lights 2.0.46 for Minecraft 1.20.1 (Fabric / Forge, Java 17) and Minecraft 1.21.1 (Fabric / NeoForge, Java 21).

本目录为“津仔的交通灯”2.0.46整理版可构建源码，包含Minecraft 1.20.1的Fabric / Forge（Java 17）以及Minecraft 1.21.1的Fabric / NeoForge（Java 21）。

## Modules / 模块

- `common/`: shared registrations, blocks, collision handling, client render setup, and all generated Minecraft resources.
- `fabric/`: Fabric entrypoints and `fabric.mod.json`.
- `forge/`: Forge entrypoint/client setup and `META-INF/mods.toml`.
- `tools/`: deterministic resource generator, resource verifier, translation sources, and historical compatibility checks.
- `versions/1.21.1/`: independent Java 21 project and its Gradle Wrapper; reads shared art and generated resources from the repository root.
- Raw Blockbench models, source textures, icon source artwork, Gradle Wrapper, README and copyright notice are retained. Private non-build documents and workbooks are excluded from the public source package.

- `common/`：共享注册、方块、碰撞逻辑、客户端渲染设置以及全部已生成Minecraft资源。
- `fabric/`：Fabric入口与`fabric.mod.json`。
- `forge/`：Forge入口、客户端初始化与`META-INF/mods.toml`。
- `tools/`：确定性资源生成器、资源校验器、翻译源和历史兼容性校验工具。
- `versions/1.21.1/`：Java 21独立工程及其Gradle Wrapper，直接读取仓库根目录公共美术和生成资源。
- 公开源码保留Blockbench模型、原始贴图、图标源图、Gradle Wrapper、README和版权说明；私有且不参与构建的说明文档与工作表不随公开源码包发布。

## Build / 构建

Use JDK 17 to run Gradle; compiled mod classes are fixed to Java 17 bytecode.

使用JDK 17运行Gradle；模组class输出固定为Java 17字节码。

```powershell
.\gradlew.bat clean build
```

Outputs / 输出：

```text
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.46.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.46.jar
```

For Minecraft 1.21.1, select JDK 21, enter `versions/1.21.1`, and run its `gradlew.bat clean build`. Keep the full repository tree: this subproject needs the root `common/src/main/resources` and `LICENSE`.

构建Minecraft 1.21.1时，切换至JDK 21、进入`versions/1.21.1`，运行该目录的`gradlew.bat clean build`。请保留完整仓库结构，子工程需要读取根目录的`common/src/main/resources`和`LICENSE`。

```text
versions/1.21.1/fabric/build/libs/JINZAI_Trafficlights-Fabric-1.21.1-2.0.46.jar
versions/1.21.1/neoforge/build/libs/JINZAI_Trafficlights-NeoForge-1.21.1-2.0.46.jar
```

## Regenerate and verify / 重新生成与校验

The commands below require separately maintained private naming workbooks and are retained for the complete private-source workflow. The public package can be built with Gradle using its committed generated resources, but cannot regenerate or run the full art audit by itself.

以下命令需要另行维护私有命名工作表，仅供私有完整源码工作流使用。公开包可使用已提交的生成资源通过Gradle构建，但无法单独重新生成资源或运行完整美术审计。

```powershell
python tools/generate_full_resources.py --private-input-root "<private-project-root>"
python tools/verify_full_resources.py --private-input-root "<private-project-root>"
python tools/verify_full_resources.py --private-input-root "<private-project-root>" fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.46.jar
python tools/verify_full_resources.py --private-input-root "<private-project-root>" forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.46.jar
```

Each of the 13 generated language files must contain exactly 261 block names plus 4 creative-tab names (265 keys) and no `tooltip.jinzai_traffic_lights.*` keys. The 31 animated textures must each retain a `frametime` of 10 ticks (2 FPS).

13个生成语言文件均必须恰好包含261个方块名称和4个创造标签页名称（共265键），且不得包含`tooltip.jinzai_traffic_lights.*`键。31个动态贴图必须各自保持`frametime`为10 tick（2 FPS）。

`verify_collision_hotfix_delta.py` remains a historical 1.0.31-to-1.0.32 collision audit. It is not the acceptance verifier for the Architectury 2.0.46 release.

`verify_collision_hotfix_delta.py`仅保留为1.0.31到1.0.32的历史碰撞修改审计工具，不作为Architectury 2.0.46的验收工具。

## Excluded from delivery / 交付时排除

Private non-build documents and workbooks, Gradle caches, build directories, run directories, logs, crash reports, Python caches, temporary review files and old release archives are excluded from the curated public source ZIP.

公开整理源码ZIP不包含私有且不参与构建的说明文档与工作表、Gradle缓存、构建目录、运行目录、日志、崩溃报告、Python缓存、临时审查文件和旧发布包。

## Phase four / 四期

`tools/translations/phase4_names.json` is the public mapping and translation source for all 21 new blocks. Original naming workbooks remain private; `--private-input-root` reads the seven earlier workbooks from a separate complete project without copying them into this repository.

四期21个新增方块以`tools/translations/phase4_names.json`维护素材映射与13语种名称。旧命名工作表仍属私有输入，`--private-input-root`可直接读取另存完整工程中的7张旧表，无需复制进公开仓库。四期新模型（含杆件）及c5/h30/h31替换模型均使用覆盖完整放置体积的单一外包箱；动态灯1/2只关闭帧插值，保持旧模型、旧贴图和10 tick帧间隔。

The supplied `bd_pole_18.bbmodel` retains `bd_pole_14` as its internal model and texture name. An explicit reader alias preserves the supplied model and PNG bytes while registering the workbook's `bd_pole_18` ID.

客户提供的`bd_pole_18.bbmodel`内部模型名和贴图名仍为`bd_pole_14`；读取时通过明确别名兼容，客户模型和PNG原始字节不变，注册ID按命名表保持`bd_pole_18`。

Optional compatibility verification against a 2.0.45 release JAR checks all 234 existing IDs, every old localized name, and byte-identical old model, texture, blockstate, item and loot resources:

可使用2.0.45正式JAR核对234个旧ID、全部旧本地化名称，以及完全不变的旧模型、贴图、方块状态、物品和掉落资源：

```powershell
python tools/verify_full_resources.py --private-input-root "<private-project-root>" --baseline "<2.0.45-release.jar>" "<2.0.46-candidate.jar>"
```

## Phase five / 五期

`tools/translations/phase5_names.json` contains all 27 public source mappings and 13-language names. The two private naming workbooks are not required for a normal Gradle build. The 11 poles and 16 animated indicators retain the established categories; each new model uses one placed-volume bounding box. Indicators remain pass-through.

五期新增11个限高杆件和16个动态指示灯，公开映射及13语种名称位于`tools/translations/phase5_names.json`。两张私有命名表不参与普通Gradle构建，也不进入公开源码。27个新模型均采用完整放置体积的单一外包箱，动态指示灯维持无物理碰撞的选择箱规则。

All 16 new animation strips contain 144 frames with `frametime: 10`, no interpolation and a 72-second loop. Source art is preserved byte-for-byte. Explicit texture-name aliases accommodate the supplied internal names `jinzai_daynamic_light_16a` and `height_limit_bar_6a` in models 16a and 6b. Null-texture faces are intentionally omitted, as in Blockbench Java export; four hidden placeholders are excluded.

16张新动画均为144帧、每帧10 tick、无插值，完整循环72秒。原始美术文件逐字节保留；16a和6b素材中的历史内部纹理名通过明确读取别名兼容。原素材中69个`texture: null`面按Blockbench语义不导出，4个隐藏占位元素被排除，不会额外补面或修改贴图。
