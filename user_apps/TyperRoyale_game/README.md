# TyperRoyale - Typing Battle Royale Game

A competitive typing game for the Hackaday SuperCon 2025 badge. Test your typing speed and accuracy across multiple game modes and difficulty levels!

## Features

- **3 Game Modes:**
  - **Score Mode** - Type as many words as possible in 60 seconds
  - **Time Trial** - Complete 20 words as fast as possible
  - **Survival** - Endless typing until you run out of lives

- **4 Difficulty Levels:**
  - **Easy** - 3-5 letter common words (cat, dog, hack, code)
  - **Medium** - 4-8 letter tech words (python, badge, circuit, firmware)
  - **Hard** - 6-12 letter technical terms (microcontroller, cryptography)
  - **Expert** - Full phrases (hello world, internet of things)

- **Game Mechanics:**
  - Lives system (3 lives, lose 1 per mistake)
  - Streak tracking (bonus points for consecutive correct words)
  - Real-time visual feedback (correct/incorrect character highlighting)
  - Backspace correction allowed
  - Ranked mode with persistent leaderboards

- **100+ Word Vocabulary** - Conference-themed, hacker slang, and technical jargon

- **Persistent Leaderboards** - Top 5 scores saved for each mode/difficulty combination (45 total leaderboards!)

## Installation

### Option A: Command Line Installation (Using ampy)

If you have `ampy` installed and your badge is connected:

```bash
# Set up ampy (if not already installed)
pip install adafruit-ampy
export PATH="/home/distiller/.local/bin:$PATH"

# Navigate to the TyperRoyale_game directory
cd user_apps/TyperRoyale_game/

# Upload main app file to badge
ampy --port /dev/ttyACM0 put typer_royale_app.py /apps/userB.py

# Upload library files
ampy --port /dev/ttyACM0 put libs/typer_game.py /libs/typer_game.py
ampy --port /dev/ttyACM0 put libs/words.py /libs/words.py
ampy --port /dev/ttyACM0 put libs/leaderboard.py /libs/leaderboard.py

# Reset the badge to load new code
# (Use hardware reset button or send Ctrl+D via serial terminal)
```

**Note:** Your badge's serial port may be `/dev/ttyACM1` or `/dev/ttyUSB0` instead of `/dev/ttyACM0`. Check with `ls /dev/tty*` to find the correct port.

### Option B: Manual File Transfer

If you prefer to copy files manually or use alternative tools:

#### Step 1: Connect to Badge Filesystem

Use a tool that can access MicroPython filesystem:
- **mpremote** (recommended): `mpremote connect /dev/ttyACM0`
- **rshell**: `rshell --port /dev/ttyACM0`
- **Thonny IDE**: Connect to MicroPython device
- **Web REPL**: If enabled on badge

#### Step 2: Create Required Directories (if needed)

```python
# In REPL or file manager:
import os
# Check if /apps and /libs directories exist
os.listdir('/')
# They should already exist on the badge
```

#### Step 3: Copy Files to Badge

Copy these files from the `TyperRoyale_game/` directory:

| Source File | Destination on Badge | Description |
|-------------|---------------------|-------------|
| `typer_royale_app.py` | `/apps/userB.py` | Main game application |
| `libs/typer_game.py` | `/libs/typer_game.py` | Game engine |
| `libs/words.py` | `/libs/words.py` | Word lists |
| `libs/leaderboard.py` | `/libs/leaderboard.py` | Leaderboard management |

**Important:** The main app file must be renamed to `userB.py` when copied to the badge!

#### Step 4: Choose Your User App Slot

TyperRoyale can be installed to any of the four user app slots:
- `/apps/userA.py` - Accessible via F4 → F1
- `/apps/userB.py` - Accessible via F4 → F2 (recommended)
- `/apps/userC.py` - Accessible via F4 → F3
- `/apps/userD.py` - Accessible via F4 → F4

Just change the destination filename when copying!

#### Step 5: Reset Badge

After copying files, reset the badge:
- Press the hardware reset button, OR
- In REPL, press `Ctrl+D`, OR
- Power cycle the badge

## How to Play

### Accessing the Game

1. From the main menu, press **F4** (User Apps)
2. Press **F2** (User B) - or whichever slot you installed to
3. Welcome to TyperRoyale!

### Main Menu Controls

- **F1: Score Mode** - 60-second word sprint
- **F2: Time Trial** - Race through 20 words
- **F3: Survival** - Endless typing challenge
- **F4: Difficulty** - Cycle through Easy → Medium → Hard → Expert
- **F5: Exit** - Return to badge main menu

### Gameplay

1. **Select a mode and difficulty** from the main menu
2. **Type the displayed word** using the badge keyboard
   - Characters appear in real-time as you type
   - Correct characters shown in **green** (yellow highlight)
   - Wrong characters rejected with **red flash** (lose 1 life)
3. **Press Enter** to submit the completed word
4. **Use Backspace** to correct mistakes (no penalty)
5. Keep typing until:
   - **Score Mode:** 60 seconds expires
   - **Time Trial:** All 20 words completed
   - **Survival:** You run out of lives

### During Gameplay

- **Lives:** ❤️❤️❤️ displayed in top-left (3 lives, lose 1 per mistake)
- **Score:** Updated in real-time (top-right)
- **Streak:** Consecutive correct words (bonus points!)
- **Progress:** Words completed / total words
- **F5:** Quit back to main menu anytime

### Ranked Mode & Leaderboards

After completing a game:
1. **Results screen** shows your stats (score, accuracy, time)
2. **Top 5 Score?** You'll be prompted to enter your name!
   - Type **3 characters** for your initials (e.g., ABC, JOE, SAM)
   - Press **Enter** to save
3. **View Leaderboards:**
   - From results screen: Press **F2** to see rankings
   - Leaderboards are per mode/difficulty combination
   - Top 5 scores saved persistently

### Scoring System

**Base Points per Word:** 10 points

**Bonuses:**
- **Time Bonus:** Up to 50 bonus points for fast completion (faster = more points)
- **Accuracy Bonus:** +20 points if typed with zero mistakes
- **Streak Bonus:** +5 points per consecutive correct word (builds with streak)

**Example:** Type "badge" in 2 seconds with no mistakes on a 5-word streak:
- Base: 10
- Time Bonus: 48 (50 - 2)
- Accuracy: 20
- Streak: 25 (5 × 5)
- **Total: 103 points for one word!**

## Game Modes Explained

### Score Mode (60 seconds)
- Type as many words as possible before time runs out
- Random words from selected difficulty
- Goal: Maximize score with speed and accuracy
- **Perfect for:** Quick gameplay sessions

### Time Trial (20 words)
- Complete exactly 20 words as fast as possible
- Clock stops when you finish the 20th word
- Mistakes add time penalty
- **Perfect for:** Speed training

### Survival Mode (Endless)
- Keep typing until you run out of lives
- Words appear continuously at increasing difficulty
- Track your longest word streak
- **Perfect for:** Endurance challenges

## Difficulty Guide

| Difficulty | Word Length | Example Words | Timeout |
|-----------|-------------|---------------|---------|
| **Easy** | 3-5 letters | cat, hack, chip, led | 10s |
| **Medium** | 4-8 letters | python, circuit, wireless | 7s |
| **Hard** | 6-12 letters | microcontroller, encryption | 5s |
| **Expert** | 2-5 word phrases | hello world, software defined radio | 15s |

**Tip:** Start with Easy/Medium to learn the mechanics, then challenge yourself with Hard/Expert!

## Tips & Strategies

1. **Focus on accuracy first** - Each mistake costs a life and resets your streak
2. **Build your streak** - Consecutive correct words multiply your score
3. **Use backspace liberally** - Better to correct than submit wrong
4. **Watch the word carefully** - Real-time validation shows if you're on track
5. **Practice common words** - Conference terms appear frequently (badge, hack, circuit)
6. **Expert mode tip** - Phrases require spaces, so type naturally!

## Technical Details

### Dependencies
- Standard badge libraries (included in firmware):
  - `apps.base_app` - BaseApp class
  - `ui.page` - Page layout system
  - `lvgl` - Display rendering
  - `uasyncio` - Async event loop
- No external dependencies required!

### File Structure
```
TyperRoyale_game/
├── typer_royale_app.py       # Main game app (739 lines)
├── libs/
│   ├── typer_game.py         # Game engine (213 lines)
│   ├── words.py              # Word lists (119 lines)
│   └── leaderboard.py        # Leaderboard system (96 lines)
└── README.md                 # This file!
```

### Leaderboard Storage
Leaderboards are stored in badge configuration using keys:
- Format: `typer_lb_{mode}_{difficulty}`
- Example: `typer_lb_score_medium`
- Total: 45 unique leaderboards (3 modes × 4 difficulties × top 5 + global)
- Persists across badge reboots

### Performance
- **Foreground refresh:** 50ms (responsive typing)
- **Background sleep:** 1000ms (when not active)
- **Memory usage:** ~30KB total
- **No lag** during normal gameplay

## Troubleshooting

### "Module not found" errors
- Ensure all library files are in `/libs/` directory on badge
- Check that imports match: `from libs.typer_game import TyperGame`

### Game doesn't appear in User menu
- Verify main app is installed to `/apps/userB.py` (or userA/C/D)
- Try resetting the badge after installation

### Leaderboards not saving
- Badge must have writable config storage
- Check available storage with `import os; os.statvfs('/')`

### Keyboard input not working
- Some keys may require Shift modifier
- Try lowercase letters first
- Check badge keyboard is functioning in other apps

### Screen glitches
- Reset badge to clear LVGL display state
- Ensure no other apps are running in foreground

## Future Plans

### Phase 2: Multiplayer Mode (Coming Soon!)
- **LoRa mesh networking** for multiplayer battles
- **Lobby system** - Create/join games over radio
- **Battle Royale elimination** - Last typer standing wins!
- **2-8 players** per game
- **Round-based gameplay** - Slowest player eliminated each round
- **Spectator mode** - Watch remaining players after elimination

Multiplayer protocol will use **Port 50** on BadgeNet for game coordination.

### Potential Enhancements
- Custom word lists
- Daily challenges
- Team vs team mode
- Power-ups (freeze opponent, extra time)
- Tournament brackets
- Audio feedback (beeps)

## Credits

**Game Design & Development:** ElectroNick https://electronick.co done with distiller alpha by https://pamir.ai and Claude Code
**Platform:** Hackaday SuperCon 2025 Badge
**Firmware:** ESP32-S3 MicroPython
**Conference:** Hackaday SuperCon 2025, Pasadena, CA

---

**Have fun typing! May your WPM be high and your errors low! ⌨️🏆**
