"""Make CAD models for a solenoid housing that uses solenoids to lift dots.

This design is characterized by the pins locking with a sliding stencil
mechanism.

* Magnets will interface with the solenoids.
* Magnets will move complex cylindrical parts up and down.
* A sliding SMD soldering mask, controlled by motors or beefy solenoids, will
    slide about 1mm side-to-side, and will lock the pins.

Stackup:
    1. PCB + Solenoids
    2. Housing Bottom
    3. Metal Sheet
    4. Housing Top
    5. Dots [not really part of the stackup]
"""

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Literal

import build123d as bd
import build123d_ease as bde
from build123d_ease import evenly_space_with_center, show
from loguru import logger


@dataclass
class GeneralSpec:
    """Specification to be used across all parts."""

    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    cell_pitch_x: float = 6.0

    dot_hole_diameter: float = 1.7
    dot_diameter: float = 1.6

    cell_count_x = 4
    cell_count_y = 1

    # Distance from outer dots to mounting holes.
    x_dist_to_mounting_holes: float = 5.0

    border_y: float = 4.0

    mounting_hole_spacing_y: float = 3
    mounting_hole_diameter: float = 2.0
    housing_x_size_past_mounting_hole_center: float = 2.5
    mounting_hole_peg_diameter: float = 1.8
    mounting_hole_peg_length: float = 1.5

    # Distance the dot expects to travel.
    dot_travel_distance: float = 1.0
    dot_min_diameter: float = 1.0
    dot_cones_height: float = 0.4

    dot_magnet_diameter: float = 1.0
    dot_magnet_height: float = 1.0

    # Distance from the top of the magnet to the Z=0 plane.
    dot_magnet_top_dist_below_z0: float = 0.4  # Start around bottom of cone.

    # Must be equal to the `dot_travel_distance`, it seems.
    dot_ui_length: float = 1
    dot_ui_round_radius: float = 0.6

    stencil_thickness: float = 0.25  # Actually 0.15, but leave some space.
    # Contact between top and bottom housing.
    border_around_stencil_x: float = 1.6
    border_around_stencil_y: float = 2
    stencil_gripper_width_y = 3
    stencil_gripper_spacing_y = 5.8
    stencil_gripped_extension_x: float = 15

    solenoid_protrusion_from_pcb: float = 2
    solenoid_clearance_diameter: float = 3

    # Pegs from the top housing to the bottom housing.
    top_to_bottom_pegs_diameter: float = 1.5
    top_to_bottom_pegs_diameter_id: float = 1.7
    top_to_bottom_pegs_length: float = 2  # Must go through stencil.
    top_to_bottom_pegs_border_x: float = 4.5
    top_to_bottom_pegs_border_y: float = 4

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert self.dot_cones_height * 2 <= self.dot_total_length

        stencil_gripper_gap_width = (
            self.stencil_gripper_spacing_y - self.stencil_gripper_width_y
        )
        assert stencil_gripper_gap_width > self.mounting_hole_diameter

        assert self.top_to_bottom_pegs_border_x > self.border_around_stencil_x
        assert self.top_to_bottom_pegs_border_y > self.border_around_stencil_y

        info = {
            "mounting_hole_spacing_x": self.mounting_hole_spacing_x,
            "top_housing_thickness": self.top_housing_thickness,
            "bottom_housing_thickness": self.bottom_housing_thickness,
            "dot_total_length": self.dot_total_length,
            "total_housing_x": self.total_housing_x,
            "total_housing_y": self.total_housing_y,
            "total_housing_z": self.total_housing_z,
        }
        logger.success(info)

    @property
    def dot_total_length(self) -> float:
        """Total length of the braille dot."""
        # Bottom to top.
        return (
            self.dot_magnet_height
            + self.dot_magnet_top_dist_below_z0
            + self.dot_travel_distance
            + self.dot_cones_height
            + self.dot_ui_length
        )

    @property
    def total_housing_x(self) -> float:
        """Total width of the braille housing."""
        return (
            self.cell_pitch_x * (self.cell_count_x)
            + 2 * self.x_dist_to_mounting_holes
            + 2 * self.housing_x_size_past_mounting_hole_center
            + self.stencil_travel_distance  # For stencil border sizing.
        )

    @property
    def total_housing_y(self) -> float:
        """Total height of the braille housing."""
        return self.dot_pitch_y * (3 - 1) + self.border_y * 2

    @property
    def bottom_housing_thickness(self) -> float:
        """Thickness of the bottom housing."""
        return (
            self.solenoid_protrusion_from_pcb
            + self.dot_total_length
            - self.dot_ui_length
            - self.dot_cones_height
        )

    @property
    def top_housing_thickness(self) -> float:
        """Thickness of the top housing.

        Note: The stencil gets removed from this thickness.

        This thickness gets set such that the top of the dot is flush with the
        top of the housing, when in the "down" position.
        """
        return self.dot_cones_height + self.dot_travel_distance

    @property
    def total_housing_z(self) -> float:
        """Total height of the braille housing."""
        return self.bottom_housing_thickness + self.top_housing_thickness

    @property
    def stencil_travel_distance(self) -> float:
        """Travel distance of the stencil.

        The stencil must travel the large radius, plus the small radius.
        """
        return self.dot_min_diameter / 2 + self.dot_diameter / 2

    @property
    def mounting_hole_spacing_x(self) -> float:
        """Spacing between the mounting holes, in X axis."""
        return (
            self.x_dist_to_mounting_holes * 2
            + self.cell_pitch_x * (self.cell_count_x - 1)
            + self.dot_pitch_x
        )


def make_full_housing(g_spec: GeneralSpec) -> bd.Part:
    """Create a CAD model of bottom_housing."""
    p = bd.Part(None)

    p += bd.Box(
        g_spec.total_housing_x,
        g_spec.total_housing_y,
        g_spec.total_housing_z,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the braille dots.
    for cell_x, cell_y in product(
        evenly_space_with_center(
            count=g_spec.cell_count_x,
            spacing=g_spec.cell_pitch_x,
        ),
        evenly_space_with_center(
            count=g_spec.cell_count_y,
            spacing=g_spec.dot_pitch_y,
        ),
    ):
        for dot_x, dot_y in product(
            [
                *evenly_space_with_center(
                    count=2, spacing=g_spec.dot_pitch_x, center=cell_x
                ),
                cell_x,  # Center dot to remove icky bits.
            ],
            evenly_space_with_center(
                count=3,
                spacing=g_spec.dot_pitch_y,
                center=cell_y,
            ),
        ):
            # Remove the solenoid.
            p -= bd.Cylinder(
                radius=g_spec.solenoid_clearance_diameter / 2,
                height=g_spec.solenoid_protrusion_from_pcb,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate((dot_x, dot_y, 0))

            # Skip the actual dot for this one.
            if dot_x == cell_x:
                continue

            # Remove the braille dot.
            p -= bd.Cylinder(
                radius=g_spec.dot_hole_diameter / 2,
                height=g_spec.total_housing_z,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate((dot_x, dot_y, 0))

    # Remove the mounting holes.
    for x_side, y_val in product([-1, 1], [0]):
        p -= bd.Cylinder(
            radius=g_spec.mounting_hole_diameter / 2,
            height=g_spec.total_housing_z,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                x_side * g_spec.mounting_hole_spacing_x / 2,
                y_val,
                0,
            )
        )

    # Add mounting hole pegs into PCB.
    for x_side, y_side in product([-1, 1], [-1, 1]):
        # TODO(KilowattSynthesis): Round the pegs.
        p += bd.Cylinder(
            radius=g_spec.mounting_hole_diameter / 2,
            height=g_spec.mounting_hole_peg_length,
            align=bde.align.ANCHOR_TOP,
        ).translate(
            (
                x_side * g_spec.mounting_hole_spacing_x / 2,
                y_side * g_spec.mounting_hole_spacing_y,
                0,
            )
        )

    # Remove the stencil body.
    p -= bd.Box(
        (
            g_spec.total_housing_x
            - 2 * g_spec.border_around_stencil_x
            + g_spec.stencil_travel_distance
            + 0.2  # Just a bit extra to let it shift as necessary.
        ),
        g_spec.total_housing_y - 2 * g_spec.border_around_stencil_y,
        g_spec.stencil_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, g_spec.bottom_housing_thickness))

    # Remove the stencil gripper grooves.
    for y_val in evenly_space_with_center(
        count=2, spacing=g_spec.stencil_gripper_spacing_y
    ):
        p -= bd.Box(
            g_spec.total_housing_x,
            g_spec.stencil_gripper_width_y,
            g_spec.stencil_thickness,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                0,
                y_val,
                g_spec.bottom_housing_thickness,
            )
        )

    return p


def make_bottom_housing(g_spec: GeneralSpec) -> bd.Part:
    """From the housing model, keep only the bottom part."""
    p = make_full_housing(g_spec)

    # Keep only the bottom part.
    p -= bd.Box(
        g_spec.total_housing_x,
        g_spec.total_housing_y,
        g_spec.top_housing_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, g_spec.bottom_housing_thickness))

    # Remove `top_to_bottom_pegs` holes.
    for x_side, y_side in product([-1, 1], [-1, 1]):
        p -= bd.Cylinder(
            radius=g_spec.top_to_bottom_pegs_diameter_id / 2,
            # Technically could be a bit shorter (could subtract the stencil).
            height=g_spec.top_to_bottom_pegs_length,
            align=bde.align.ANCHOR_TOP,
        ).translate(
            (
                x_side
                * (
                    g_spec.total_housing_x / 2
                    - g_spec.top_to_bottom_pegs_border_x
                ),
                y_side
                * (
                    g_spec.total_housing_y / 2
                    - g_spec.top_to_bottom_pegs_border_y
                ),
                g_spec.bottom_housing_thickness,
            )
        )

    return p


def make_top_housing(g_spec: GeneralSpec) -> bd.Part:
    """From the housing model, keep only the top part."""
    p = make_full_housing(g_spec)

    # Keep only the top part.
    p -= bd.Box(
        g_spec.total_housing_x,
        g_spec.total_housing_y,
        g_spec.bottom_housing_thickness + 10,
        align=bde.align.ANCHOR_TOP,
    ).translate((0, 0, g_spec.bottom_housing_thickness))

    # Add `top_to_bottom_pegs` pegs.
    for x_side, y_side in product([-1, 1], [-1, 1]):
        p += bd.Cylinder(
            radius=g_spec.top_to_bottom_pegs_diameter / 2,
            height=(
                g_spec.top_to_bottom_pegs_length + g_spec.top_housing_thickness
            ),
            align=bde.align.ANCHOR_TOP,
        ).translate(
            (
                x_side
                * (
                    g_spec.total_housing_x / 2
                    - g_spec.top_to_bottom_pegs_border_x
                ),
                y_side
                * (
                    g_spec.total_housing_y / 2
                    - g_spec.top_to_bottom_pegs_border_y
                ),
                g_spec.total_housing_z,
            )
        )

    return p


def make_stencil_2d(
    g_spec: GeneralSpec,
    *,
    show_dot_holes: bool = True,
    show_slot_holes: bool = True,
) -> bd.Shape:
    """Make a 2d version of the stencil."""
    # Add the stencil body.
    p = bd.Rectangle(
        g_spec.total_housing_x - 2 * g_spec.border_around_stencil_x - 0.2,
        g_spec.total_housing_y - 2 * g_spec.border_around_stencil_y - 0.2,
    )

    # Add the stencil grippers (long, to the sides).
    for y_val in evenly_space_with_center(
        count=2, spacing=g_spec.stencil_gripper_spacing_y
    ):
        p += bd.Rectangle(
            g_spec.total_housing_x + g_spec.stencil_gripped_extension_x * 2,
            g_spec.stencil_gripper_width_y - 0.2,
        ).translate((0, y_val))

    # Remove the holes. Each hole is a hull between the big and small circles.
    for cell_x, cell_y in product(
        evenly_space_with_center(
            count=g_spec.cell_count_x,
            spacing=g_spec.cell_pitch_x,
        ),
        evenly_space_with_center(
            count=g_spec.cell_count_y,
            spacing=g_spec.dot_pitch_y,
        ),
    ):
        for dot_x, dot_y in product(
            evenly_space_with_center(
                count=2,
                spacing=g_spec.dot_pitch_x,
                center=cell_x,
            ),
            evenly_space_with_center(
                count=3,
                spacing=g_spec.dot_pitch_y,
                center=cell_y,
            ),
        ):
            if not show_dot_holes:
                continue
            p -= bd.make_hull(
                bd.Circle(g_spec.dot_hole_diameter / 2)
                .translate((-g_spec.stencil_travel_distance / 2, 0))
                .edges()
                + bd.Circle(g_spec.dot_min_diameter / 2)
                .translate((g_spec.stencil_travel_distance / 2, 0))
                .edges()
            ).translate((dot_x, dot_y))

    # Remove the mounting screw slots.
    for x_val in evenly_space_with_center(
        count=2, spacing=g_spec.mounting_hole_spacing_x
    ):
        if not show_slot_holes:
            continue

        p -= bd.SlotCenterToCenter(
            center_separation=g_spec.stencil_travel_distance,
            height=g_spec.mounting_hole_diameter,
        ).translate((x_val, 0))

    # Remove the `top_to_bottom_pegs` slots.
    for x_side, y_side in product([-1, 1], [-1, 1]):
        if not show_slot_holes:
            continue

        p -= bd.SlotCenterToCenter(
            center_separation=g_spec.stencil_travel_distance,
            height=g_spec.top_to_bottom_pegs_diameter_id,
        ).translate(
            (
                x_side
                * (
                    g_spec.total_housing_x / 2
                    - g_spec.top_to_bottom_pegs_border_x
                ),
                y_side
                * (
                    g_spec.total_housing_y / 2
                    - g_spec.top_to_bottom_pegs_border_y
                ),
            )
        )

    return p


def make_stencil_3d(
    g_spec: GeneralSpec, thickness_override: float | None = None
) -> bd.Part:
    """Make a 3d version of the stencil."""
    p = bd.Part(None)

    p += bd.extrude(
        bd.Sketch(None) + make_stencil_2d(g_spec),
        amount=thickness_override or g_spec.stencil_thickness,
    )

    return p


def make_dot(g_spec: GeneralSpec) -> bd.Part:
    """Create a CAD model of a braille dot in the Z axis.

    At Z=0: The small part of the cone which makes the dot stick out
        (bottom cone).

    At Z=1: The small part of the cone which makes the dot recessed
        (top cone).

    Note that Z = 1 = g_spec.dot_travel_distance
    """
    p = bd.Part(None)

    cone_pointer = (
        bd.Part(None)
        # Make cone below Z=0.
        + bd.Cone(
            bottom_radius=g_spec.dot_diameter / 2,
            top_radius=g_spec.dot_min_diameter / 2,
            height=g_spec.dot_cones_height,
            align=bde.align.ANCHOR_TOP,
        )
        # Make the cone above Z=0.
        + bd.Cone(
            bottom_radius=g_spec.dot_min_diameter / 2,
            top_radius=g_spec.dot_diameter / 2,
            height=g_spec.dot_cones_height,
            align=bde.align.ANCHOR_BOTTOM,
        )
    )

    # Add the cone pointer around Z=0.
    p += cone_pointer

    # Add the cone pointer around Z=1.
    p += cone_pointer.translate((0, 0, g_spec.dot_travel_distance))

    # Add the cylinder between the cones.
    p += bd.Cylinder(
        radius=g_spec.dot_diameter / 2,
        height=g_spec.dot_travel_distance - 2 * g_spec.dot_cones_height,
        align=bde.align.ANCHOR_BOTTOM,
    ).translate((0, 0, g_spec.dot_cones_height))

    # Add the cylinder below the bottom cone for around the magnet.
    p += bd.Cylinder(
        radius=g_spec.dot_diameter / 2,
        height=(
            g_spec.dot_magnet_height
            + g_spec.dot_magnet_top_dist_below_z0
            - g_spec.dot_cones_height
        ),
        align=bde.align.ANCHOR_TOP,
    ).translate((0, 0, -g_spec.dot_cones_height))

    # Draw the magnet (removing space for it).
    p -= bd.Cylinder(
        radius=g_spec.dot_magnet_diameter / 2,
        height=g_spec.dot_magnet_height,
        align=bde.align.ANCHOR_TOP,
    ).translate((0, 0, -g_spec.dot_magnet_top_dist_below_z0))

    # Draw the top of the top (user interface).
    ui_top = bd.Part(None) + bd.Cylinder(
        radius=g_spec.dot_diameter / 2,
        height=g_spec.dot_ui_length,
        align=bde.align.ANCHOR_BOTTOM,
    )
    p += ui_top.fillet(
        radius=g_spec.dot_ui_round_radius,
        edge_list=bde.top_face_of(ui_top).edges(),
    ).translate((0, 0, g_spec.dot_travel_distance + g_spec.dot_cones_height))

    assert g_spec.dot_total_length == (
        bde.top_face_of(p).center().Z - bde.bottom_face_of(p).center().Z
    )

    return p


def make_dot_cluster(g_spec: GeneralSpec) -> bd.Part:
    """Create a CAD model of many printable dots."""
    p = bd.Part(None)
    dot = make_dot(g_spec)

    x_count = 3
    y_count = 3
    x_spacing = 3
    y_spacing = 3

    interface_height = 1

    # Add base
    p += bd.Box(
        x_count * x_spacing,
        y_count * y_spacing,
        2,
        align=bde.align.ANCHOR_TOP,
    )

    for dot_x, dot_y in product(
        evenly_space_with_center(
            count=x_count,
            spacing=x_spacing,
        ),
        evenly_space_with_center(
            count=y_count,
            spacing=y_spacing,
        ),
    ):
        p += dot.translate(
            (
                dot_x,
                dot_y,
                -dot.bounding_box().min.Z + interface_height,
            )
        )

        # Add the interface cone.
        p += (
            bd.Box(
                g_spec.dot_diameter - 0.5,
                min(x_spacing, y_spacing),
                interface_height,
                align=bde.align.ANCHOR_BOTTOM,
            )
            .rotate(axis=bd.Axis.Z, angle=45)
            .translate((dot_x, dot_y, 0))
        )

    return p


def make_assembly(
    g_spec: GeneralSpec,
    stencil_shift: Literal[0, -1, 1] = 0,
    housing_select: Literal["top", "bottom", "full"] = "bottom",
) -> bd.Part:
    """Create a CAD model of the entire assembly."""
    p = bd.Part(None)

    if housing_select == "top":
        p += make_top_housing(g_spec)
    elif housing_select == "bottom":
        p += make_bottom_housing(g_spec)
    elif housing_select == "full":
        p += make_full_housing(g_spec)
    else:
        msg = f"Unknown housing_select: {housing_select}"
        raise ValueError(msg)

    cell_center_x = (
        -g_spec.cell_pitch_x / 2 if g_spec.cell_count_x % 2 == 0 else 0
    )

    # Place the Z=0 hole at the top of the housing, thus making the dot "up".
    p += make_dot(g_spec).translate(
        (
            cell_center_x + g_spec.dot_pitch_x / -2,
            0,
            g_spec.bottom_housing_thickness,
        )
    )

    # Place the Z=1 hole at the top of the housing, thus making the dot "down".
    p += make_dot(g_spec).translate(
        (
            cell_center_x + g_spec.dot_pitch_x / 2,
            0,
            g_spec.bottom_housing_thickness - g_spec.dot_travel_distance,
        )
    )

    # Draw the stencil.
    p += bd.extrude(
        bd.Sketch(None) + make_stencil_2d(g_spec),
        amount=g_spec.stencil_thickness,
    ).translate(
        (
            g_spec.stencil_travel_distance / 2 * stencil_shift,
            0,
            g_spec.bottom_housing_thickness,
        )
    )

    return p


def make_many_assemblies(g_spec: GeneralSpec) -> bd.Part:
    """Create a CAD model of the entire assembly."""
    p = bd.Part(None)

    for housing_select, z_val in zip(
        ("top", "bottom"), (0, g_spec.total_housing_z + 5), strict=True
    ):
        for stencil_shift in (-1, 1):
            p += make_assembly(
                g_spec, stencil_shift, housing_select=housing_select
            ).translate(
                (0, stencil_shift / 2 * (g_spec.total_housing_y + 3.5), z_val)
            )

    return p


if __name__ == "__main__":
    parts = {
        "dot_cluster": show(make_dot_cluster(GeneralSpec())),
        "full_housing": (make_full_housing(GeneralSpec())),
        "dot": (make_dot(GeneralSpec())),
        "bottom_housing": (make_bottom_housing(GeneralSpec())),
        "bottom_housing_0.3mm_solenoid": (
            make_bottom_housing(GeneralSpec(solenoid_protrusion_from_pcb=0.3))
        ),
        "bottom_housing_1mm_solenoid": (
            make_bottom_housing(GeneralSpec(solenoid_protrusion_from_pcb=1))
        ),
        "bottom_housing_3mm_solenoid": (
            make_bottom_housing(GeneralSpec(solenoid_protrusion_from_pcb=3))
        ),
        "bottom_housing_8mm_solenoid": (
            make_bottom_housing(GeneralSpec(solenoid_protrusion_from_pcb=8))
        ),
        "bottom_housing_12mm_solenoid": (
            make_bottom_housing(GeneralSpec(solenoid_protrusion_from_pcb=12))
        ),
        "top_housing": (make_top_housing(GeneralSpec())),
        "top_housing_0.25mm_stencil": (
            make_top_housing(GeneralSpec(stencil_thickness=0.25))
        ),
        "top_housing_0.4mm_stencil": (
            make_top_housing(GeneralSpec(stencil_thickness=0.4))
        ),
        "top_housing_0.6mm_stencil": (
            make_top_housing(GeneralSpec(stencil_thickness=0.6))
        ),
        "top_housing_1mm_stencil": (
            make_top_housing(GeneralSpec(stencil_thickness=1))
        ),
        "assembly": (make_assembly(GeneralSpec())),
        "stencil_2d": (make_stencil_2d(GeneralSpec())),
        "stencil_2d_outline": (
            make_stencil_2d(
                GeneralSpec(), show_dot_holes=False, show_slot_holes=False
            )
        ),
        "stencil_3d": (make_stencil_3d(GeneralSpec())),
        "many_assemblies": (make_many_assemblies(GeneralSpec())),
    }

    logger.info("Saving CAD model(s)")

    (
        export_folder := Path(__file__).parent.parent
        / "build"
        / Path(__file__).stem
    ).mkdir(exist_ok=True, parents=True)
    for name, part in parts.items():
        if isinstance(part, bd.Part | bd.Solid | bd.Compound):
            bd.export_stl(part, str(export_folder / f"{name}.stl"))
            bd.export_step(part, str(export_folder / f"{name}.step"))
        if "2d" in name:
            # Export SVG.
            svg = bd.ExportSVG(unit=bd.Unit.MM, line_weight=0.1)
            svg.add_layer(
                "default",
                fill_color=bd.ColorIndex.RED,
                line_color=bd.ColorIndex.BLACK,
            )
            svg.add_shape(part, layer="default")
            svg.write(export_folder / f"{name}.svg")

            # Export DXF.
            dxf = bd.ExportDXF(unit=bd.Unit.MM, line_weight=0.1)
            dxf.add_layer(
                "default",
                color=bd.ColorIndex.RED,
                line_type=bd.LineType.CONTINUOUS,
            )
            dxf.add_shape(part, layer="default")
            dxf.write(export_folder / f"{name}.dxf")

    logger.success("Saved CAD model(s)")

    data = {
        "stencil_box": parts["stencil_2d_outline"].bounding_box(),
    }
    logger.success(f"General data: {data}")
