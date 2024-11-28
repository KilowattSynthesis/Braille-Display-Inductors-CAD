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
    mounting_hole_head_diameter: float = 4.0
    mounting_hole_peg_diameter: float = 1.8
    mounting_hole_peg_length: float = 1.5

    # TODO(KilowattSynthesis): Make a property.
    bottom_housing_thickness: float = 5.0

    # Distance the dot expects to travel.
    dot_travel_distance: float = 1.0
    dot_min_diameter: float = 1.0
    dot_total_length: float = 5
    dot_cones_height: float = 0.4

    dot_magnet_diameter: float = 1.0
    dot_magnet_height: float = 1.0

    # Distance from the top of the magnet to the Z=0 plane.
    dot_magnet_top_dist_below_z0: float = 0.4  # Start around bottom of cone.

    # TODO(KilowattSynthesis): Check or set dynamically.
    dot_ui_length: float = 1.0
    dot_ui_round_radius: float = 0.6

    stencil_thickness: float = 0.25  # Actually 0.15, but leave some space.
    border_around_stencil: float = 2  # Contact between top and bottom housing.
    stencil_gripper_width_y = 3
    stencil_gripper_spacing_y = 5.8
    stencil_gripped_extension_x: float = 15

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert self.dot_cones_height * 2 <= self.dot_total_length

        stencil_gripper_gap_width = (
            self.stencil_gripper_spacing_y - self.stencil_gripper_width_y
        )
        assert stencil_gripper_gap_width > self.mounting_hole_diameter

        info = {
            "mounting_hole_spacing_x": self.mounting_hole_spacing_x,
        }
        logger.success(info)

    @property
    def total_housing_x(self) -> float:
        """Total width of the braille housing."""
        return (
            self.cell_pitch_x * (self.cell_count_x)
            + 2 * self.x_dist_to_mounting_holes
            + self.mounting_hole_head_diameter
        )

    @property
    def total_housing_y(self) -> float:
        """Total height of the braille housing."""
        return self.dot_pitch_y * (3 - 1) + self.border_y * 2

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
    # TODO(KilowattSynthesis): Do better.
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
            - 2 * g_spec.border_around_stencil
            + g_spec.stencil_travel_distance
            + 0.2  # Just a bit extra to let it shift as necessary.
        ),
        g_spec.total_housing_y - 2 * g_spec.border_around_stencil,
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

    return p


def make_stencil_2d(g_spec: GeneralSpec) -> bd.Shape:
    """Make a 2d version of the stencil."""
    # Add the stencil body.
    p = bd.Rectangle(
        g_spec.total_housing_x - 2 * g_spec.border_around_stencil - 0.2,
        g_spec.total_housing_y - 2 * g_spec.border_around_stencil - 0.2,
    )

    # Add the stencil grippers.
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
            p -= bd.make_hull(
                bd.Circle(g_spec.dot_hole_diameter / 2)
                .translate((-g_spec.stencil_travel_distance / 2, 0))
                .edges()
                + bd.Circle(g_spec.dot_min_diameter / 2)
                .translate((g_spec.stencil_travel_distance / 2, 0))
                .edges()
            ).translate((dot_x, dot_y))

    # Remove the mounting screws.
    for x_val in evenly_space_with_center(
        count=2, spacing=g_spec.mounting_hole_spacing_x
    ):
        p -= bd.make_hull(
            bd.Circle(g_spec.mounting_hole_diameter / 2)
            .translate((-g_spec.stencil_travel_distance / 2, 0))
            .edges()
            + bd.Circle(g_spec.mounting_hole_diameter / 2)
            .translate((g_spec.stencil_travel_distance / 2, 0))
            .edges(),
        ).translate((x_val, 0))

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
        "full_housing": (make_full_housing(GeneralSpec())),
        "dot": (make_dot(GeneralSpec())),
        "bottom_housing": (make_bottom_housing(GeneralSpec())),
        "top_housing": (make_top_housing(GeneralSpec())),
        "assembly": show(make_assembly(GeneralSpec())),
        "stencil_2d": (make_stencil_2d(GeneralSpec())),
        "many_assemblies": show(make_many_assemblies(GeneralSpec())),
    }

    logger.info("Saving CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        if isinstance(part, bd.Part | bd.Solid | bd.Compound):
            bd.export_stl(part, str(export_folder / f"{name}.stl"))
            bd.export_step(part, str(export_folder / f"{name}.step"))
        elif isinstance(part, bd.Shape):
            # bd.export_svg(part, str(export_folder / f"{name}.svg"))
            pass
            # TODO(KilowattSynthesis): Export SVG.
        else:
            msg = f"Unknown type for {name}"
            raise NotImplementedError(msg)
