# Source Package / 源代码包

This is the curated, rebuildable Architectury source package for JINZAI Traffic Lights 2.0.33 on Minecraft 1.20.1, targeting Fabric and Forge.

本目录是“津仔的交通灯”2.0.33在Minecraft 1.20.1上的Architectury整理版可构建源代码，同时输出Fabric与Forge版本。

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
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.33.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.33.jar
```

## Regenerate and verify / 重新生成与校验

The commands below require separately maintained private naming workbooks and are retained for the complete private-source workflow. The public package can be built with Gradle using its committed generated resources, but cannot regenerate or run the full art audit by itself.

以下命令需要另行维护私有命名工作表，仅供私有完整源码工作流使用。公开包可使用已提交的生成资源通过Gradle构建，但无法单独重新生成资源或运行完整美术审计。

```powershell
python tools/generate_full_resources.py
python tools/verify_full_resources.py
python tools/verify_full_resources.py fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.33.jar
python tools/verify_full_resources.py forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.33.jar
```

Each of the 13 generated language files must contain exactly 161 block names plus 4 creative-tab names (165 keys) and no `tooltip.jinzai_traffic_lights.*` keys.

13个生成语言文件均必须恰好包含161个方块名称和4个创造标签页名称（共165键），且不得包含`tooltip.jinzai_traffic_lights.*`键。

`verify_collision_hotfix_delta.py` remains a historical 1.0.31-to-1.0.32 collision audit. It is not the acceptance verifier for the Architectury 2.0.33 release.

`verify_collision_hotfix_delta.py`仅保留为1.0.31到1.0.32的历史碰撞修改审计工具，不作为Architectury 2.0.33的验收工具。

## Excluded from delivery / 交付时排除

Private non-build documents and workbooks, Gradle caches, build directories, run directories, logs, crash reports, Python caches, temporary review files and old release archives are excluded from the curated public source ZIP.

公开整理源码ZIP不包含私有且不参与构建的说明文档与工作表、Gradle缓存、构建目录、运行目录、日志、崩溃报告、Python缓存、临时审查文件和旧发布包。
