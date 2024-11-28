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

    def __post_init__(self) -> None:
        """Post initialization checks."""

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


def make_bottom_housing(g_spec: GeneralSpec) -> bd.Part:
    """Create a CAD model of bottom_housing."""
    p = bd.Part(None)

    p += bd.Box(
        g_spec.total_housing_x,
        g_spec.total_housing_y,
        g_spec.bottom_housing_thickness,
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
                height=g_spec.bottom_housing_thickness,
                align=bde.align.ANCHOR_BOTTOM,
            ).translate((dot_x, dot_y, 0))

    # Remove the mounting holes.
    for x_side, y_val in product([-1, 1], [0]):
        p -= bd.Cylinder(
            radius=g_spec.mounting_hole_diameter / 2,
            height=g_spec.bottom_housing_thickness,
            align=bde.align.ANCHOR_BOTTOM,
        ).translate(
            (
                x_side
                * (
                    g_spec.x_dist_to_mounting_holes
                    + g_spec.cell_pitch_x * g_spec.cell_count_x / 2
                ),
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
                x_side
                * (
                    g_spec.x_dist_to_mounting_holes
                    + g_spec.cell_pitch_x * g_spec.cell_count_x / 2
                ),
                y_side * g_spec.mounting_hole_spacing_y,
                0,
            )
        )

    return p


if __name__ == "__main__":
    parts = {
        "bottom_housing": show(make_bottom_housing(GeneralSpec())),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid), f"{name} is not a Part"
        # assert part.is_manifold is True, f"{name} is not manifold"

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
