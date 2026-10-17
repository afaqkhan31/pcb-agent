# EasyEDA bridge spike: results (Sprint 1)

Date: ...   EasyEDA Pro version: ...   Run by: Shammas, guided by Hamdan

| # | Check | Pass? | Notes |
|---|---|---|---|
| 1 | Python connects to EasyEDA through the bridge (`check`) | | |
| 2 | All 3 LCSC numbers found and through-hole (`parts`) | | |
| 3 | Schematic placed; every pin name matches its net (`sch`, Hamdan checks) | | |
| 4 | ERC: no errors (warnings are OK) (`erc`) | | |
| 5 | Schematic imported into the PCB (`pcb`) | | |
| 6 | Auto layout put all 5 parts inside the outline (`pcb`) | | |
| 7 | Auto routing on BOTTOM only: all nets routed (`pcb`) | | |
| 8 | DRC: 0 errors (`drc`) | | |
| 9 | Rule format saved; we know where track width is stored (`rules`) | | |

## Decision
GO / NO-GO: ...
(GO if checks 1-5 and 7 pass. Layout can be done by our own code later if 6 fails.)

## Surprises / things to fix in Sprint 2
- ...

## Screenshots
![schematic](spike_schematic.png)
![pcb](spike_pcb.png)