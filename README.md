# JINZAI Traffic Lights

![JINZAI Traffic Lights thumbnail](common/src/main/resources/icon.png)

## English

Mod version: 2.1.50 on all four platforms.

| Minecraft | Loaders | Java | Source project |
|---|---|---|---|
| 1.20.1 | Fabric / Forge | 17 | Repository root |
| 1.21.1 | Fabric / NeoForge | 21 | [versions/1.21.1](versions/1.21.1/README.md) |

This mod received art assets and funding support from "Crzay津仔", with technical implementation and production by "QiZhang". Copyright in the art assets belongs to "Crzay津仔"; copyright in the mod code and configuration belongs to "QiZhang".

The project's original code, configuration, documentation, models, textures and other artwork are licensed under the [MIT License](LICENSE). Copyright ownership and credits remain unchanged; third-party components retain their respective licenses.

### Introduction

JINZAI Traffic Lights is a decorative expansion mod for city building. Version 2.1.50 keeps all 261 existing registry IDs, adds 73 phase-six blocks, and replaces 44 existing frame models. There are 334 blocks in total:

- 89 traffic-light frames and frame components.
- 71 static indicators and decorative lights, plus 37 animated signal blocks.
- 117 poles and pole components.
- 20 pass-through traffic-light accessories.

Phase six adds 24 frames, 14 indicators (including six animated signals), 29 poles and six accessories. All additions use the four established creative tabs. The 217 unchanged older blocks retain their models, textures and collision behavior; all older IDs, names and animation strips are preserved.

Every phase-six addition and replacement uses one axis-aligned bounding box enclosing the complete placed model volume. Indicators and accessories have no physical collision; their boxes are used for selection. The new cylindrical camera emits light at level 15; the five other new accessories emit no light, as specified in the supplied naming table. Older lighting behavior is preserved.

The 37 animated signals use vanilla synchronized texture animation at 2 FPS. Each of the six new strips has 144 frames at 10 ticks per frame, for a 72-second loop. Independent per-block timing, functional countdowns, automatic traffic control and redstone-controlled signals are not included.

The existing corrections that fit and center 26 older inventory icons within their slots are retained. These corrections affect only the GUI display transform; supplied art, placed models, textures, animation and collision boxes are unchanged. The explicit corrections are maintained in `tools/gui_display_overrides.json`.

The mod provides localized block and creative-tab names in 13 languages and follows the language selected in Minecraft: English, Simplified Chinese, Spanish, Hindi, Arabic, French, Brazilian Portuguese, Russian, Indonesian, German, Japanese, Turkish and Korean. Items intentionally show only their localized names; no additional item tooltip notes are added.

### Installation

The following Fabric / Forge instructions are for Minecraft 1.20.1. For Minecraft 1.21.1, use Java 21 and either Fabric Loader 0.17.2 with Fabric API 0.116.15+1.21.1, or NeoForge 21.1.248; both require Architectury API 13.0.8 (13.x). See the [1.21.1 project](versions/1.21.1/README.md) for the corresponding JAR names. Dependencies must match both Minecraft and the loader.

Fabric:

1. Install Fabric Loader 0.17.2 or a newer compatible release for Minecraft 1.20.1.
2. Separately install Fabric API 0.92.6+1.20.1 and Architectury API 9.0.6 through versions earlier than 10.0.0. Testing used Architectury API 9.2.14; dependencies are not bundled in the release JARs.
3. Put `JINZAI_Trafficlights-Fabric-1.20.1-2.1.50.jar` in the instance's `mods` folder.

Forge:

1. Install Forge 47.x for Minecraft 1.20.1.
2. Separately install Architectury API 9.0.6 through versions earlier than 10.0.0. Testing used Architectury API 9.2.14; dependencies are not bundled in the release JARs.
3. Put `JINZAI_Trafficlights-Forge-1.20.1-2.1.50.jar` in the instance's `mods` folder.

Remove older copies of this mod before launching so two JARs with the same mod ID are not loaded together.

### Build and verify

```powershell
.\gradlew.bat clean build
```

This builds Minecraft 1.20.1 using JDK 17. To build Minecraft 1.21.1, select JDK 21, change to `versions/1.21.1`, then run that project's `gradlew.bat clean build`.

The public source contains the original art, generated resources and the complete
`tools/block_manifest.json` mapping. Resource generation and verification require
Python 3.11 or newer and the standard library; private workbooks are not required:

```powershell
python tools/generate_full_resources.py
python tools/verify_full_resources.py
```

Private documents, workbooks, runtime data and build caches are excluded from the source package.

Release JARs:

```text
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.1.50.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.1.50.jar
```

---

# 津仔的交通灯

## 中文

四端模组版本统一为2.1.50。

| Minecraft | 加载器 | Java | 源码工程 |
|---|---|---|---|
| 1.20.1 | Fabric / Forge | 17 | 仓库根目录 |
| 1.21.1 | Fabric / NeoForge | 21 | [versions/1.21.1](versions/1.21.1/README.md) |

本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。

本项目自身的代码、配置、文档、模型、贴图及其他美术素材采用 [MIT 许可证](LICENSE)。版权归属和署名保持不变；第三方组件保留各自的许可证。

### 模组介绍

津仔的交通灯是一个面向城建装饰的扩展模组。2.1.50保留全部261个旧注册ID，新增六期73个方块、替换44个旧框架模型，总计334个方块：

- 89个红绿灯框架与框架部件。
- 71个静态指示灯与照明装饰，以及37个动态指示灯。
- 117个杆子与杆件部件。
- 20个可穿透的交通灯附属。

六期新增24个框架、14个指示灯（其中6个动态）、29个杆件和6个附属，沿用原有4个创造分类。217个未修改旧方块保留原有模型、贴图和碰撞；全部旧ID、名称及动画贴图均保留。

本期新增和替换模型均使用覆盖放置后完整体积的单一轴对齐外包箱。指示灯和附属没有物理碰撞，外包箱用于准星选中。按素材命名表，新增圆筒摄像头亮度为15，其余五个新附属不发光；旧方块照明行为保持不变。

37组动态指示灯使用原版同步纹理动画，以2 FPS播放。六组新动画各144帧、每帧10 tick、完整循环72秒。它们属于装饰动画，不包含每个方块独立计时、功能性倒计时、自动交通控制或红石控制逻辑。

保留此前26个旧物品图标的缩小和居中修复，避免图标跨出物品格。仅修改GUI展示变换，原始美术、放置后的模型、贴图、动画和碰撞箱均保持原样。明确的展示覆盖配置保存在`tools/gui_display_overrides.json`。

模组提供13种语言的方块名称和创造标签页名称，并根据Minecraft当前语言自动切换：英语、简体中文、西班牙语、印地语、阿拉伯语、法语、巴西葡萄牙语、俄语、印度尼西亚语、德语、日语、土耳其语和韩语。物品按要求只显示本地化名称，不额外添加物品备注提示。

### 安装

下方Fabric / Forge步骤适用于Minecraft 1.20.1。Minecraft 1.21.1需要Java 21，可选择Fabric Loader 0.17.2与Fabric API 0.116.15+1.21.1，或NeoForge 21.1.248；两端均需Architectury API 13.0.8（13.x）。对应JAR名称见[1.21.1工程说明](versions/1.21.1/README.md)，依赖文件必须匹配Minecraft版本及加载器。

Fabric：

1. 安装Minecraft 1.20.1对应的Fabric Loader 0.17.2或更高兼容版本。
2. 另行安装Fabric API 0.92.6+1.20.1和Architectury API 9.0.6至低于10.0.0的版本；测试使用Architectury API 9.2.14，Release JAR不内置这些依赖。
3. 将`JINZAI_Trafficlights-Fabric-1.20.1-2.1.50.jar`放入实例的`mods`文件夹。

Forge：

1. 安装Minecraft 1.20.1对应的Forge 47.x。
2. 另行安装Architectury API 9.0.6至低于10.0.0的版本；测试使用Architectury API 9.2.14，Release JAR不内置这些依赖。
3. 将`JINZAI_Trafficlights-Forge-1.20.1-2.1.50.jar`放入实例的`mods`文件夹。

启动前请移除本模组旧版本，避免同时加载两个具有相同模组ID的JAR。

### 构建与校验

```powershell
.\gradlew.bat clean build
```

上述命令在仓库根目录使用JDK 17构建Minecraft 1.20.1。构建Minecraft 1.21.1时，切换至JDK 21并进入`versions/1.21.1`，再运行该目录的`gradlew.bat clean build`。

公开源码包含原始美术、生成资源及完整的`tools/block_manifest.json`映射表。
Python 3.11及以上版本可运行`python tools/generate_full_resources.py`和
`python tools/verify_full_resources.py`重新生成和校验，无需私有工作表或额外Python依赖。
源码包排除私有文档、工作表、运行数据和构建缓存。

正式JAR：

```text
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.1.50.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.1.50.jar
```
