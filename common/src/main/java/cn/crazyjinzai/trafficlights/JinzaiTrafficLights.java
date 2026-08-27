/*
 * 本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
 */
package cn.crazyjinzai.trafficlights;

import cn.crazyjinzai.trafficlights.block.CatalogFacingBlock;
import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import dev.architectury.registry.CreativeTabRegistry;
import dev.architectury.registry.registries.DeferredRegister;
import dev.architectury.registry.registries.RegistrySupplier;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroup;
import net.minecraft.item.ItemStack;
import net.minecraft.registry.Registries;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.sound.BlockSoundGroup;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.Box;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class JinzaiTrafficLights {
    public static final String MOD_ID = "jinzai_traffic_lights";

    private static final String CATALOG_RESOURCE =
        "assets/" + MOD_ID + "/block_catalog.json";
    private static final int SUPPORTED_CATALOG_SCHEMA = 1;
    private static final Gson GSON = new Gson();

    private static final DeferredRegister<Block> BLOCKS =
        DeferredRegister.create(MOD_ID, RegistryKeys.BLOCK);
    private static final DeferredRegister<Item> ITEMS =
        DeferredRegister.create(MOD_ID, RegistryKeys.ITEM);
    private static final DeferredRegister<ItemGroup> ITEM_GROUPS =
        DeferredRegister.create(MOD_ID, RegistryKeys.ITEM_GROUP);

    private static volatile boolean initialized;
    private static List<RegistrySupplier<Block>> registeredBlockSuppliers = List.of();
    private static EnumMap<Category, List<RegistrySupplier<Block>>> blockSuppliersByCategory =
        emptyCategoryMap();
    private static EnumMap<Category, RegistrySupplier<ItemGroup>> itemGroups =
        new EnumMap<>(Category.class);

    private JinzaiTrafficLights() {
    }

    public static synchronized void init() {
        if (initialized) {
            return;
        }

        CatalogDocument document = loadCatalog();
        List<PreparedEntry> entries = validateCatalog(document);
        preflightRegistries(entries);

        EnumMap<Category, List<RegistrySupplier<Block>>> mutableByCategory = emptyCategoryMap();
        List<RegistrySupplier<Block>> mutableAllBlocks = new ArrayList<>(entries.size());
        List<RegisteredEntry> registeredEntries = new ArrayList<>(entries.size());

        for (PreparedEntry entry : entries) {
            RegistrySupplier<Block> block = BLOCKS.register(
                entry.identifier().getPath(),
                () -> createBlock(entry)
            );
            registeredEntries.add(new RegisteredEntry(entry, block));
            mutableAllBlocks.add(block);
            mutableByCategory.get(entry.category()).add(block);
        }

        EnumMap<Category, RegistrySupplier<ItemGroup>> mutableItemGroups =
            new EnumMap<>(Category.class);
        for (Category category : Category.values()) {
            List<RegistrySupplier<Block>> categoryBlocks = mutableByCategory.get(category);
            if (categoryBlocks.isEmpty()) {
                throw new IllegalStateException(
                    "Cannot create item group for empty category '"
                        + category.serializedName + "'"
                );
            }

            RegistrySupplier<ItemGroup> group = ITEM_GROUPS.register(
                category.serializedName,
                () -> CreativeTabRegistry.create(
                    Text.translatable(category.itemGroupTranslationKey()),
                    () -> new ItemStack(categoryBlocks.get(0).get())
                )
            );
            mutableItemGroups.put(category, group);
        }

        for (RegisteredEntry registeredEntry : registeredEntries) {
            PreparedEntry entry = registeredEntry.entry();
            RegistrySupplier<ItemGroup> group = mutableItemGroups.get(entry.category());
            ITEMS.register(
                entry.identifier().getPath(),
                () -> new BlockItem(
                    registeredEntry.block().get(),
                    new Item.Settings().arch$tab(group)
                )
            );
        }

        EnumMap<Category, List<RegistrySupplier<Block>>> immutableByCategory =
            emptyCategoryMap();
        for (Category category : Category.values()) {
            immutableByCategory.put(
                category,
                Collections.unmodifiableList(new ArrayList<>(mutableByCategory.get(category)))
            );
        }

        registeredBlockSuppliers = Collections.unmodifiableList(
            new ArrayList<>(mutableAllBlocks)
        );
        blockSuppliersByCategory = immutableByCategory;
        itemGroups = new EnumMap<>(mutableItemGroups);

        // Blocks must exist before creative-tab icons are created on Fabric.
        // Forge still defers each registry to its correct registry event.
        BLOCKS.register();
        ITEM_GROUPS.register();
        ITEMS.register();

        initialized = true;
    }

    public static List<Block> getRegisteredBlocks() {
        requireInitialized();
        return resolveBlocks(registeredBlockSuppliers);
    }

    public static List<Block> getBlocks(Category category) {
        requireInitialized();
        return resolveBlocks(blockSuppliersByCategory.get(category));
    }

    public static ItemGroup getFrameItemGroup() {
        return getItemGroup(Category.FRAME);
    }

    public static ItemGroup getIndicatorItemGroup() {
        return getItemGroup(Category.INDICATOR);
    }

    public static ItemGroup getPoleItemGroup() {
        return getItemGroup(Category.POLE);
    }

    public static ItemGroup getAnnexItemGroup() {
        return getItemGroup(Category.ANNEX);
    }

    public static Identifier id(String path) {
        return new Identifier(MOD_ID, path);
    }

    private static ItemGroup getItemGroup(Category category) {
        requireInitialized();
        return itemGroups.get(category).get();
    }

    private static List<Block> resolveBlocks(List<RegistrySupplier<Block>> suppliers) {
        List<Block> blocks = new ArrayList<>(suppliers.size());
        for (RegistrySupplier<Block> supplier : suppliers) {
            blocks.add(supplier.get());
        }
        return Collections.unmodifiableList(blocks);
    }

    private static CatalogDocument loadCatalog() {
        ClassLoader classLoader = JinzaiTrafficLights.class.getClassLoader();
        InputStream inputStream = classLoader.getResourceAsStream(CATALOG_RESOURCE);
        if (inputStream == null) {
            throw new IllegalStateException(
                "Missing required block catalog on the classpath: " + CATALOG_RESOURCE
            );
        }

        try (InputStream stream = inputStream;
             Reader reader = new InputStreamReader(stream, StandardCharsets.UTF_8)) {
            CatalogDocument document = GSON.fromJson(reader, CatalogDocument.class);
            if (document == null) {
                throw new IllegalStateException("Block catalog is empty: " + CATALOG_RESOURCE);
            }
            return document;
        } catch (JsonParseException exception) {
            throw new IllegalStateException(
                "Invalid JSON in block catalog " + CATALOG_RESOURCE + ": "
                    + exception.getMessage(),
                exception
            );
        } catch (IOException exception) {
            throw new IllegalStateException(
                "Could not read block catalog " + CATALOG_RESOURCE,
                exception
            );
        }
    }

    private static List<PreparedEntry> validateCatalog(CatalogDocument document) {
        if (document.schema != SUPPORTED_CATALOG_SCHEMA) {
            throw new IllegalStateException(
                "Unsupported block catalog schema " + document.schema
                    + "; expected " + SUPPORTED_CATALOG_SCHEMA
            );
        }
        if (document.blocks == null) {
            throw new IllegalStateException("Block catalog field 'blocks' is missing");
        }

        List<PreparedEntry> prepared = new ArrayList<>(document.blocks.size());
        Set<Identifier> identifiers = new HashSet<>();
        EnumMap<Category, Integer> categoryCounts = new EnumMap<>(Category.class);
        for (Category category : Category.values()) {
            categoryCounts.put(category, 0);
        }

        for (int index = 0; index < document.blocks.size(); index++) {
            CatalogEntry entry = document.blocks.get(index);
            if (entry == null) {
                throw catalogEntryError(index, "entry is null");
            }
            if (entry.id == null || entry.id.isBlank()) {
                throw catalogEntryError(index, "field 'id' is missing or blank");
            }
            if (entry.source_folder == null || entry.source_folder.isBlank()) {
                throw catalogEntryError(index, "field 'source_folder' is missing or blank");
            }
            if (entry.source_stem == null || entry.source_stem.isBlank()) {
                throw catalogEntryError(index, "field 'source_stem' is missing or blank");
            }

            Identifier identifier;
            try {
                identifier = id(entry.id);
            } catch (RuntimeException exception) {
                throw catalogEntryError(index, "invalid block id '" + entry.id + "'", exception);
            }
            if (!identifiers.add(identifier)) {
                throw catalogEntryError(index, "duplicate block id '" + identifier + "'");
            }

            Category category = Category.parse(entry.category, index);
            List<Box> boxes = validateBoxes(entry.collision_boxes, index, identifier);
            prepared.add(new PreparedEntry(identifier, category, boxes));
            categoryCounts.put(category, categoryCounts.get(category) + 1);
        }

        for (Category category : Category.values()) {
            if (categoryCounts.get(category) == 0) {
                throw new IllegalStateException(
                    "Block catalog contains no entries for required category '"
                        + category.serializedName + "'"
                );
            }
        }

        return Collections.unmodifiableList(prepared);
    }

    private static List<Box> validateBoxes(
        List<List<Double>> rawBoxes,
        int entryIndex,
        Identifier identifier
    ) {
        if (rawBoxes == null) {
            throw catalogEntryError(entryIndex, "field 'collision_boxes' is missing");
        }

        List<Box> boxes = new ArrayList<>(rawBoxes.size());
        for (int boxIndex = 0; boxIndex < rawBoxes.size(); boxIndex++) {
            List<Double> raw = rawBoxes.get(boxIndex);
            if (raw == null || raw.size() != 6) {
                throw catalogEntryError(
                    entryIndex,
                    "collision_boxes[" + boxIndex + "] for '" + identifier
                        + "' must contain exactly 6 numbers"
                );
            }

            double[] values = new double[6];
            for (int coordinate = 0; coordinate < values.length; coordinate++) {
                Double value = raw.get(coordinate);
                if (value == null || !Double.isFinite(value)) {
                    throw catalogEntryError(
                        entryIndex,
                        "collision_boxes[" + boxIndex + "][" + coordinate
                            + "] for '" + identifier + "' is not a finite number"
                    );
                }
                values[coordinate] = value / 16.0D;
            }

            if (values[0] >= values[3]
                || values[1] >= values[4]
                || values[2] >= values[5]) {
                throw catalogEntryError(
                    entryIndex,
                    "collision_boxes[" + boxIndex + "] for '" + identifier
                        + "' has non-positive size"
                );
            }

            boxes.add(new Box(
                values[0], values[1], values[2],
                values[3], values[4], values[5]
            ));
        }
        return Collections.unmodifiableList(boxes);
    }

    private static void preflightRegistries(List<PreparedEntry> entries) {
        for (PreparedEntry entry : entries) {
            if (Registries.BLOCK.containsId(entry.identifier())) {
                throw new IllegalStateException(
                    "Cannot register catalog block because the block id already exists: "
                        + entry.identifier()
                );
            }
            if (Registries.ITEM.containsId(entry.identifier())) {
                throw new IllegalStateException(
                    "Cannot register catalog block item because the item id already exists: "
                        + entry.identifier()
                );
            }
        }

        for (Category category : Category.values()) {
            Identifier groupId = id(category.serializedName);
            if (Registries.ITEM_GROUP.containsId(groupId)) {
                throw new IllegalStateException(
                    "Cannot register item group because the id already exists: " + groupId
                );
            }
        }
    }

    private static Block createBlock(PreparedEntry entry) {
        return switch (entry.category()) {
            case FRAME, POLE -> new CatalogFacingBlock(
                AbstractBlock.Settings.create()
                    .strength(1.5F, 6.0F)
                    .sounds(BlockSoundGroup.METAL)
                    .nonOpaque(),
                entry.boxes(),
                true
            );
            case INDICATOR, ANNEX -> new CatalogFacingBlock(
                AbstractBlock.Settings.create()
                    .strength(0.3F)
                    .sounds(BlockSoundGroup.GLASS)
                    .luminance(state -> 15)
                    .noCollision()
                    .nonOpaque(),
                entry.boxes(),
                false
            );
        };
    }

    private static EnumMap<Category, List<RegistrySupplier<Block>>> emptyCategoryMap() {
        EnumMap<Category, List<RegistrySupplier<Block>>> map =
            new EnumMap<>(Category.class);
        for (Category category : Category.values()) {
            map.put(category, new ArrayList<>());
        }
        return map;
    }

    private static void requireInitialized() {
        if (!initialized) {
            throw new IllegalStateException(
                "JinzaiTrafficLights has not completed its common initialization"
            );
        }
    }

    private static IllegalStateException catalogEntryError(int index, String message) {
        return new IllegalStateException("Invalid block catalog entry " + index + ": " + message);
    }

    private static IllegalStateException catalogEntryError(
        int index,
        String message,
        Throwable cause
    ) {
        return new IllegalStateException(
            "Invalid block catalog entry " + index + ": " + message,
            cause
        );
    }

    public enum Category {
        FRAME("frame"),
        INDICATOR("indicator"),
        POLE("pole"),
        ANNEX("annex");

        private final String serializedName;

        Category(String serializedName) {
            this.serializedName = serializedName;
        }

        private String itemGroupTranslationKey() {
            return "itemGroup." + MOD_ID + "." + serializedName;
        }

        private static Category parse(String value, int entryIndex) {
            if (value == null || value.isBlank()) {
                throw catalogEntryError(entryIndex, "field 'category' is missing or blank");
            }
            String normalized = value.toLowerCase(Locale.ROOT);
            for (Category category : values()) {
                if (category.serializedName.equals(normalized)) {
                    return category;
                }
            }
            throw catalogEntryError(entryIndex, "unknown category '" + value + "'");
        }
    }

    private record PreparedEntry(
        Identifier identifier,
        Category category,
        List<Box> boxes
    ) {
    }

    private record RegisteredEntry(
        PreparedEntry entry,
        RegistrySupplier<Block> block
    ) {
    }

    private static final class CatalogDocument {
        private int schema;
        private List<CatalogEntry> blocks;
    }

    private static final class CatalogEntry {
        private String id;
        private String category;
        private String source_folder;
        private String source_stem;
        private List<List<Double>> collision_boxes;
    }
}
