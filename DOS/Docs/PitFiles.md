# Puzzle Pits `.PIT` Level File Format

This document describes the binary format of Puzzle Pits level files (`LEVELS/*.PIT`) in enough detail to read and fully decode one. It is derived from the game's loader (`GameLoadLevel`, `ReadRun` in `Source/PITS.C`; `ReadWord`, `ReadString`, `Decrypt` in `Source/FILE.C`) and was checked against all 40 shipped levels. Every one of them parses exactly to end-of-file with the procedure below.

The bytecode stored in the file is documented separately in [PitCode.md](PitCode.md).

## Primitive types

| Type   | Size     | Encoding |
|--------|----------|----------|
| `u8`   | 1 byte   | Unsigned byte. |
| `u16`  | 2 bytes  | Unsigned 16-bit integer, **big-endian** (high byte first). The game reads it as a signed 16-bit `int`. |
| `estr` | variable | Encrypted string (see below). |

### Encrypted strings (`estr`)

```
u16   lenx        // actual length = lenx XOR 22 (0x16)
u8    data[len]   // XOR-encrypted with the string key, no terminator
```

Decrypt `data` by XORing byte `i` with `KEY[i mod 5]`, where `KEY` is the ASCII string **`Mindy`** (`4D 69 6E 64 79`). The key restarts at position 0 for every string.

(In the source, the key is stored obfuscated as `{'M'-4,'i'-8,'n'-12,'d'-16,'y'-20}` and decoded at startup.)

## File layout

| # | Field | Type | Notes |
|---|-------|------|-------|
| 1 | `magic` | `u16` | Always `0x0895` (bytes `08 95`). The game refuses to load anything else. |
| 2 | `password` | `estr` | Password shown when this level is completed. Typing it on the title screen starts the **next** level. Max 20 chars. |
| 3 | `title` | `estr` | Level title shown in the status bar. Max 100 chars. |
| 4 | `under` | grid | Floor ("UnderTile") layer. |
| 5 | `over` | grid | Object ("OverTile") layer. |
| 6 | `numPrograms` | `u16` | Number of PitCode programs. If 0, the file ends here. |
| 7 | `links` | grid | *Only if `numPrograms > 0`.* Maps each map cell to a program index. |
| 8 | `programs[numPrograms]` | records | *Only if `numPrograms > 0`.* Program directory (see below). |
| 9 | `codeLen` | `u16` | *Only if `numPrograms > 0`.* Length of the bytecode blob. |
| 10 | `code[codeLen]` | `u8[]` | *Only if `numPrograms > 0`.* Encrypted bytecode blob. |

There is no padding or alignment between fields, and nothing follows `code`.

## Grids

The game keeps the map in `WORD grid[23][23]`, indexed `grid[x][y]`. The playable area is `x = 1..21`, `y = 1..21`, and the outer ring (`x` or `y` equal to 0 or 22) is always 0. Only the 21×21 interior (441 cells) is stored.

### Encoding

A grid is a sequence of run-length pairs:

```
u8 count   // number of cells in this run (1..255)
u8 value   // tile value written to each of those cells
```

Pairs are read until all 441 interior cells are filled. The shipped files never let a run cross the end of a grid, so the next field begins immediately after the last pair.

### Cell order

Cells are filled **column by column**: `x` is the outer loop and `y` is the inner loop.

```
for x in 1..21:
    for y in 1..21:
        grid[x][y] = next run value
```

Runs continue across column boundaries without interruption. (The game does this by writing into the flat array `grid[23*23]` starting at index 24 (`x=1, y=1`), skipping the two border cells each time it reaches `y = 22`.)

When displaying a decoded map, put `x` on the horizontal axis and `y` on the vertical axis, with (1,1) at the top-left.

### Grid contents

**`under`** holds floor tiles. **`over`** holds walls and objects; the value `100` (GUY) marks the player's start position and is removed from the grid at load time. If no GUY is present, the player starts at (1,1).

**`links`** holds the index of the PitCode program linked to each cell, or `255` for none. A program only fires from its cell if that cell holds a sign, switch, pressure plate or lock (see [PitCode.md](PitCode.md#when-programs-run)). Programs with the special names below run regardless of links.

### Tile values

UnderTiles (`under` layer, range 53–96):

| Value | Tile | Value | Tile | Value | Tile |
|------:|------|------:|------|------:|------|
| 0 | Empty space (pit) | 62 | Down arrow | 76 | Red lock |
| 53 | Floor | 63 | Left arrow | 77 | Green lock |
| 54 | Red target | 64 | Red gem | 78 | Blue lock |
| 55 | Green target | 65 | Green gem | 79 | Water with sunken crate |
| 56 | Blue target | 66 | Blue gem | 80 | Hole with crate (`HOLECRATE`) |
| 57 | Marked tile | 67 | Yellow gem | 81 | Wood |
| 58 | Pressure plate (up) | 68 | Red key | 82 | Grass |
| 59 | Pressure plate (down) | 69 | Green key | 83 | Hole |
| 60 | Up arrow | 70 | Blue key | 84 | Water |
| 61 | Right arrow | 71 | Glass (ice) | 88 | Lava |
| | | | | 92, 96 | Lava debris |

OverTiles (`over` layer, range 0–52, plus 100):

| Value | Tile | Value | Tile |
|------:|------|------:|------|
| 0 | Nothing | 29 | Barrel |
| 1 | Wall | 33 | Barrel on blue target |
| 5 | Sign (text wall) | 37 | Crate |
| 9 | Pillar | 41 | Crate on red target |
| 13 | Switch (off) | 45 | Glass chest |
| 17 | Switch (on) | 49 | Chest on green target |
| 21 | Barrel floating in water | 100 | Player start (GUY) |
| 25 | Barrel in hole | | |

The values skipped between entries (for example 2–4 after Wall, or 85–87 after Water) are reserved for that tile's extra graphics frames. Level files only use the base values listed. The authoritative list is `Source/TILEDEFS.H`.

Values seen across all 40 shipped levels: under `{0,53–58,60–68,71,76,77,79,81,82,84,88}`, over `{0,1,5,9,13,21,29,33,37,41,45,100}`.

## Program directory

`numPrograms` records follow the `links` grid:

```
u16   index      // program slot 0..99; the number used in the links grid
estr  name       // program name (Mindy-encrypted like other strings), max 15 chars
u16   codeSize   // declared size in bytes
u16   codeOffset // byte offset of the program's first instruction within the decrypted code blob
```

- Records are stored **sorted alphabetically by name**, not by `index`. Store each record at `programs[index]`.
- If `codeSize == 0`, the program is treated as empty and never runs.
- `codeSize` is otherwise **unreliable**. In 32 of the 141 shipped programs it is 5 more than the real length. The game uses it only for the zero test. To find where a program ends, decode until its `END` (opcode 0) instruction; in every shipped file that `END` is the byte just before the next program's `codeOffset`.
- Names are matched case-insensitively. Five names have special meaning: **`Intro`**, **`Master`**, **`RedGem`**, **`GreenGem`**, **`BlueGem`** (see [PitCode.md](PitCode.md#when-programs-run)).

## Code blob

`code` is the bytecode for all programs, stored back to back. Decrypt the **whole blob as one stream**: XOR byte `i` with `KEY2[i mod 6]`, where `KEY2` is the ASCII string **`Amanda`** (`41 6D 61 6E 64 61`). The key position does not restart per program, so to decrypt a program on its own, start at key position `codeOffset mod 6`.

(In the source this key is stored as `{'A'-5,'m'-10,'a'-15,'n'-20,'d'-25,'a'-30}`.)

The game loads the blob into a 32,768-byte buffer, and at most 100 programs (`MAXPITCODE`) are allowed.

## Related conventions

- Level files live in `levels\` relative to the game directory. Their names have at most 8 characters and end in a two-digit number (`LEVEL01`, `MyPit05`). Going to the next level increments that number (`LEVEL09` → `LEVEL10`), and the game ends when the next file does not exist.
- Password entry scans every `*.pit` in `levels\`, finds the file whose `password` matches (case-insensitive), and starts the level after it. A blank `xxx00` level whose password is the series name is the editor-recommended way to let players jump to the start of a custom series.
- The shipped game starts a new game at `Level01`.

## Reference decoder (Python 3)

```python
import struct

STR_KEY  = b"Mindy"
CODE_KEY = b"Amanda"

def xor(data, key, start=0):
    return bytes(b ^ key[(start + i) % len(key)] for i, b in enumerate(data))

class Reader:
    def __init__(self, data): self.d, self.p = data, 0
    def u8(self):
        v = self.d[self.p]; self.p += 1; return v
    def u16(self):
        v = struct.unpack_from(">H", self.d, self.p)[0]; self.p += 2; return v
    def bytes(self, n):
        v = self.d[self.p:self.p + n]; self.p += n; return v
    def estr(self):
        n = self.u16() ^ 22
        return xor(self.bytes(n), STR_KEY).decode("latin-1")
    def grid(self):
        """Returns g[x][y] for x, y in 0..22 (border cells are 0)."""
        g = [[0] * 23 for _ in range(23)]
        cells = [(x, y) for x in range(1, 22) for y in range(1, 22)]
        i = 0
        while i < len(cells):
            count, value = self.u8(), self.u8()
            for _ in range(count):
                x, y = cells[i]; g[x][y] = value; i += 1
        return g

def load_pit(path):
    r = Reader(open(path, "rb").read())
    if r.u16() != 0x0895:
        raise ValueError("not a Puzzle Pits level")
    level = {"password": r.estr(), "title": r.estr(),
             "under": r.grid(), "over": r.grid(),
             "links": None, "programs": {}, "code": b""}
    n = r.u16()
    if n:
        level["links"] = r.grid()
        for _ in range(n):
            index = r.u16()
            name = r.estr()
            size, offset = r.u16(), r.u16()
            level["programs"][index] = {"name": name, "size": size, "offset": offset}
        level["code"] = xor(r.bytes(r.u16()), CODE_KEY)
    assert r.p == len(r.d), "trailing data"
    return level
```

Example result for `LEVEL01.PIT`: password `First`, title `Starting Out`, four programs: `Master` (index 0, offset 0), `GemPlate` (1, 259), `MoveGem` (2, 668) and `Intro` (3, 764), with a 1,759-byte code blob. The player starts at (5,4) above a barrel that is already on a blue target at (5,5). `GemPlate` is linked to the pressure plate at (2,2).
