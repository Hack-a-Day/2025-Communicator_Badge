# Snake Game

Classic Snake game for the Supercon 2025 badge.

## Controls

- **Arrow Keys**: Change snake direction (up, down, left, right)
- **F1**: Restart game
- **F5**: Exit to menu

## How to Play

Guide the snake to eat the red food blocks. Each food eaten makes the snake grow longer and increases your score. Avoid hitting the walls or your own tail, or it's game over!

## Technical Details

- **Grid**: 53×17 blocks (8×8 pixels each)
- **Update Rate**: ~10 FPS (100ms per frame)
- **Display**: Uses LVGL objects for snake segments and food
- **Movement**: Direction changes are buffered to prevent reverse-direction bugs

The game uses a simple collision detection system and maintains the snake as a list of coordinate tuples. Food spawns randomly at positions not occupied by the snake body.
