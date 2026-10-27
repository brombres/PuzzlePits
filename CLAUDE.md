# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Puzzle Pits is a 1995/96 MS-DOS puzzle game (Sokoban-style: push barrels/crates/glass chests onto matching blue/red/green targets) written in 16-bit real-mode C for Borland C++ plus some TASM assembly. This repo is an archive of the original source and shipped binaries; there is no modern build, test suite, or linter.

- `DOS/Source/` — game source (the only code in the repo).
- `DOS/Game/PITS95/` — the shipped game: `PITS.EXE`, data files (`TILES*.DAT`, `LOGO.DAT`, `TITLE.DAT`, `PLASMA1.FNT`, `*.WAV`), `LEVELS/LEVELxx.PIT`, and `MANUAL.TXT`.
- `DOS/PitFiles.md`, `DOS/PitCode.md` — verified references for the `.PIT` level format and the PitCode bytecode.
- `DOS/Tools/dat2png.py` — stdlib-only Python converter for all `.DAT`/`.FNT` graphics (formats documented in its docstring); run `python3 DOS/Tools/dat2png.py` to regenerate `DOS/Assets/Graphics/`.
- `DOS/Editor/` — the level editor binary (`EDIT.EXE`, a later djgpp rebuild) and `EDITOR.TXT`, which is the authoritative reference for the level format concepts and the PitCode scripting language (predefined program names, event sequencing, registers, object IDs). **Editor source is not in the repo.**

## Building

Builds use the Borland `bcc` compiler, large memory model (`-ml`), run under DOS (e.g. DOSBox). Scripts in `DOS/Source/`:

- `MALL.BAT` — compile all modules to `.obj` (`bcc -c -ml ...`). Note it lists `gfxa.c`, but the file is actually `GFXA.ASM` (needs TASM).
- `MPITS.BAT` — compile `pits.c` and link with the other `.obj` files → `pits.exe`. `MPITSO.BAT` relinks from `pits.obj` only.
- `MDEMO.BAT` / `MDEMOO.BAT` — same for the demo build; they reference `pitsdemo.c`, which corresponds to `DEMO.C` in this repo.
- `MGFX.BAT` / `MGFXO.BAT` — standalone gfx test build (the test `main()` in `GFX.C` is commented out).
- `INSTALL.BAT` / `NEWDISK.BAT` — floppy distribution scripts, not build steps.

The game must run from a directory containing the data files and a `levels\` subdirectory (`LEVELPATH`). To play, run `DOS/Game/PITS95/PITS.EXE` in DOSBox.

## Architecture

- **`PITS.C`** — the entire game: title menu/password entry (`main`), level loading (`GameLoadLevel`, `ProcessLevel`), the PitCode interpreter (`RunPitCode`, `GetRegVal`/`SetRegVal`), tile interaction rules (`CheckGameTileLogic`, `CheckStuff`, `CheckUnderGuy`), player movement/pushing/pathfinding (`MoveGuy`, `PathFind`, `CheckAutoWalk`), rendering (`Gdrall`, `DrawSideBar`), and `GameMainLoop`.
- **`DEMO.C`** — a near-copy of `PITS.C` for the demo build (starts at level `Demo01`, different menu). Changes to game logic usually need to be mirrored in both.
- **`TILEDEFS.H`** — platform defines (`_ibmpits_`; `_amigapits_` branches are vestiges of an Amiga version), tile IDs, PitCode opcodes (`CMD_*`), register IDs (`REG_*`, numbered from 201 and indexed as `regs[REG_X-201]`), sound IDs, `struct GameVars`, `struct PitCode`.
- **`GFX.C` / `GFXA.ASM`** — VGA mode 13h (320x200x256) with a `LOGIC` back buffer (`farmalloc`'d 64000 bytes) and `PHYSIC` screen, `ScreenSwap` to present; 16/24px tile blitters from three tile banks; bitmap font; software mouse cursor; palette fades; `.DAT` asset loading; `gfxInit`/`cleanExit` (also initializes sound). `GFXA.ASM` provides `setmode`, palette, mouse INT 33h, and the INT 9 keyboard handler filling `keytable[]`. `KEYINTR.ASM` is an older alternate keyboard handler.
- **`FILE.C`** — big-endian `ReadWord`, `ReadMem`, and `ReadString` (length XOR 22, contents decrypted with `cryptkey`).
- **Sound** — `DIG.C`, `DMA.C`, `SB.C`, `ENV.C`, `LOAD.C` and headers are third-party DiamondWare Sound Blaster code (BLASTER env parsing, DMA playback, `.WAV` loading). `OLDSOUND.H` is unused legacy.

### Level file (`.PIT`) format

Read by `GameLoadLevel`: magic word `0x0895`; encrypted password string; encrypted title string; RLE-encoded `under` (floor) layer and `over` (object) layer via `ReadRun` into 23x23 `WORD` grids (outer border forced to 0); number of PitCode programs; if nonzero, an RLE `pitcode` grid mapping cells to programs, then per program: index, name, code size, code offset; then total code length and a bytecode blob XOR-encrypted with a second key. Program names `Intro`, `Master`, `RedGem`, `GreenGem`, `BlueGem` are special hooks.

### Obfuscated strings

Several strings (`cryptkey` in `FILE.C`, the level key in `GameLoadLevel`, the starting level name in `main`) are stored with per-character offsets and decoded in place at first use (e.g. `'M'-4,'i'-8,...` → `"Mindy"`). Preserve this pattern; the encoded forms must stay consistent with existing `.PIT` files and `EDIT.EXE`.

### Level progression

`IncrementLevel` increments the numeric suffix of the level name in place (`Level01` → `Level02`), and the game ends when the next file is missing. Password entry scans `levels\*.pit` with `findfirst`/`findnext` (`GetLevelName`) for the file whose stored password matches, then calls `IncrementLevel`, so a level's password unlocks the level *after* it. Level names must end in a two-digit number (see `EDITOR.TXT` §3).

## Code conventions

- Use the `file.h` typedefs (`WORD` = 16-bit `int`, `UWORD`, `UBYTE`, `LONG`, `CHAR` = `char far`) and `far` pointers; `int` is 16 bits.
- `strcpy`/`strcat`/`strnicmp` are macro-redirected to `_f*` far versions in `TILEDEFS.H`.
- Drawing pattern: `OwnBlit()` … blits … `DisownBlit()`, draw to `LOGIC`, then `ScreenSwap()`.
- Input is polled via `CheckMouse()`, which updates globals `inkey`, mouse position, and buttons.
