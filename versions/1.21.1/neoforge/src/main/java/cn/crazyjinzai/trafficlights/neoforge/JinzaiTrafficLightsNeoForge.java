/*
 * 本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
 */
package cn.crazyjinzai.trafficlights.neoforge;

import cn.crazyjinzai.trafficlights.JinzaiTrafficLights;
import net.neoforged.fml.common.Mod;

@Mod(JinzaiTrafficLights.MOD_ID)
public final class JinzaiTrafficLightsNeoForge {
    public JinzaiTrafficLightsNeoForge() {
        // Architectury 13 obtains the NeoForge bus from the mod container.
        JinzaiTrafficLights.init();
    }
}
