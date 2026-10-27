# Puzzle Pits DOS Overview

There's no modern toolchain here, so there are no lint or test commands.

- **Layout:** the source is in `DOS/Source/`, the shipped game and its 40 levels are in `DOS/Game/PITS95/`, and the level editor is only included as a program file and its docs (no source code).
- **Building:** the `.BAT` scripts call Borland `bcc` with the large memory model (`-ml`), run under DOS or DOSBox. Two problems in them:
  - `MALL.BAT` names `gfxa.c`, but the file is actually `GFXA.ASM`.
  - `MDEMO.BAT` names `pitsdemo.c`, which is `DEMO.C` in this repo.
- **Architecture:**
  - `PITS.C` holds the whole game, and `DEMO.C` is a near-copy of it, so logic changes usually need to go in both.
  - `TILEDEFS.H` holds the PitCode opcodes and registers (the level scripting language).
  - `GFX.C` and `GFXA.ASM` handle graphics in VGA mode 13h, drawing to a back buffer and then swapping it to the screen.
  - The sound code is third-party DiamondWare code.
- **The `.PIT` level file format:** the magic number, the encrypted password and title, the compressed floor and object layers, and the XOR-encrypted PitCode bytecode. Five program names (`Intro`, `Master` and the three gem hooks) are special.
- **Hidden strings:** some names and keys are stored as offset characters and decoded when first used (for example, the file key decodes to "Mindy"). These must stay matched to the existing level files and the editor.
- **Level progression:** each level's password unlocks the level *after* it.
- **Coding conventions:** the 16-bit `WORD` types, `far` pointers, the `strcpy`/`strcat` far-version macros, and the drawing pattern (draw to the back buffer between `OwnBlit` and `DisownBlit`, then `ScreenSwap`).
