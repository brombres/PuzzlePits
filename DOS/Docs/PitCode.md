# PitCode Bytecode Reference

PitCode is the scripting language Puzzle Pits levels use for dialogue, special rules, secrets and win conditions. Authors build programs from icons in the level editor (`Editor/EDITOR.TXT` §5). The editor compiles them into the bytecode described here, which is stored in the encrypted code blob of each `.PIT` file (see [PitFiles.md](PitFiles.md)).

This reference is derived from the interpreter in `Source/PITS.C` (`RunPitCode`, `GetRegVal`, `SetRegVal`, `PrintText`) and the constants in `Source/TILEDEFS.H`. A disassembler following these rules decodes all 141 programs in the 40 shipped levels cleanly. Each one ends with `END` exactly where the next program begins, and every jump lands on an instruction boundary.

## Conventions

- All multi-byte fields are **big-endian `u16`**.
- Every **jump offset** is relative to the address of the offset field itself: `target = address_of_offset_field + offset`. Offsets are always forward.
- Arithmetic and comparisons use **signed 16-bit** integers (Borland `int`), and overflow wraps.
- Coordinates are map cells, `x` and `y` in 1..21, with (1,1) at the top-left.

## Execution model

A program is started with four inputs: the program slot `index`, a cell `(x, y)` and a phase `onoff` (1 = ON, 0 = OFF).

1. If the slot is empty (`255`/`-1`, or `codeSize == 0`), nothing happens.
2. Registers `XPos`/`YPos` are set to `(x, y)`. For the special programs (`Intro`, `Master` and the gem programs) this is (0,0).
3. Instructions run from the program's `codeOffset` until `END`, `STOP`, `WIN`, an ON-phase `SWITCHOFF`, or a `GOTO` to an empty cell.

Execution is synchronous: the game waits for the program to finish, including any text boxes or `TARGET` clicks. A program can start others while it runs, for example through `REDGEMOFF` (which runs the RedGem program's OFF phase).

Each invocation has its own loop stack, 32 entries deep, with no overflow check. Unknown opcodes are skipped as 1-byte no-ops.

### Program skeleton

The editor wraps every program's code in an ON/OFF frame:

```
SWITCHON  ->A        ; when phase is OFF, jump to A
  ...ON-phase body...
A: SWITCHOFF         ; when phase is ON, return here
  ...OFF-phase body...
END
```

### When programs run

| Trigger | Program | Phase |
|---------|---------|-------|
| Level first entered (also on restart if no moves were made) | `Intro` | ON |
| Level loaded or restarted, before the first frame | `Master` | ON |
| Each move or wait, before the player moves | `Master` | ON |
| Each move or wait, if that gem is active and a program with that name exists | `RedGem`, `GreenGem`, `BlueGem` | ON |
| Player activates the gem (when the program exists) | gem program | ON |
| Gem turned off (by the player, or by `xxxGEMOFF`) | gem program | OFF |
| Player bumps a **sign** (over = 5) | linked program | ON |
| Player bumps an **off switch** (13), which turns it on | linked program | ON |
| Player bumps an **on switch** (17), which turns it off | linked program | OFF |
| Player or object moves onto a **raised plate** (58), which goes down to 59 | linked program | ON |
| A **lowered plate** (59) is left empty | linked program | OFF |
| Player uses a matching key while standing on a **lock** (76–78), which becomes 59 | linked program | ON |
| End of each move or wait, after arrows, plates and other events | `Master` | OFF |

Plates do not reset themselves. The OFF phase of a plate program must run `POPUP` to raise it again.

A level is won when every red, green and blue target is covered, or when a program executes `WIN`.

## Operand encoding

Most instruction arguments are **value operands**. A value operand is one tag byte, possibly followed by nested value operands for its arguments. The same encoding is used for reading (the source) and for writing (the destination of `LET`, `ADD`, ..., and the `FOR` counter).

| Byte | Meaning | Extra operands | Read | Write |
|-----:|---------|----------------|------|-------|
| 0–100 | Literal 0..100 | — | value | ignored |
| 101–200 | Literal −100..−1 (`byte − 201`) | — | value | ignored |
| 201–210 | `R0`–`R9` | — | ✔ | ✔ |
| 211–227 | Named registers (table below) | — | ✔ | ✔ |
| 228 | `Walkable(t)` | `t` | ✔ | ✔ |
| 229 | `Delta(a, b)` | `a`, `b` | `a + b` | ignored (operands still consumed) |
| 230 | `Under(x, y)` | `x`, `y` | ✔ | ✔ |
| 231 | `Over(x, y)` | `x`, `y` | ✔ | ✔ |
| 232 | `LastPushed(x, y)` | `x`, `y` | ✔ | ✔ |
| 233 | `RedGemOn` | — | ✔ | ignored |
| 234 | `GreenGemOn` | — | ✔ | ignored |
| 235 | `BlueGemOn` | — | ✔ | ignored |
| 236–255 | Unused | — | 0 | ignored |

Literals can only be −100..100, but registers hold full 16-bit values. `Delta` is the only way to build an expression, and operands nest freely, for example `Under(Delta(-1, XGuy), YGuy)`.

## Registers

The register file `regs[35]` is indexed by `tag − 201`.

| Tag | Name | Description |
|----:|------|-------------|
| 201–210 | `R0`–`R9` | General purpose. Zeroed every time the level is loaded or restarted. |
| 211 | `XGuy` | Player X. Writing it teleports the player without any checks. |
| 212 | `YGuy` | Player Y. |
| 213 | `LastX` | Player X before the current move. |
| 214 | `LastY` | Player Y before the current move. |
| 215 | `Facing` | Player facing: 0 = N, 4 = E, 8 = S, 12 = W. |
| 216 | `RedGems` | Red gems held. ¹ |
| 217 | `GreenGems` | Green gems held. ¹ |
| 218 | `BlueGems` | Blue gems held. ¹ |
| 219 | `YellowGems` | Picking up a yellow gem sets this to **−1** (not +1); levels test `YellowGems == -1`. ¹ |
| 220 | `RedKeys` | Red keys held. ¹ |
| 221 | `GreenKeys` | Green keys held. ² |
| 222 | `BlueKeys` | Blue keys held. ² |
| 223 | `InputValue` | The number typed at the last `INPUT` (parsed with `%d`; left unchanged if the text is not a number). |
| 224 | `XPos` | The cell the program was started for, or the cell chosen by `TARGET`, or the X set by `GOTO`. |
| 225 | `YPos` | Same, for Y. |
| 226 | `Moves` | Move count mod 100. Recomputed before every move, so writes do not stick. |
| 227 | `HectoMoves` | Move count ÷ 100. Also recomputed. |
| 228 | `Walkable(t)` | 1 if tile type `t` can be walked on or through. Reset each level so that only tiles 53–82 are walkable. `t` is clamped to ≥ 0 but has no upper bound; keep it ≤ 100. |
| 229 | `Delta(a,b)` | `a + b`. Read only. |
| 230 | `Under(x,y)` | UnderTile at `(x,y)`. |
| 231 | `Over(x,y)` | OverTile at `(x,y)`. Reads **100** at the player's cell, unless the green gem is active and no `GreenGem` program exists. |
| 232 | `LastPushed(x,y)` | Direction the object at `(x,y)` was last pushed; −1 = none. Used for sliding on ice. The game's push code stores 0–3 (N, E, S, W), although `EDITOR.TXT` documents 0, 4, 8, 12. |
| 233–235 | `RedGemOn`, `GreenGemOn`, `BlueGemOn` | Whether each gem is active. **Read only**: writes are silently ignored, although `EDITOR.TXT` says they can be set. Use `xxxGEMOFF` instead. |

¹ Writing tags 216–220 also redraws the inventory sidebar.
² Writing 221–222 does not redraw the sidebar right away.

Inventory registers (216–222) carry over from one level to the next. They are saved when a level is completed and restored when the next one loads.

**Writing `Under` / `Over`**: the coordinates are clamped to 1..21 and the value to 0..100. The cell's `LastPushed` is reset to −1, and then the normal tile logic runs. For example, writing a barrel (29) over water turns it into a floating barrel. Writing an arrow (60–63) to `Under` also registers it as an active arrow. Reading also clamps the coordinates.

## Instruction reference

`v` is a value operand, `off` is a `u16` jump offset, `len` is a `u16` byte count.

| Op | Mnemonic | Encoding | Summary |
|---:|----------|----------|---------|
| 0 | `END` | `00` | End the program. |
| 1 | `ENDIF` | `01` | No-op marker. The target of IF and ELSE jumps. |
| 2 | `NEXT` | `02` | Close the innermost `FOR`. |
| 3 | `ELSE` | `03 off` | Jump to the end of the ELSE block. |
| 4 | `SWITCHOFF` | `04` | When the phase is ON, end the program. When it is OFF, continue. |
| 5 | `SWITCHON` | `05 off` | When the phase is ON, continue. When it is OFF, jump. |
| 6 | `IFEQ` | `06 v v off` | If `a == b`. |
| 7 | `IFLT` | `07 v v off` | If `a < b`. |
| 8 | `IFGT` | `08 v v off` | If `a > b`. |
| 9 | `IFLE` | `09 v v off` | If `a <= b`. |
| 10 | `IFGE` | `0A v v off` | If `a >= b`. |
| 11 | `IFNE` | `0B v v off` | If `a != b`. |
| 12 | `IFINPUT` | `0C len off chars[len]` | If the last typed input matches the text. |
| 13 | `FOR` | `0D v v v off` | Loop `counter` from `start` to `end`. |
| 14 | `REDRAW` | `0E` | Redraw the screen. |
| 15 | `APPEAR` | `0F` | Redraw with a fade-in and the magic sound. |
| 16 | `STOP` | `10` | End the program. |
| 17 | `WIN` | `11` | Complete the level and end the program. |
| 18 | `TARGET` | `12` | Let the player pick a cell; the result goes to `XPos`/`YPos`. |
| 19 | `REDGEMOFF` | `13` | Turn the red gem off. |
| 20 | `GREENGEMOFF` | `14` | Turn the green gem off. |
| 21 | `BLUEGEMOFF` | `15` | Turn the blue gem off. |
| 22 | `POPUP` | `16` | Raise the pressure plate at the program's own cell. |
| 23 | `LET` | `17 dst src` | `dst = src` |
| 24 | `ADD` | `18 dst v` | `dst = dst + v` |
| 25 | `SUB` | `19 dst v` | `dst = dst − v` |
| 26 | `MUL` | `1A dst v` | `dst = dst × v` |
| 27 | `DIV` | `1B dst v` | `dst = dst ÷ v` (truncating; 0 if `v == 0`) |
| 28 | `SWAPOVER` | `1C v v v v` | Exchange the OverTiles at `(x1,y1)` and `(x2,y2)`. |
| 29 | `SWAPUNDER` | `1D v v v v` | Exchange the UnderTiles at `(x1,y1)` and `(x2,y2)`. |
| 30 | `GOTO` | `1E v v v v` | Continue in the program linked at `(x,y)`, with `XPos`/`YPos` set to `(asX,asY)`. |
| 31 | `CHANGEMAP` | `1F len (v v v)...` | Place tiles from a list of `(x, y, tile)` triples. |
| 32 | `PRINT` | `20 len chars[len]` | Show a text box. |
| 33 | `INPUT` | `21 len chars[len]` | Show a text box and read a line of input. |

### Control flow

**IF family (6–11, 12).** The interpreter evaluates the condition. If it is true, execution continues after the `off` field (or after the text, for `IFINPUT`) into the THEN body. If it is false, it jumps to `off`. When the jump lands on an `ELSE`, the interpreter also skips that 3-byte instruction to enter the ELSE body. The compiled shape is:

```
IFxx a, b, ->E           IFxx a, b, ->X
  ...then...               ...then...
E: ELSE ->X              X: ENDIF
  ...else...
X: ENDIF
```

Without an ELSE, the false jump lands on the `ENDIF`. With one, it lands on the `ELSE`. The `ELSE` reached at the end of the THEN body jumps to the `ENDIF`. IFs nest freely, and each one has its own `ENDIF`.

**`IFINPUT`**: compares the text with the last line typed at an `INPUT` (up to 16 chars, kept across programs) using a case-insensitive comparison of the first `len` characters. This is a **prefix** match: input `blackbird` matches the text `black`. In the encoding, the `off` field comes before the text and is relative to `off`'s own address, as usual.

**`FOR counter, start, end`**: sets `counter = start` and enters the body. **The body always runs at least once.** At the matching `NEXT`, the interpreter re-reads the `FOR` operands:

- If `end > start` (counting up): when `counter < end`, it sets `counter = counter + 1` and repeats the body. Otherwise it exits.
- Otherwise (counting down): when `counter > end`, it sets `counter = counter − 1` and repeats. Otherwise it exits.

The bounds are inclusive. Changing the counter inside the body affects the loop. The counter can be any writable operand, such as `Over(3,4)`. On exit, execution jumps to the `FOR`'s `off`, which points just past its `NEXT`.

```
FOR R0, 1, -1, ->X       ; R0 = 1, 0, -1
  ...body...
  NEXT
X:
```

**`SWITCHON` / `SWITCHOFF`**: see [Program skeleton](#program-skeleton). The editor puts exactly one pair at the top level of each program.

**`STOP`** ends only the current program. **`WIN`** marks the level as won (the "Level Complete" screen follows once control returns to the game loop) and ends the program.

**`GOTO x, y, asX, asY`**: looks up the program linked to cell `(x,y)` in the link grid and continues there. It sets `XPos = asX` and `YPos = asY`.

- If `(x,y)` is outside 1..21, `GOTO` does nothing and execution continues with the next instruction.
- If the cell has no program linked (255) or the program is empty, the current program ends.
- The ON/OFF phase is unchanged, and so is the loop stack.
- `POPUP` in the target program still uses the *original* invocation cell, not `asX, asY`.

### Map and state

**`CHANGEMAP len, triples...`**: `len` is the byte length of the triple list. Because operands can be nested, triples vary in size. Each triple `(x, y, tile)` is applied in order:

| `tile` | Effect |
|--------|--------|
| 0–52, or 100 | Sets the OverTile. |
| 53–99 | Sets the UnderTile. Arrows (60–63) are registered as active arrows. |
| −1 | Clears the UnderTile. |
| −2 | Clears the OverTile. |
| −3 | Clears both. |

The other layer is left alone. After placing a tile, `LastPushed` is reset (except for the clear values) and normal tile logic runs.

Quirks and bugs:
- `x` and `y` are **not range-checked**, so out-of-range values write outside the map arrays.
- Placing **33, 41 or 49** (an object already on its target) hits a bug. The interpreter breaks out of the triple loop without placing the tile, and the remaining triple bytes are then **executed as opcodes**. Place 29, 37 or 45 on the target tile instead; the tile logic converts it.

**`SWAPOVER` / `SWAPUNDER x1, y1, x2, y2`**: exchange the two cells' tiles along with their `LastPushed` values, then run tile logic on both cells. If either cell is outside 1..21, nothing happens.

`SWAPOVER` moves the player too: if one of the cells is the player's position, `XGuy`/`YGuy` follow the swap. Following `SWAPOVER` with `APPEAR` gives a teleport effect.

**`POPUP`**: sets the UnderTile at the program's invocation cell to a raised plate (58) and plays the plate sound. It ignores `XPos`/`YPos`.

**`REDGEMOFF` / `GREENGEMOFF` / `BLUEGEMOFF`**: if that gem is active, these turn it off, run its gem program in the OFF phase, and decrement its count. Otherwise they do nothing.

### Display and input

**`REDRAW`** draws the current map and presents it. **`APPEAR`** queues the magic sound, then redraws and fades in.

**`PRINT` / `INPUT len, text`**: show `text` in a stone panel over the 216×168 map view.

- Byte `0x0A` starts a new line. Lines word-wrap at about 205 pixels.
- Long text is split into pages, and the player clicks, presses Enter or presses Space to advance.
- `INPUT` then shows a prompt on its last page and reads up to 16 printable characters, ending with Enter. The text is kept for `IFINPUT`, and its numeric value goes to `InputValue`.
- `REDRAW` is commonly placed before `PRINT` so the panel appears over an up-to-date map.

**`TARGET`**: switches the cursor to crosshairs and waits for the player to click a cell in the map view (with the mouse or arrow keys, plus Enter or F1). It converts the click to map coordinates relative to the player (the view is 9 × 7 cells, with the player at view cell (4,3)). If the result is outside 1..21, `XPos` and `YPos` are both set to 0.

## Worked example

`MoveGem` from `LEVEL01.PIT`, disassembled (addresses are offsets into the code blob). When ON, it searches the four neighbouring cells of its own cell for an empty floor tile and swaps the gem under it into that cell.

```
0668 SWITCHON ->0762
0671   FOR R0 = 1 .. -1           exit->0762
0677     FOR R1 = -1 .. 1         exit->0761
0683       IFEQ R0, 0             ->0722 (ELSE)
0688         IFNE R1, 0           ->0721
0693           IFEQ Over(XPos, Delta(R1,YPos)), 0     ->0720
0702             IFEQ Under(XPos, Delta(R1,YPos)), 53 ->0719
0711               SWAPUNDER XPos, YPos, XPos, Delta(R1,YPos)
0718               STOP
0719             ENDIF
0720           ENDIF
0721         ENDIF
0722       ELSE                   ->0759
0725         IFEQ R1, 0           ->0758
0730           IFEQ Over(Delta(R0,XPos), YPos), 0     ->0757
0739             IFEQ Under(Delta(R0,XPos), YPos), 53 ->0756
0748               SWAPUNDER XPos, YPos, Delta(R0,XPos), YPos
0755               STOP
0756             ENDIF
0757           ENDIF
0758         ENDIF
0759       ENDIF
0760     NEXT
0761   NEXT
0762 SWITCHOFF
0763 END
```

Two instructions decoded byte by byte:

`0671 FOR R0 = 1 .. -1` is `0D C9 01 C8 00 57`:

| Bytes | Meaning |
|-------|---------|
| `0D` | `FOR` |
| `C9` | counter `R0` (201) |
| `01` | start: literal 1 |
| `C8` | end: literal −1 (200 − 201) |
| `00 57` | `off` = 87; the field is at 0675, so the exit is 0762 |

`0693 IFEQ Over(XPos, Delta(R1,YPos)), 0` is `06 E7 E0 E5 CA E1 00 00 14`:

| Bytes | Meaning |
|-------|---------|
| `06` | `IFEQ` |
| `E7` | `Over(` (231), which takes two operands |
| `E0` | `XPos` (224) |
| `E5 CA E1` | `Delta(R1, YPos)` (229, 202, 225) |
| `00` | literal 0 |
| `00 14` | `off` = 20; the field is at 0700, so the target is 0720 |
