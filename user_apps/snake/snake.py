"""Snake game for the badge."""

import lvgl
import random
import time
from apps.base_app import BaseApp
from ui import styles
from hardware.keyboard import Keyboard


class SnakeApp(BaseApp):
    """Classic Snake game using arrow keys."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 100  # Game speed (100ms = ~10 FPS)

        # Game grid settings (using larger blocks for visibility)
        self.block_size = 8  # 8x8 pixel blocks
        self.grid_width = 53  # 428 / 8 = 53.5
        self.grid_height = 17  # 142 / 8 = 17.75

        # Game state
        self.reset_game()

    def reset_game(self):
        """Initialize/reset the game state."""
        # Clean up old LVGL objects first
        if hasattr(self, 'snake_blocks'):
            for block in self.snake_blocks:
                if block:
                    block.delete()
        if hasattr(self, 'food_block') and self.food_block:
            self.food_block.delete()
        if hasattr(self, 'game_over_label') and self.game_over_label:
            self.game_over_label.delete()

        # Snake starts in the middle, moving right
        start_x = self.grid_width // 2
        start_y = self.grid_height // 2
        self.snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = (1, 0)  # (dx, dy) - moving right
        self.next_direction = (1, 0)  # Buffer for direction changes

        # Food
        self.food = None
        self.spawn_food()

        # Game state
        self.score = 0
        self.game_over = False
        self.last_update = 0

        # LVGL objects (will be created in switch_to_foreground)
        self.snake_blocks = []
        self.food_block = None
        self.score_label = None
        self.game_over_label = None

    def spawn_food(self):
        """Spawn food at a random location not occupied by snake."""
        while True:
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break

    def switch_to_foreground(self):
        """Set up the game screen."""
        super().switch_to_foreground()
        self.badge.display.clear()

        # Set up function key labels
        self.badge.display.f1("Restart", styles.hackaday_yellow)
        self.badge.display.f5("Exit", styles.hackaday_yellow)

        # Create score label
        self.score_label = lvgl.label(self.badge.display.screen)
        self.score_label.set_text(f"Score: {self.score}")
        self.score_label.set_style_text_color(styles.hackaday_yellow, 0)
        self.score_label.align(lvgl.ALIGN.TOP_CENTER, 0, 2)

        # Draw initial game state
        self.draw_game()

    def draw_game(self):
        """Draw the snake and food on the screen."""
        # Clear old snake blocks
        for block in self.snake_blocks:
            if block:
                block.delete()
        self.snake_blocks = []

        # Draw snake
        for i, (x, y) in enumerate(self.snake):
            block = lvgl.obj(self.badge.display.screen)
            block.set_size(self.block_size, self.block_size)
            block.set_pos(x * self.block_size, y * self.block_size + 20)  # +20 for score label

            # Head is brighter
            if i == 0:
                block.set_style_bg_color(lvgl.color_hex(0x00FF00), 0)  # Bright green head
            else:
                block.set_style_bg_color(lvgl.color_hex(0x00AA00), 0)  # Darker green body
            block.set_style_border_width(0, 0)
            self.snake_blocks.append(block)

        # Draw food
        if self.food_block:
            self.food_block.delete()

        self.food_block = lvgl.obj(self.badge.display.screen)
        self.food_block.set_size(self.block_size, self.block_size)
        self.food_block.set_pos(
            self.food[0] * self.block_size,
            self.food[1] * self.block_size + 20
        )
        self.food_block.set_style_bg_color(lvgl.color_hex(0xFF0000), 0)  # Red food
        self.food_block.set_style_border_width(0, 0)

    def run_foreground(self):
        """Main game loop."""
        # Check for restart
        if self.badge.keyboard.f1():
            self.reset_game()
            self.draw_game()
            if self.score_label:
                self.score_label.set_text(f"Score: {self.score}")
            return

        # Check for exit
        if self.badge.keyboard.f5():
            self.badge.display.clear()
            self.switch_to_background()
            return

        # Don't update if game is over
        if self.game_over:
            return

        # Read arrow keys for direction changes
        key = self.badge.keyboard.read_key()
        if key == Keyboard.UP and self.direction != (0, 1):  # Can't go opposite direction
            self.next_direction = (0, -1)
        elif key == Keyboard.DOWN and self.direction != (0, -1):
            self.next_direction = (0, 1)
        elif key == Keyboard.LEFT and self.direction != (1, 0):
            self.next_direction = (-1, 0)
        elif key == Keyboard.RIGHT and self.direction != (-1, 0):
            self.next_direction = (1, 0)

        # Update snake position
        self.direction = self.next_direction  # Apply buffered direction change
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        # Check for collisions
        if (new_head[0] < 0 or new_head[0] >= self.grid_width or
            new_head[1] < 0 or new_head[1] >= self.grid_height or
            new_head in self.snake):
            # Game over!
            self.game_over = True
            if not self.game_over_label:
                self.game_over_label = lvgl.label(self.badge.display.screen)
                self.game_over_label.set_text("GAME OVER!")
                self.game_over_label.set_style_text_color(lvgl.color_hex(0xFF0000), 0)
                self.game_over_label.set_style_text_font(lvgl.font_montserrat_16, 0)
                self.game_over_label.align(lvgl.ALIGN.CENTER, 0, -10)
            return

        # Move snake
        self.snake.insert(0, new_head)

        # Check if food was eaten
        if new_head == self.food:
            self.score += 1
            if self.score_label:
                self.score_label.set_text(f"Score: {self.score}")
            self.spawn_food()
        else:
            # Remove tail if no food eaten
            self.snake.pop()

        # Redraw game
        self.draw_game()

    def switch_to_background(self):
        """Clean up when going to background."""
        super().switch_to_background()
        # Clean up LVGL objects
        for block in self.snake_blocks:
            if block:
                block.delete()
        self.snake_blocks = []
        if self.food_block:
            self.food_block.delete()
            self.food_block = None
        if self.score_label:
            self.score_label.delete()
            self.score_label = None
        if self.game_over_label:
            self.game_over_label.delete()
            self.game_over_label = None
