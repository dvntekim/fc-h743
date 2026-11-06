# Contributing to fc-h743

Review comments are the most useful contribution right now. The board is a draft and nothing
has been built.

## Reviewing
- Work through [REVIEW.md](REVIEW.md). Open an issue with the **Design review finding** template
  for anything that fails, quoting the datasheet section or the measurement.
- [docs/design_review.md](docs/design_review.md) lists what was already checked against each
  vendor guide, so you can skip or challenge it.

## Changing the design
1. The schematic is generated: change `scripts/design.py` (parts, values, nets, LCSC numbers),
   then run `scripts/build_sch.sh`. Do not hand-edit the `.kicad_sch` files.
2. The layout is hand-finished: `kicad/fc.kicad_pcb` is the source of truth. Edit it in
   KiCad 9 and keep DRC at 0 errors and 0 unconnected with schematic parity.
3. Pin changes go through `scripts/pinmap_check.py` and the PX4 port in `firmware/`.
4. Add a line to `CHANGELOG.md` under *Unreleased*.
5. Open a pull request. CI must pass: ERC, DRC with parity, pin map, KiBot outputs and the PX4
   build.

## Bring-up reports
Use the **Bring-up / erratum** issue template. Include the board serial, what was measured,
with what instrument, and a photo or scope capture.

## Releases
A tag `rev-<letter>-draft<n>` builds a GitHub pre-release with the fab package. A revision
loses "draft" only after REVIEW.md is signed off by someone other than its author.
