# Source Package / 源代码包

This is the curated, rebuildable Architectury source package for JINZAI Traffic Lights 2.0.45 on Minecraft 1.20.1, targeting Fabric and Forge.

本目录是“津仔的交通灯”2.0.45在Minecraft 1.20.1上的Architectury整理版可构建源代码，同时输出Fabric与Forge版本。

## Modules / 模块

- `common/`: shared registrations, blocks, collision handling, client render setup, and all generated Minecraft resources.
- `fabric/`: Fabric entrypoints and `fabric.mod.json`.
- `forge/`: Forge entrypoint/client setup and `META-INF/mods.toml`.
- `tools/`: deterministic resource generator, resource verifier, translation sources, and historical compatibility checks.
- Raw Blockbench models, source textures, icon source artwork, Gradle Wrapper, README and copyright notice are retained. Private non-build documents and workbooks are excluded from the public source package.

- `common/`：共享注册、方块、碰撞逻辑、客户端渲染设置以及全部已生成Minecraft资源。
- `fabric/`：Fabric入口与`fabric.mod.json`。
- `forge/`：Forge入口、客户端初始化与`META-INF/mods.toml`。
- `tools/`：确定性资源生成器、资源校验器、翻译源和历史兼容性校验工具。
- 公开源码保留Blockbench模型、原始贴图、图标源图、Gradle Wrapper、README和版权说明；私有且不参与构建的说明文档与工作表不随公开源码包发布。

## Build / 构建

Use JDK 17 to run Gradle; compiled mod classes are fixed to Java 17 bytecode.

使用JDK 17运行Gradle；模组class输出固定为Java 17字节码。

```powershell
.\gradlew.bat clean build
```

Outputs / 输出：

```text
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.45.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.45.jar
```

## Regenerate and verify / 重新生成与校验

The commands below require separately maintained private naming workbooks and are retained for the complete private-source workflow. The public package can be built with Gradle using its committed generated resources, but cannot regenerate or run the full art audit by itself.

以下命令需要另行维护私有命名工作表，仅供私有完整源码工作流使用。公开包可使用已提交的生成资源通过Gradle构建，但无法单独重新生成资源或运行完整美术审计。

```powershell
python tools/generate_full_resources.py --private-input-root "<private-project-root>"
python tools/verify_full_resources.py --private-input-root "<private-project-root>"
python tools/verify_full_resources.py --private-input-root "<private-project-root>" fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.45.jar
python tools/verify_full_resources.py --private-input-root "<private-project-root>" forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.45.jar
```

Each of the 13 generated language files must contain exactly 234 block names plus 4 creative-tab names (238 keys) and no `tooltip.jinzai_traffic_lights.*` keys. The 15 animated textures must each retain a `frametime` of 10 ticks (2 FPS).

13个生成语言文件均必须恰好包含234个方块名称和4个创造标签页名称（共238键），且不得包含`tooltip.jinzai_traffic_lights.*`键。15个动态贴图必须各自保持`frametime`为10 tick（2 FPS）。

`verify_collision_hotfix_delta.py` remains a historical 1.0.31-to-1.0.32 collision audit. It is not the acceptance verifier for the Architectury 2.0.45 release.

`verify_collision_hotfix_delta.py`仅保留为1.0.31到1.0.32的历史碰撞修改审计工具，不作为Architectury 2.0.45的验收工具。

## Excluded from delivery / 交付时排除

Private non-build documents and workbooks, Gradle caches, build directories, run directories, logs, crash reports, Python caches, temporary review files and old release archives are excluded from the curated public source ZIP.

公开整理源码ZIP不包含私有且不参与构建的说明文档与工作表、Gradle缓存、构建目录、运行目录、日志、崩溃报告、Python缓存、临时审查文件和旧发布包。

## Phase four / 四期

`tools/translations/phase4_names.json` is the public mapping and translation source for all 21 new blocks. Original naming workbooks remain private; `--private-input-root` reads the seven earlier workbooks from a separate complete project without copying them into this repository.

四期21个新增方块以`tools/translations/phase4_names.json`维护素材映射与13语种名称。旧命名工作表仍属私有输入，`--private-input-root`可直接读取另存完整工程中的7张旧表，无需复制进公开仓库。四期新模型（含杆件）及c5/h30/h31替换模型均使用覆盖完整放置体积的单一外包箱；动态灯1/2只关闭帧插值，保持旧模型、旧贴图和10 tick帧间隔。

The supplied `bd_pole_18.bbmodel` retains `bd_pole_14` as its internal model and texture name. An explicit reader alias preserves the supplied model and PNG bytes while registering the workbook's `bd_pole_18` ID.

客户提供的`bd_pole_18.bbmodel`内部模型名和贴图名仍为`bd_pole_14`；读取时通过明确别名兼容，客户模型和PNG原始字节不变，注册ID按命名表保持`bd_pole_18`。

Optional compatibility verification against a 2.0.41 release JAR checks all 213 existing IDs, every old localized name, and the exact allowed old-resource changes:

可使用2.0.41正式JAR核对213个旧ID、全部旧本地化名称及允许变更的旧资源范围：

```powershell
python tools/verify_full_resources.py --private-input-root "<private-project-root>" --baseline "<2.0.41-release.jar>" "<2.0.45-candidate.jar>"
```
