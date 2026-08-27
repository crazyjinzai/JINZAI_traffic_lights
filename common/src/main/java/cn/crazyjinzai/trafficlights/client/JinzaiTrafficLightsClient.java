/*
 * 本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
 */
package cn.crazyjinzai.trafficlights.client;

import cn.crazyjinzai.trafficlights.JinzaiTrafficLights;
import dev.architectury.registry.client.rendering.RenderTypeRegistry;
import net.minecraft.block.Block;
import net.minecraft.client.render.RenderLayer;

import java.util.List;

public final class JinzaiTrafficLightsClient {
    private static boolean initialized;

    private JinzaiTrafficLightsClient() {
    }

    public static synchronized void init() {
        if (initialized) {
            return;
        }

        List<Block> blocks = JinzaiTrafficLights.getRegisteredBlocks();
        RenderTypeRegistry.register(RenderLayer.getCutout(), blocks.toArray(Block[]::new));
        initialized = true;
    }
}
