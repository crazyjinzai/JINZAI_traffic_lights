# Source Package / 源代码包

This is the curated, rebuildable source package for JINZAI Traffic Lights Fabric 1.20.1 v1.0.32.

本目录是“津仔的交通灯”Fabric 1.20.1 v1.0.32 的整理版可构建源代码。

## Included / 包含内容

- `src/`: Java source and all generated Minecraft resources.
- `tools/`: deterministic resource generator, verifier, and translation sources.
- `杆子/`, `红绿灯框架/`, `指示灯/`: all retained phase-one Blockbench models, textures, and name-mapping workbooks.
- `杆子（新增）/`, `红绿灯框架（新增）/`, `指示灯（新增）/`, `交通灯附属/`: all 58 phase-two model/texture pairs and their name-mapping workbooks.
- `gradle/`, `gradlew`, `gradlew.bat`: Gradle Wrapper.
- `build.gradle`, `settings.gradle`, `gradle.properties`: build configuration.
- The three DOCX requirement/update documents, `README.md`, and `COPYRIGHT.txt`.

- `src/`：Java 源码与全部已生成的 Minecraft 资源。
- `tools/`：可重复执行的资源生成器、校验器和翻译源文件。
- `杆子/`、`红绿灯框架/`、`指示灯/`：完整保留的一期 Blockbench 模型、贴图和名称映射表。
- `杆子（新增）/`、`红绿灯框架（新增）/`、`指示灯（新增）/`、`交通灯附属/`：二期 58 组模型、贴图和名称映射表。
- Gradle Wrapper、构建配置、三份需求/更新文档、README 和版权说明。

## Excluded / 已排除

Build output, Gradle caches, game run directories, logs, crash reports, Python caches, temporary review files, old JARs, and old release archives are not included.

不包含构建产物、Gradle 缓存、游戏运行目录、日志、崩溃报告、Python 缓存、临时审查文件、旧 JAR 和旧发布包。

## Build / 构建

```powershell
.\gradlew.bat clean build
```

The player-facing JAR is written to:

```text
build/libs/JINZAI_Trafficlights-Fabric-1.20.1-1.0.32.jar
```

## Regenerate and verify resources / 重新生成与校验资源

The Python tools use only the Python standard library. The compatibility and
hotfix-delta verifiers additionally accept baseline and candidate JAR paths.

```powershell
python tools/generate_full_resources.py
python tools/verify_full_resources.py
python tools/verify_phase1_compatibility.py <phase-one.jar> <1.0.32.jar>
python tools/verify_collision_hotfix_delta.py <1.0.31.jar> <1.0.32.jar>
```
