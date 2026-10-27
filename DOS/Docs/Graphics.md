# Puzzle Pits Graphics

`DOS/Tools/dat2png.py` converts all the game and editor graphics to PNGs in `DOS/Assets/Graphics/`. Running `python3 DOS/Tools/dat2png.py` writes 676 PNGs (about 2.5 MB). The script uses only Python's standard library.

## What gets converted

| Source | Output |
|---|---|
| `LOGO.DAT`, `TITLE.DAT` | `Screens/` — the full 320×200 Plasma Works logo and title screen, each with the palette the game uses for it |
| `TILES1`–`3.DAT` | `Tiles/` — all 285 game graphics, numbered as in `TILEDEFS.H` and named where possible (`029_BARREL.png`, `277_CROSSHAIRS.png`) |
| (same tiles) | `Objects/` — 51 objects assembled at 48×48 (see below) |
| `PLASMA1.FNT` | `Font/PLASMA1/` — one image per character |
| `ETILES.DAT`, `PITSFONT.DAT` | `Editor/Tiles/`, `Editor/Font/` — the editor's tiles, buttons and font |
| (all of the above) | `Sheets/` — one overview image per source file, plus one of the assembled objects |

## Things worth knowing

- **Objects come in quarters.** The game draws each wall, barrel, crate, chest and player frame as four 24×24 pieces. The individual files in `Tiles/` are those pieces, so they are also put back together as 48×48 images in `Objects/`. That includes all of the player's walking, pushing, gem-magic and morph frames.
- **Colours:** the game's colour tables are copied into the script from `GFX.C`. The editor's files use a different format from the game's, with their own colour table built in, and the script reads that format too. Both formats are documented in the script's header.
- **Transparency:** colour 0 is made transparent wherever the game draws a graphic as a see-through overlay. Floor tiles and screens stay solid. Use `--opaque` to turn transparency off.
- **One wrong-coloured sheet:** the title-text panel (graphic 275) is only shown on the title screen. Its own file uses the title-screen colours, but in the `TILES3` overview sheet it appears in gameplay colours.
