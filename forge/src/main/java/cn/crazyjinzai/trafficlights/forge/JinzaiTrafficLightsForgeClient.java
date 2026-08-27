/*
 * 本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
 */
package cn.crazyjinzai.trafficlights.forge;

import cn.crazyjinzai.trafficlights.JinzaiTrafficLights;
import cn.crazyjinzai.trafficlights.client.JinzaiTrafficLightsClient;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

@Mod.EventBusSubscriber(
    modid = JinzaiTrafficLights.MOD_ID,
    bus = Mod.EventBusSubscriber.Bus.MOD,
    value = Dist.CLIENT
)
public final class JinzaiTrafficLightsForgeClient {
    private JinzaiTrafficLightsForgeClient() {
    }

    @SubscribeEvent
    public static void onClientSetup(FMLClientSetupEvent event) {
        event.enqueueWork(JinzaiTrafficLightsClient::init);
    }
}
