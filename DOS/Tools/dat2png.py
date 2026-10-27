#!/usr/bin/env python3
"""Convert Puzzle Pits .DAT/.FNT graphics into PNG files.

Usage:  python3 DOS/Tools/dat2png.py [--opaque] [--out DIR]

Reads the game's and editor's data files and writes PNGs (by default into
DOS/Assets/Graphics/). Uses only the Python standard library.

Formats handled:
  LOGO.DAT, TITLE.DAT   Raw 320x200 8-bit screens (game palettes 2 and 3).
  TILES1-3.DAT          Game shape lists: repeated [u8 w, u8 h, w*h pixels],
                        terminated by w == 0. Shapes are numbered
                        consecutively across the three files (0..284), matching
                        the tile/shape constants in Source/TILEDEFS.H.
  PLASMA1.FNT           Game font, same shape-list format starting at
                        character 32; pixels are 0/1.
  ETILES.DAT,           Editor "SHST" shape files: "SHST", u32 size, u16 count,
  PITSFONT.DAT          u16 has_palette, [768-byte 8-bit RGB palette], then
                        count x [u16 w, u16 h, u16 bpp(8), w*h pixels]
                        (big-endian). Empty slots have w == h == 0.

Game palettes are the 64-entry VGA (6-bit) palettes from SetPalette() in
Source/GFX.C. Pixel value 0 is written as transparent for shapes the game
draws with a mask; pass --opaque to keep it black everywhere.

Objects (walls, barrels, the player, ...) are drawn as four 24x24 quarter
shapes offset by half a tile (see Gdrall() in Source/PITS.C): shape N+0 is the
top-left quarter, N+1 top-right, N+2 bottom-left and N+3 bottom-right, with
the object's own map cell under the bottom-right quarter. These are also
written assembled as 48x48 images in Objects/.
"""

import argparse
import os
import struct
import sys
import zlib

DOS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.join(DOS_DIR, "Game", "PITS95")
EDITOR_DIR = os.path.join(DOS_DIR, "Editor")
DEFAULT_OUT = os.path.join(DOS_DIR, "Assets", "Graphics")

# 6-bit VGA palettes copied from SetPalette() in Source/GFX.C.
# 1 = gameplay, 2 = Plasma Works logo, 3 = title screen.
VGA_PALETTES = {
    1: [
    (0,0,0), (63,63,63), (54,54,54), (50,50,50), (42,42,42), (37,37,37),
    (25,25,25), (63,0,0), (54,0,0), (46,0,0), (37,0,0), (63,63,0),
    (63,42,0), (0,63,63), (29,46,63), (33,0,33), (33,63,33), (0,63,0),
    (0,46,0), (0,33,0), (0,33,63), (0,25,58), (0,16,50), (0,8,46),
    (0,4,37), (0,0,33), (63,37,33), (46,21,21), (33,16,0), (29,12,0),
    (25,8,0), (21,4,0), (0,0,0), (31,31,31), (27,27,27), (25,25,25),
    (21,21,21), (18,18,18), (12,12,12), (31,0,0), (27,0,0), (23,0,0),
    (18,0,0), (31,31,0), (31,21,0), (0,31,31), (14,23,31), (16,0,16),
    (16,31,16), (0,31,0), (0,23,0), (0,16,0), (0,16,31), (0,12,29),
    (0,8,25), (0,4,23), (0,2,18), (0,0,16), (31,18,16), (23,10,10),
    (16,8,0), (14,6,0), (12,4,0), (10,2,0),
    ],
    2: [
    (0,0,0), (63,63,63), (54,54,54), (46,46,46), (33,33,33), (25,25,25),
    (16,16,16), (63,33,0), (63,42,0), (63,50,0), (63,58,0), (63,63,0),
    (63,63,12), (63,63,29), (63,63,25), (63,63,63), (0,33,63), (0,29,63),
    (0,25,63), (0,25,58), (0,21,58), (0,16,54), (0,16,54), (0,12,50),
    (0,12,50), (0,8,46), (0,4,46), (0,4,42), (0,4,0), (0,0,37),
    (0,0,37), (0,0,33), (0,0,0), (31,31,31), (27,27,27), (23,23,23),
    (16,16,16), (12,12,12), (8,8,8), (31,16,0), (31,21,0), (31,25,0),
    (31,29,0), (31,31,0), (31,31,6), (31,31,14), (31,31,12), (31,31,31),
    (0,16,31), (0,14,31), (0,12,31), (0,12,29), (0,10,29), (0,8,27),
    (0,8,27), (0,6,25), (0,6,25), (0,4,23), (0,2,23), (0,2,21),
    (0,2,0), (0,0,18), (0,0,18), (0,0,16),
    ],
    3: [
    (0,0,0), (63,63,63), (54,54,54), (0,33,63), (0,29,63), (0,25,63),
    (0,25,58), (63,0,0), (54,0,0), (46,0,0), (37,0,0), (63,63,0),
    (63,54,0), (63,46,0), (63,37,0), (37,37,37), (0,63,0), (0,54,0),
    (0,46,0), (0,37,0), (0,21,58), (0,16,54), (0,16,54), (0,12,50),
    (0,12,50), (0,8,46), (0,4,46), (0,4,42), (0,0,42), (0,0,37),
    (0,0,37), (0,0,33), (0,0,0), (31,31,31), (27,27,27), (0,16,31),
    (0,14,31), (0,12,31), (0,12,29), (31,0,0), (27,0,0), (23,0,0),
    (18,0,0), (31,31,0), (31,27,0), (31,23,0), (31,18,0), (18,18,18),
    (0,31,0), (0,27,0), (0,23,0), (0,18,0), (0,10,29), (0,8,27),
    (0,8,27), (0,6,25), (0,6,25), (0,4,23), (0,2,23), (0,2,21),
    (0,0,21), (0,0,18), (0,0,18), (0,0,16),
    ],
}

# Shape numbers named in Source/TILEDEFS.H. Unnamed numbers are extra
# animation frames/variants of the preceding named tile.
SHAPE_NAMES = {
    0: "EMPTYSPACE", 1: "WALL", 5: "TEXTWALL", 9: "PILLAR", 13: "OFFSWITCH",
    17: "ONSWITCH", 21: "WATERBARREL", 25: "HOLEBARREL", 29: "BARREL",
    33: "BLUEBARREL", 37: "CRATE", 41: "REDCRATE", 45: "CHEST",
    49: "GREENCHEST", 53: "FLOOR", 54: "REDTARGET", 55: "GREENTARGET",
    56: "BLUETARGET", 57: "MARKEDTILE", 58: "OFFPLATE", 59: "ONPLATE",
    60: "UPARROW", 61: "RIGHTARROW", 62: "DOWNARROW", 63: "LEFTARROW",
    64: "REDGEM", 65: "GREENGEM", 66: "BLUEGEM", 67: "YELLOWGEM",
    68: "REDKEY", 69: "GREENKEY", 70: "BLUEKEY", 71: "GLASS", 76: "REDLOCK",
    77: "GREENLOCK", 78: "BLUELOCK", 79: "WATERCRATE", 80: "HOLECRATE",
    81: "WOOD", 82: "GRASS", 83: "HOLE", 84: "WATER", 88: "LAVA",
    92: "LAVADEBRIS1", 96: "LAVADEBRIS2", 100: "GUY", 148: "GUYMAGIC",
    196: "GUYPUSH", 228: "GUYMORPH", 252: "REDGEMON", 253: "GREENGEMON",
    254: "BLUEGEMON", 255: "YELLOWGEMON", 256: "YIELD", 257: "YIELDPRESSED",
    258: "STOP", 259: "STOPPRESSED", 260: "EYEFRAME1", 261: "EYEFRAME2",
    262: "EYEFRAME3", 263: "EYEFRAME4", 264: "OPENEYE", 265: "F1SHAPE",
    266: "F2SHAPE", 267: "F3SHAPE", 268: "F4SHAPE", 269: "F5SHAPE",
    270: "F6SHAPE", 271: "F7SHAPE", 272: "F8SHAPE", 273: "F9SHAPE",
    274: "F10SHAPE", 275: "TITLETEXTBG",
    # Mouse pointers: shapes[276 + pointer id] (see drawmouse() in GFX.C)
    276: "STDPOINTER", 277: "CROSSHAIRS", 278: "BRACKETCROSSHAIRS",
    279: "UPARROWPTR", 280: "RIGHTARROWPTR", 281: "DOWNARROWPTR",
    282: "LEFTARROWPTR", 283: "BUSYPOINTER", 284: "BLANKPOINTER",
}

# First shape of each four-quarter object: over tiles 1..49 and the player
# frames GUY..GUYMORPH (base + facing 0/4/8/12 + walk frame 0/16/32).
OBJECT_BASES = list(range(1, 53, 4)) + list(range(100, 252, 4))

# Floor tiles are drawn opaque with Blit24(); so is the title text panel.
OPAQUE_SHAPES = set(range(53, 100)) | {275}
# The title text panel is only ever shown on the title screen.
SHAPE_PALETTE = {275: 3}

FONT_PALETTE = [(0, 0, 0), (255, 255, 255)]


def vga_to_rgb(palette):
    return [tuple((c * 255 + 31) // 63 for c in rgb) for rgb in palette]


def write_png(path, width, height, pixels, palette, transparent0=False):
    """Write an 8-bit indexed PNG. pixels is a bytes-like of width*height."""
    used = max(pixels) + 1 if pixels else 1
    pal = list(palette) + [(0, 0, 0)] * max(0, used - len(palette))
    raw = b"".join(b"\x00" + bytes(pixels[y * width:(y + 1) * width])
                   for y in range(height))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
    png += chunk(b"PLTE", b"".join(bytes(c) for c in pal[:256]))
    if transparent0:
        png += chunk(b"tRNS", b"\x00")
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def write_sheet(path, shapes, palette, transparent0, max_width=480, gap=2):
    """Pack shapes left-to-right into rows and write a single contact sheet."""
    placed, x, y, row_h, sheet_w = [], 0, 0, 0, 0
    for w, h, px in shapes:
        if w == 0 or h == 0:
            continue
        if x and x + w > max_width:
            x, y, row_h = 0, y + row_h + gap, 0
        placed.append((x, y, w, h, px))
        x += w + gap
        row_h = max(row_h, h)
        sheet_w = max(sheet_w, x - gap)
    sheet_h = y + row_h
    canvas = bytearray(sheet_w * sheet_h)
    for sx, sy, w, h, px in placed:
        for row in range(h):
            start = (sy + row) * sheet_w + sx
            canvas[start:start + w] = px[row * w:(row + 1) * w]
    write_png(path, sheet_w, sheet_h, canvas, palette, transparent0)


def read_shape_list(path):
    """Game format: [u8 w, u8 h, pixels] ... terminated by w == 0."""
    data = open(path, "rb").read()
    shapes, p = [], 0
    while p + 2 <= len(data) and data[p] != 0:
        w, h = data[p], data[p + 1]
        shapes.append((w, h, data[p + 2:p + 2 + w * h]))
        p += 2 + w * h
    return shapes


def read_shst(path):
    """Editor format. Returns (palette or None, [(w, h, pixels), ...])."""
    data = open(path, "rb").read()
    if data[:4] != b"SHST":
        raise ValueError("%s: not an SHST file" % path)
    _size, count, has_palette = struct.unpack_from(">IHH", data, 4)
    p, palette = 12, None
    if has_palette:
        palette = [tuple(data[p + i * 3:p + i * 3 + 3]) for i in range(256)]
        p += 768
    shapes = []
    for _ in range(count):
        w, h, _bpp = struct.unpack_from(">HHH", data, p)
        p += 6
        shapes.append((w, h, data[p:p + w * h]))
        p += w * h
    return palette, shapes


def shape_label(index):
    """'029_BARREL' for named shapes, '116_GUY+16' for offsets from a name."""
    base = max(n for n in SHAPE_NAMES if n <= index)
    if base == index:
        return "%03d_%s" % (index, SHAPE_NAMES[index])
    if index >= 100:
        return "%03d_%s+%d" % (index, SHAPE_NAMES[base], index - base)
    return "%03d" % index


def assemble_object(shapes, base):
    """Combine quarter shapes base..base+3 into one 48x48 pixel buffer."""
    canvas = bytearray(48 * 48)
    for part, (ox, oy) in enumerate(((0, 0), (24, 0), (0, 24), (24, 24))):
        w, h, px = shapes[base + part]
        for row in range(h):
            start = (oy + row) * 48 + ox
            canvas[start:start + w] = px[row * w:(row + 1) * w]
    return canvas


def char_label(code):
    ch = chr(code)
    return "%03d_%s" % (code, ch) if ch.isalnum() else "%03d" % code


def convert(out_dir, opaque):
    written = 0

    # Full-screen images
    for name, pal in (("LOGO", 2), ("TITLE", 3)):
        data = open(os.path.join(GAME_DIR, name + ".DAT"), "rb").read()
        write_png(os.path.join(out_dir, "Screens", name + ".png"), 320, 200,
                  data[:64000], vga_to_rgb(VGA_PALETTES[pal]))
        written += 1

    # Game tiles/shapes, numbered across TILES1..3
    game_pal = vga_to_rgb(VGA_PALETTES[1])
    all_shapes = []
    for fname in ("TILES1.DAT", "TILES2.DAT", "TILES3.DAT"):
        shapes = read_shape_list(os.path.join(GAME_DIR, fname))
        for w, h, px in shapes:
            index = len(all_shapes)
            pal = vga_to_rgb(VGA_PALETTES[SHAPE_PALETTE.get(index, 1)])
            write_png(os.path.join(out_dir, "Tiles", shape_label(index) + ".png"),
                      w, h, px, pal, not opaque and index not in OPAQUE_SHAPES)
            all_shapes.append((w, h, px))
            written += 1
        write_sheet(os.path.join(out_dir, "Sheets", fname[:-4] + ".png"),
                    shapes, game_pal, not opaque)
        written += 1

    # Assembled 48x48 objects
    objects = []
    for base in OBJECT_BASES:
        px = assemble_object(all_shapes, base)
        write_png(os.path.join(out_dir, "Objects", shape_label(base) + ".png"),
                  48, 48, px, game_pal, not opaque)
        objects.append((48, 48, px))
        written += 1
    write_sheet(os.path.join(out_dir, "Sheets", "Objects.png"), objects,
                game_pal, not opaque, max_width=600)
    written += 1

    # Game font (glyphs start at character 32)
    glyphs = read_shape_list(os.path.join(GAME_DIR, "PLASMA1.FNT"))
    for code, (w, h, px) in enumerate(glyphs, start=32):
        write_png(os.path.join(out_dir, "Font", "PLASMA1", char_label(code) + ".png"),
                  w, h, px, FONT_PALETTE, not opaque)
        written += 1
    write_sheet(os.path.join(out_dir, "Sheets", "PLASMA1.png"), glyphs,
                FONT_PALETTE, not opaque)
    written += 1

    # Editor tiles (own 8-bit palette; empty slots skipped)
    palette, shapes = read_shst(os.path.join(EDITOR_DIR, "ETILES.DAT"))
    for i, (w, h, px) in enumerate(shapes):
        if w and h:
            write_png(os.path.join(out_dir, "Editor", "Tiles", "%03d.png" % i),
                      w, h, px, palette, not opaque)
            written += 1
    write_sheet(os.path.join(out_dir, "Sheets", "ETILES.png"), shapes, palette,
                not opaque)
    written += 1

    # Editor font (slot number == character code)
    _, glyphs = read_shst(os.path.join(EDITOR_DIR, "PITSFONT.DAT"))
    for code, (w, h, px) in enumerate(glyphs):
        if w and h:
            write_png(os.path.join(out_dir, "Editor", "Font", char_label(code) + ".png"),
                      w, h, px, FONT_PALETTE, not opaque)
            written += 1
    write_sheet(os.path.join(out_dir, "Sheets", "PITSFONT.png"), glyphs,
                FONT_PALETTE, not opaque)
    written += 1

    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="output directory (default: DOS/Assets/Graphics)")
    parser.add_argument("--opaque", action="store_true",
                        help="do not make pixel value 0 transparent")
    args = parser.parse_args()
    count = convert(args.out, args.opaque)
    print("Wrote %d PNG files to %s" % (count, args.out))


if __name__ == "__main__":
    sys.exit(main())
