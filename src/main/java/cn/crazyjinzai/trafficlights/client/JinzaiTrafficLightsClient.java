/*
 * 本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
 */
package cn.crazyjinzai.trafficlights.client;

import cn.crazyjinzai.trafficlights.JinzaiTrafficLights;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.blockrenderlayer.v1.BlockRenderLayerMap;
import net.fabricmc.fabric.api.client.item.v1.ItemTooltipCallback;
import net.minecraft.client.render.RenderLayer;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.Identifier;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Map;

public final class JinzaiTrafficLightsClient implements ClientModInitializer {
    private static final String TOOLTIP_PREFIX =
        "tooltip." + JinzaiTrafficLights.MOD_ID + ".";

    public JinzaiTrafficLightsClient() {
    }

    @Override
    public void onInitializeClient() {
        JinzaiTrafficLights.getRegisteredBlocks().forEach(
            block -> BlockRenderLayerMap.INSTANCE.putBlock(block, RenderLayer.getCutout())
        );

        Map<Item, String> mutableCategories = new IdentityHashMap<>();
        addCategoryItems(
            mutableCategories,
            JinzaiTrafficLights.Category.FRAME,
            "frame"
        );
        addCategoryItems(
            mutableCategories,
            JinzaiTrafficLights.Category.INDICATOR,
            "indicator"
        );
        addCategoryItems(
            mutableCategories,
            JinzaiTrafficLights.Category.POLE,
            "pole"
        );
        addCategoryItems(
            mutableCategories,
            JinzaiTrafficLights.Category.ANNEX,
            "annex"
        );
        Map<Item, String> categories = Collections.unmodifiableMap(mutableCategories);

        ItemTooltipCallback.EVENT.register((stack, context, lines) -> {
            String category = categories.get(stack.getItem());
            if (category == null) {
                return;
            }

            Identifier itemId = Registries.ITEM.getId(stack.getItem());
            if (!JinzaiTrafficLights.MOD_ID.equals(itemId.getNamespace())) {
                return;
            }

            lines.add(Text.translatable(
                TOOLTIP_PREFIX + itemId.getPath() + ".description"
            ).formatted(Formatting.GRAY));
            lines.add(Text.translatable(
                TOOLTIP_PREFIX + "category." + category
            ).formatted(Formatting.DARK_GRAY));
            if ("indicator".equals(category)) {
                lines.add(Text.translatable(
                    TOOLTIP_PREFIX + "indicator.automation_limit"
                ).formatted(Formatting.DARK_GRAY));
            }
        });
    }

    private static void addCategoryItems(
        Map<Item, String> categories,
        JinzaiTrafficLights.Category category,
        String categoryKey
    ) {
        JinzaiTrafficLights.getBlocks(category).forEach(
            block -> categories.put(block.asItem(), categoryKey)
        );
    }
}
