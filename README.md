# Screen-driven 3DEN object placer

This helper drives the Arma 3 3DEN editor from Python. It reads your screen to
find the object browser, clicks every object entry in order, scrolls to keep the
list moving, and drops each object into a neat grid in the viewport. The
defaults are tuned for a 1920x1080 screen.

## Setup
1. Install Python 3.9+.
2. Install dependencies (requires internet access):
   ```bash
   pip install pyautogui pillow opencv-python
   ```
3. Take a small screenshot of a stable element at the top of the object browser
   (for example the "Entities" header). Save it as `anchor.png`.
4. (Recommended) Use a color picker on a category triangle (the little arrow
   next to categories like "1 - SSG Intel Items") and note its RGB values. This
   lets the script skip category rows instead of clicking them.
5. The script also checks for the item-row color before clicking (`#8e7d12` by
   default). If your UI skin differs, sample that color (RGB or hex) so only
   actual object rows are chosen.

## Running the script
Position your camera so clicks on the right-hand list are valid and your mouse
is where you want the first object to appear. Then run, for example:

```bash
python main/place_objects.py anchor.png \
  --limit 200 \
  --per-row 20 \
  --spacing-pixels 140 \
  --screen-height 1080 \
  --scroll-clicks-per-row 3 \
  --category-color-hex #464646 \
  --category-offset-x -18 \
  --item-color-hex #8e7d12
```

Key options:
- `anchor.png` – the screenshot the script uses to find the browser.
- `--screen-height` – set this to `1080` for a 1920x1080 display (default is
  auto-detected).
- `--limit` – how many objects to place; set this before running to avoid
  endless scrolling.
- `--per-row` / `--spacing-pixels` – control the grid layout in the world.
- `--scroll-clicks-per-row` – how much to scroll between list rows when the
  list runs off-screen.
- `--category-color` (with `--category-offset-x`) – RGB color and horizontal
  sample point for the category triangle so category headers are skipped.
- `--category-color-hex` – hex alternative for the category color (e.g.,
  `#464646`).
- `--item-color` (with `--item-offset-x` / `--item-offset-y`) – expected color on
  valid item rows. Defaults to `#8e7d12` and is checked before clicking so
  categories or empty rows are skipped.
- `--item-color-hex` – hex alternative for the item-row guard (e.g.,
  `#8e7d12`).
- `--dry-run` – print the planned clicks without moving the mouse (great for
  validation before running on a live editor).
- `--log-sampled-colors` – print the sampled colors for each row so you can tune
  offsets/tolerances when UI scaling or mods change the palette.

### Tips for reliable runs
- The script automatically scrolls once the current row is past the visible
  portion of the list. Adjust `--scroll-clicks-per-row` if a single scroll moves
  too far or not far enough.
- If your UI scale changes the vertical spacing, tweak `--row-height` and
  `--list-offset-y` until the printed dry-run coordinates line up with rows.
- To ignore categories entirely, omit `--category-color`. To skip them, sample
  the triangle color from your UI (RGB) and keep `--category-offset-x`
  negative so the pixel is read just left of the entry text.
- If colors feel off (e.g., the script still lands on category rows), rerun
  with `--log-sampled-colors` for a short batch. That will print the sampled
  RGB values so you can update the hex/RGB arguments and tolerances.
- `pyautogui.FAILSAFE` is enabled; move the mouse to the top-left corner to
  abort instantly.

## What changed
- Removed the old SQF helper and focused solely on the Python screen-reading
  workflow.
- Added scrolling support, category-row detection, a dry-run mode, and clearer
  defaults for a 1920x1080 layout.
