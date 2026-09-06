# JINZAI Traffic Lights

![JINZAI Traffic Lights thumbnail](common/src/main/resources/icon.png)

## English

Platforms: Fabric and Forge (shared Architectury codebase)  
Minecraft: 1.20.1  
Mod version: 2.0.41
Java bytecode: 17

This mod received art assets and funding support from "Crzay津仔", with technical implementation and production by "QiZhang". Copyright in the art assets belongs to "Crzay津仔"; copyright in the mod code and configuration belongs to "QiZhang".

### Introduction

JINZAI Traffic Lights is a decorative expansion mod for city building. Version 2.0.41 retains all 103 phase-one blocks and all 58 phase-two blocks, then adds 52 phase-three blocks, for 213 blocks in total:

- 59 traffic-light frames and frame components.
- 57 static indicators and decorative lights, plus 15 animated signal blocks.
- 72 poles and pole components.
- 10 illuminated, pass-through traffic-light accessories in their own **Traffic Light Accessories** creative tab.

All 161 phase-one and phase-two registry IDs and resources are retained from the 2.0.33 Architectury baseline. The 52 phase-three blocks are added to the existing frame, indicator and pole tabs; the accessories remain the only blocks with their own additional creative tab. The phase-three feature line began at 2.0.4; this bug-fix build is 2.0.41, and later bug-fix builds use 2.0.42 and so on.

Ten previously optimized complex models continue to use one enclosing box matching the complete placed model volume. The 28 new non-pole models also use one enclosing placed-volume box to keep targeting and adjacent placement responsive. The 24 new pole models retain a reduced model-following outline with coarser diagonal segments; the other 151 existing blocks retain their prior collision behavior.

Indicators and accessories remain illuminated and have no physical collision. The 15 new animated signals use vanilla synchronized texture animation at 2 FPS. They are decorative animations: independent per-block timing, functional countdowns, automatic traffic control and redstone-controlled signal logic are not included.

The mod provides localized block and creative-tab names in 13 languages and follows the language selected in Minecraft: English, Simplified Chinese, Spanish, Hindi, Arabic, French, Brazilian Portuguese, Russian, Indonesian, German, Japanese, Turkish and Korean. Items intentionally show only their localized names; no additional item tooltip notes are added.

### Installation

Fabric:

1. Install Fabric Loader 0.17.2 or a newer compatible release for Minecraft 1.20.1.
2. Install Fabric API 0.92.6+1.20.1 and Architectury API 9.0.6 through versions earlier than 10.0.0. The supplied and verified 9.2.14 release is recommended.
3. Put `JINZAI_Trafficlights-Fabric-1.20.1-2.0.41.jar` in the instance's `mods` folder.

Forge:

1. Install Forge 47.x for Minecraft 1.20.1.
2. Install Architectury API 9.0.6 through versions earlier than 10.0.0. The supplied and verified 9.2.14 release is recommended.
3. Put `JINZAI_Trafficlights-Forge-1.20.1-2.0.41.jar` in the instance's `mods` folder.

Remove older copies of this mod before launching so two JARs with the same mod ID are not loaded together.

### Build and verify

```powershell
.\gradlew.bat clean build
```

The public source retains the original art files and all pre-generated runtime
resources. Private non-build documents and workbooks are not part of the public
source package. The resource generator and full art audit remain in `tools/`
for development reference and require separately maintained private inputs;
they are not public-package acceptance commands.

Release JARs:

```text
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.41.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.41.jar
```

---

# 津仔的交通灯

## 中文

平台：Fabric 与 Forge（共享 Architectury 代码）  
Minecraft：1.20.1  
模组版本：2.0.41
Java 字节码：17

本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。

### 模组介绍

津仔的交通灯是一个面向城建装饰的扩展模组。2.0.41完整保留一期103个方块和二期58个方块，并新增三期52个方块，共213个：

- 59个红绿灯框架与框架部件。
- 57个静态指示灯与照明装饰，以及15个动态指示灯方块。
- 72个杆子与杆件部件。
- 10个发光且可穿透的交通灯附属，单独位于“交通灯附属”创造标签页。

一期与二期的161个注册ID和资源全部沿用2.0.33 Architectury基线。三期52个方块分别加入原有的框架、指示灯和杆子标签页；仍然只有交通灯附属使用单独新增的创造标签页。三期功能版本线始于2.0.4；本次BUG修复版本为2.0.41，后续修复依次采用2.0.42等追加一位的版本号。

此前已优化的10个复杂模型继续使用1个覆盖完整放置模型体积的外包碰撞箱。三期新增的28个非杆件模型也各使用1个覆盖放置后整体体积的碰撞外包箱，以避免准星选中和侧边放置时掉帧；24个新杆件保留经过适度简化的模型跟随轮廓，并对斜杆分段降复杂度。其余151个旧方块保持此前碰撞行为。

指示灯与交通灯附属保持发光且没有物理碰撞。15个新增动态指示灯使用原版同步纹理动画，以2 FPS播放。它们属于装饰动画，不包含每个方块独立计时、功能性倒计时、自动交通控制或红石控制信号逻辑。

模组提供13种语言的方块名称和创造标签页名称，并根据Minecraft当前语言自动切换：英语、简体中文、西班牙语、印地语、阿拉伯语、法语、巴西葡萄牙语、俄语、印度尼西亚语、德语、日语、土耳其语和韩语。物品按要求只显示本地化名称，不额外添加物品备注提示。

### 安装

Fabric：

1. 安装Minecraft 1.20.1对应的Fabric Loader 0.17.2或更高兼容版本。
2. 安装Fabric API 0.92.6+1.20.1和Architectury API 9.0.6至低于10.0.0的版本；随包提供且已经验证的9.2.14版本为推荐版本。
3. 将`JINZAI_Trafficlights-Fabric-1.20.1-2.0.41.jar`放入实例的`mods`文件夹。

Forge：

1. 安装Minecraft 1.20.1对应的Forge 47.x。
2. 安装Architectury API 9.0.6至低于10.0.0的版本；随包提供且已经验证的9.2.14版本为推荐版本。
3. 将`JINZAI_Trafficlights-Forge-1.20.1-2.0.41.jar`放入实例的`mods`文件夹。

启动前请移除本模组旧版本，避免同时加载两个具有相同模组ID的JAR。

### 构建与校验

```powershell
.\gradlew.bat clean build
```

公开源码保留原始美术文件和全部已生成运行资源。私有且不参与构建的说明文档与
工作表不属于公开源码包。`tools/`中的资源生成器和完整美术审计工具作为开发参考
保留，运行时需要另行维护私有输入，不作为公开源码包的验收命令。

正式JAR：

```text
fabric/build/libs/JINZAI_Trafficlights-Fabric-1.20.1-2.0.41.jar
forge/build/libs/JINZAI_Trafficlights-Forge-1.20.1-2.0.41.jar
```
