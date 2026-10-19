# JINZAI Traffic Lights 2.0.46 — Minecraft 1.21.1

This independent Architectury project builds Fabric and NeoForge versions with
Java 21. Run `gradlew clean build` from this directory. The Minecraft 1.20.1
project remains at the repository root.

Models, textures, animation metadata, block catalog, 13 translations and icon
are read directly from the repository's `common/src/main/resources` at build
time. No separate art copy is maintained here. Processing only updates the
Minecraft 1.21 resource/data layout: resource format 34, data format 48 (both
accepted by `supported_formats`), `loot_table`, `tags/block`,
and corresponding singular data registry folders. Catalog entries register
automatically in the four existing creative tabs.

Requires Minecraft 1.21.1, Java 21 and Architectury 13.0.8 (13.x). Fabric uses
Loader 0.17.2 and Fabric API 0.116.15+1.21.1. NeoForge uses 21.1.248. Dependencies
must be installed separately; install only the JAR matching your loader.

- `fabric/build/libs/JINZAI_Trafficlights-Fabric-1.21.1-2.0.46.jar`
- `neoforge/build/libs/JINZAI_Trafficlights-NeoForge-1.21.1-2.0.46.jar`

本目录为 Minecraft 1.21.1 / Java 21 独立移植工程，提供 Fabric 和 NeoForge。
在本目录运行 `gradlew clean build`。模型、贴图、动画、目录、语言和图标在构建时直接
读取仓库根目录的公共资源，只转换 1.21 所需的数据目录及 pack 格式，不另行维护素材。
方块朝向、选框、碰撞、发光、四个创造分类及不增加自定义 Tooltip 的行为保持一致。
指示灯及附属为发光、可穿透装饰方块；不添加红石控制或独立交通计时逻辑。

本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。
发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
项目自身内容采用仓库根目录的 MIT 许可证，第三方内容保留各自许可证。

References: [Architectury NeoForge migration](https://docs.architectury.dev/loom/neoforge_migration/),
[NeoForge 1.21.1 setup](https://docs.neoforged.net/docs/1.21.1/gettingstarted/),
[Fabric Yarn 1.21.1](https://maven.fabricmc.net/docs/yarn-1.21.1+build.3/).
