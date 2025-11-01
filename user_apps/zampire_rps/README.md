# Rock/Paper/Scissors

This is a simple Rock/Paper/Scissors game using a custom protocol on port 129.

Play with another person by pressing Start at approximately the same time as
your opponent, and then choosing Rock, Paper or Scissors. Each user's choice
will then be communicated via LoRa and the result will be displayed once a
local choice is made and remote choice is received.

Matching is completely based on temporal locality, so things will get
interesting if lots of games are happening concurrently, but otherwise the
simple protocol should work well enough.

## Installation Instructions

Copy rps.py to your badge/apps folder and modify badge/main.py to add RPS to
your User Apps menu.