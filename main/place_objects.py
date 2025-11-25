"""Automate placing 3DEN objects by reading the UI and moving the mouse.

The script uses PyAutoGUI to locate the object browser on your screen and
click through each entry, placing them next to one another in the viewport.
It also scrolls the list as it moves through entries and can skip category
rows so only actual objects are placed.

Requirements:
- Python 3.9+
- pyautogui
- pillow
- opencv-python (for confidence-based template matching)
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pyautogui


@dataclass
class PlacementConfig:
    """Runtime configuration for controlling placement behaviour."""

    anchor_template: Path
    row_height: int = 26
    list_offset_x: int = 10
    list_offset_y: int = 40
    screen_height: Optional[int] = None
    spacing_pixels: int = 120
    per_row: int = 15
    click_delay: float = 0.05
    place_delay: float = 0.1
    scroll_clicks_per_row: int = 3
    scroll_delay: float = 0.15
    limit: Optional[int] = None
    confidence: float = 0.9
    placement_origin: Optional[tuple[int, int]] = None
    category_color: Optional[tuple[int, int, int]] = None
    category_color_tolerance: int = 8
    category_icon_offset_x: int = -14
    item_color: Optional[tuple[int, int, int]] = (142, 125, 18)
    item_color_tolerance: int = 10
    item_color_offset_x: int = 26
    item_color_offset_y: int = 12
    require_item_color: bool = True
    dry_run: bool = False


def locate_anchor(template: Path, confidence: float) -> pyautogui.Box:
    """Locate the supplied template on the current screen.

    The template should be a cropped screenshot of a stable UI element at the top
    of the 3DEN object browser, e.g., the "Entities" header. A failure to find it
    raises a RuntimeError.
    """

    if not template.exists():
        raise RuntimeError(f"anchor template not found: {template}")

    location = pyautogui.locateOnScreen(str(template), confidence=confidence)
    if location is None:
        raise RuntimeError(
            "Could not find anchor on screen. Make sure the 3DEN object browser "
            "is visible and matches the template screenshot."
        )

    return location


def safe_screen_height(default: int = 1080) -> int:
    """Return the detected screen height, falling back to a sensible default."""

    try:
        return pyautogui.size().height
    except Exception:
        return default


def is_category_row(list_x: int, list_y: int, cfg: PlacementConfig) -> bool:
    """Detect whether the current row is a category header (triangle icon).

    If ``category_color`` is provided, the script samples the pixel at
    ``list_x + category_icon_offset_x`` to see if it matches the expected
    color. This keeps the script from clicking category rows when iterating
    down the list. Returns ``False`` when no color is configured.
    """

    if cfg.category_color is None:
        return False

    icon_x = list_x + cfg.category_icon_offset_x
    try:
        return pyautogui.pixelMatchesColor(
            icon_x,
            list_y,
            cfg.category_color,
            tolerance=cfg.category_color_tolerance,
        )
    except Exception:
        return False


def row_has_item_color(list_x: int, list_y: int, cfg: PlacementConfig) -> bool:
    """Check for the expected item text/icon color on the current row.

    The default color matches the object rows shown in the reference screenshot
    (#8e7d12). When ``require_item_color`` is true, a missing match causes the
    row to be skipped. If ``item_color`` is ``None`` or checking is disabled,
    the function returns True.
    """

    if cfg.item_color is None or not cfg.require_item_color:
        return True

    sample_x = list_x + cfg.item_color_offset_x
    sample_y = list_y + cfg.item_color_offset_y
    try:
        return pyautogui.pixelMatchesColor(
            sample_x,
            sample_y,
            cfg.item_color,
            tolerance=cfg.item_color_tolerance,
        )
    except Exception:
        return False


def place_objects(cfg: PlacementConfig) -> None:
    """Drive the mouse to click each object and place it in a grid."""

    anchor = (
        pyautogui.Box(0, 0, 0, 0)
        if cfg.dry_run
        else locate_anchor(cfg.anchor_template, cfg.confidence)
    )

    pyautogui.FAILSAFE = True

    list_start_x = anchor.left + cfg.list_offset_x
    list_start_y = anchor.top + cfg.list_offset_y
    placement_origin = cfg.placement_origin or pyautogui.position()

    screen_height = cfg.screen_height or safe_screen_height()
    visible_rows = max(1, (screen_height - list_start_y) // cfg.row_height)

    scroll_rows_consumed = 0
    placed = 0
    index = 0

    while cfg.limit is None or placed < cfg.limit:
        row_in_view = index - scroll_rows_consumed
        if row_in_view >= visible_rows:
            rows_to_scroll = row_in_view - visible_rows + 1
            scroll_amount = -cfg.scroll_clicks_per_row * rows_to_scroll
            if not cfg.dry_run:
                pyautogui.scroll(scroll_amount, x=list_start_x, y=list_start_y)
                time.sleep(cfg.scroll_delay)
            scroll_rows_consumed += rows_to_scroll
            row_in_view = index - scroll_rows_consumed

        list_pos = (list_start_x, list_start_y + row_in_view * cfg.row_height)

        if not cfg.dry_run and is_category_row(list_pos[0], list_pos[1], cfg):
            index += 1
            continue

        if not cfg.dry_run and not row_has_item_color(list_pos[0], list_pos[1], cfg):
            print(f"Skipping row {index}: item color not detected at {list_pos}.")
            index += 1
            continue

        col = placed % cfg.per_row
        row = placed // cfg.per_row
        world_pos = (
            placement_origin[0] + col * cfg.spacing_pixels,
            placement_origin[1] + row * cfg.spacing_pixels,
        )

        if cfg.dry_run:
            print(f"Would click list entry at {list_pos} and place at {world_pos}")
        else:
            pyautogui.moveTo(*list_pos)
            pyautogui.click()
            time.sleep(cfg.click_delay)

            pyautogui.moveTo(*world_pos)
            pyautogui.click()
            time.sleep(cfg.place_delay)

        placed += 1
        index += 1


def parse_args(argv: list[str]) -> PlacementConfig:
    parser = argparse.ArgumentParser(description="Place 3DEN objects with PyAutoGUI.")
    parser.add_argument(
        "anchor_template",
        type=Path,
        help="Cropped screenshot of the top of the object browser (PNG recommended)",
    )
    parser.add_argument("--row-height", type=int, default=26, help="Pixel height of each object entry")
    parser.add_argument("--list-offset-x", type=int, default=10, help="Pixels from anchor's left to the first entry")
    parser.add_argument("--list-offset-y", type=int, default=40, help="Pixels from anchor's top to the first entry")
    parser.add_argument(
        "--screen-height",
        type=int,
        default=None,
        help="Screen height in pixels (defaults to detected height; set to 1080 for 1920x1080)",
    )
    parser.add_argument("--spacing-pixels", type=int, default=120, help="Pixel spacing between placed objects")
    parser.add_argument("--per-row", type=int, default=15, help="How many objects to place before wrapping to the next row")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of objects to place (omit for all visible)")
    parser.add_argument("--click-delay", type=float, default=0.05, help="Delay between selecting an entry and placing it")
    parser.add_argument("--place-delay", type=float, default=0.1, help="Delay after placing an object to allow UI to settle")
    parser.add_argument(
        "--scroll-clicks-per-row",
        type=int,
        default=3,
        help="Mouse wheel clicks to move by roughly one list row when scrolling",
    )
    parser.add_argument("--scroll-delay", type=float, default=0.15, help="Pause after scrolling to let the UI catch up")
    parser.add_argument("--confidence", type=float, default=0.9, help="Template matching confidence for finding the anchor")
    parser.add_argument(
        "--origin",
        type=int,
        nargs=2,
        metavar=("X", "Y"),
        help="Screen coordinates to start placing objects (defaults to current mouse position)",
    )
    parser.add_argument(
        "--category-color",
        type=int,
        nargs=3,
        metavar=("R", "G", "B"),
        help="RGB value of the category triangle to skip clicking category rows",
    )
    parser.add_argument(
        "--category-tolerance",
        type=int,
        default=8,
        help="Tolerance for matching the category triangle color",
    )
    parser.add_argument(
        "--category-offset-x",
        type=int,
        default=-14,
        help="Horizontal offset from the entry label to sample the category triangle pixel",
    )
    parser.add_argument(
        "--item-color",
        type=int,
        nargs=3,
        metavar=("R", "G", "B"),
        default=(142, 125, 18),
        help="RGB value expected on valid item rows (defaults to #8e7d12)",
    )
    parser.add_argument(
        "--item-color-tolerance",
        type=int,
        default=10,
        help="Tolerance for matching the item row color",
    )
    parser.add_argument(
        "--item-offset-x",
        type=int,
        default=26,
        help="Horizontal offset from the entry label where the item color is sampled",
    )
    parser.add_argument(
        "--item-offset-y",
        type=int,
        default=12,
        help="Vertical offset from the top of the row where the item color is sampled",
    )
    parser.add_argument(
        "--allow-missing-item-color",
        action="store_true",
        help="Click rows even if the expected item color is not detected",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned clicks instead of moving the mouse (useful for validation)",
    )

    args = parser.parse_args(argv)
    return PlacementConfig(
        anchor_template=args.anchor_template,
        row_height=args.row_height,
        list_offset_x=args.list_offset_x,
        list_offset_y=args.list_offset_y,
        screen_height=args.screen_height,
        spacing_pixels=args.spacing_pixels,
        per_row=args.per_row,
        click_delay=args.click_delay,
        place_delay=args.place_delay,
        scroll_clicks_per_row=args.scroll_clicks_per_row,
        scroll_delay=args.scroll_delay,
        limit=args.limit,
        confidence=args.confidence,
        placement_origin=tuple(args.origin) if args.origin else None,
        category_color=tuple(args.category_color) if args.category_color else None,
        category_color_tolerance=args.category_tolerance,
        category_icon_offset_x=args.category_offset_x,
        item_color=tuple(args.item_color) if args.item_color else None,
        item_color_tolerance=args.item_color_tolerance,
        item_color_offset_x=args.item_offset_x,
        item_color_offset_y=args.item_offset_y,
        require_item_color=not args.allow_missing_item_color,
        dry_run=args.dry_run,
    )


def main(argv: list[str]) -> int:
    cfg = parse_args(argv)
    try:
        place_objects(cfg)
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting cleanly.")
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
