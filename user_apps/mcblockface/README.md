# BlockyBlockMcBlockFace

Author: Pieter Hooimeijer

BlockyBlockMcBlockFace game for the 2025 Communicator Badge. Use `install.py` to copy it into `firmware/badge/apps` and wire it to a user slot (A–D).

## Controls
The game is played sideways to make the best use of the Very Wide aspect ratio.

- `F1` – start a new game
- `.` – move left
- `5` – move right
- `2` – soft drop
- `7` – rotate counter-clockwise
- `8` – rotate clockwise
- `ESC` - exit

Play with the badge rotated 90° counter-clockwise (USB port down).

## Installer & Cleanup

- `install.py` — copies the app into `firmware/badge/apps/mcblockface`, updates a user slot (A–D), and keeps a backup of the original menu entry.
- `cleanup.py` — removes the installed copy from `firmware/badge/apps/` and restores the original menu entry (using the saved backup or `git`). It can auto-detect deployments or target a specific slot.

Run either script with `-h` for usage details.

## Notes

Getting this to run at a reasonable pace was a pain :)

Enjoy tweaking and extending!
