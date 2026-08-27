/*
 * 本模组由"Crzay津仔"提供美术与资金支持，"QiZhang"提供技术实现与制作。发布署名仅为"Crzay津仔"，美术素材版权归 "Crzay津仔"所有，模组代码/配置版权归"QiZhang"所有。
 */
package cn.crazyjinzai.trafficlights.block;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.HorizontalFacingBlock;
import net.minecraft.block.ShapeContext;
import net.minecraft.item.ItemPlacementContext;
import net.minecraft.state.StateManager;
import net.minecraft.util.BlockMirror;
import net.minecraft.util.BlockRotation;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Box;
import net.minecraft.util.math.Direction;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.util.shape.VoxelShapes;
import net.minecraft.world.BlockView;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;

@SuppressWarnings("deprecation")
public final class CatalogFacingBlock extends HorizontalFacingBlock {
    private final EnumMap<Direction, VoxelShape> modelShapes;
    private final boolean hasPhysicalCollision;

    public CatalogFacingBlock(
        Settings settings,
        List<Box> northBoxes,
        boolean hasPhysicalCollision
    ) {
        super(settings);
        this.modelShapes = createDirectionalShapes(northBoxes);
        this.hasPhysicalCollision = hasPhysicalCollision;
        setDefaultState(getStateManager().getDefaultState().with(FACING, Direction.NORTH));
    }

    @Override
    public BlockState getPlacementState(ItemPlacementContext context) {
        return getDefaultState().with(FACING, context.getHorizontalPlayerFacing().getOpposite());
    }

    @Override
    public BlockState rotate(BlockState state, BlockRotation rotation) {
        return state.with(FACING, rotation.rotate(state.get(FACING)));
    }

    @Override
    public BlockState mirror(BlockState state, BlockMirror mirror) {
        return state.rotate(mirror.getRotation(state.get(FACING)));
    }

    @Override
    protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
        builder.add(FACING);
    }

    @Override
    public VoxelShape getOutlineShape(
        BlockState state,
        BlockView world,
        BlockPos position,
        ShapeContext context
    ) {
        return shapeFor(state);
    }

    @Override
    public VoxelShape getCollisionShape(
        BlockState state,
        BlockView world,
        BlockPos position,
        ShapeContext context
    ) {
        return hasPhysicalCollision ? shapeFor(state) : VoxelShapes.empty();
    }

    private VoxelShape shapeFor(BlockState state) {
        VoxelShape shape = modelShapes.get(state.get(FACING));
        return shape == null ? modelShapes.get(Direction.NORTH) : shape;
    }

    private static EnumMap<Direction, VoxelShape> createDirectionalShapes(List<Box> northBoxes) {
        EnumMap<Direction, VoxelShape> shapes = new EnumMap<>(Direction.class);
        if (northBoxes.isEmpty()) {
            VoxelShape fullCube = VoxelShapes.fullCube();
            shapes.put(Direction.NORTH, fullCube);
            shapes.put(Direction.EAST, fullCube);
            shapes.put(Direction.SOUTH, fullCube);
            shapes.put(Direction.WEST, fullCube);
            return shapes;
        }

        List<Box> boxes = List.copyOf(northBoxes);
        shapes.put(Direction.NORTH, union(boxes));
        boxes = rotateClockwise(boxes);
        shapes.put(Direction.EAST, union(boxes));
        boxes = rotateClockwise(boxes);
        shapes.put(Direction.SOUTH, union(boxes));
        boxes = rotateClockwise(boxes);
        shapes.put(Direction.WEST, union(boxes));
        return shapes;
    }

    private static VoxelShape union(List<Box> boxes) {
        if (boxes.isEmpty()) {
            return VoxelShapes.empty();
        }

        // Merge as a balanced tree.  Sequentially adding hundreds of fine
        // diagonal boxes repeatedly simplifies an ever-growing voxel grid and
        // makes startup quadratic; pairing similarly sized shapes keeps the
        // precise outline while making initialization practical.
        List<VoxelShape> level = new ArrayList<>(boxes.size());
        for (Box box : boxes) {
            level.add(VoxelShapes.cuboid(box));
        }

        while (level.size() > 1) {
            List<VoxelShape> next = new ArrayList<>((level.size() + 1) / 2);
            for (int index = 0; index < level.size(); index += 2) {
                if (index + 1 == level.size()) {
                    next.add(level.get(index));
                } else {
                    next.add(VoxelShapes.union(level.get(index), level.get(index + 1)));
                }
            }
            level = next;
        }
        return level.get(0);
    }

    private static List<Box> rotateClockwise(List<Box> boxes) {
        return boxes.stream().map(CatalogFacingBlock::rotateClockwise).toList();
    }

    private static Box rotateClockwise(Box box) {
        // x' = 1 - z and z' = x rotates around the block center (0.5, 0.5).
        // The formula intentionally does not clamp, so overhanging model boxes remain exact.
        return new Box(
            1.0D - box.maxZ,
            box.minY,
            box.minX,
            1.0D - box.minZ,
            box.maxY,
            box.maxX
        );
    }
}
