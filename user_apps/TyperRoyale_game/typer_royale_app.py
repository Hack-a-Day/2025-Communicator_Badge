"""TyperRoyale - Typing Battle Royale Game
Single player mode with future multiplayer support
"""

import uasyncio as aio
import time

from apps.base_app import BaseApp
from ui.page import Page
import ui.styles as styles
import lvgl

# Future multiplayer protocol (port 50)
# TYPER_PROTOCOL = Protocol(port=50, name="TYPER", structdef="!BBfB")


class App(BaseApp):
    """TyperRoyale typing game app"""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 50  # Responsive typing

        # Game state machine
        self.state = "main_menu"  # main_menu, difficulty_select, playing, results, name_entry, leaderboard
        self.game = None

        # Game settings
        self.mode = "score"  # score, time, survival
        self.difficulty = "medium"  # easy, medium, hard, expert
        self.is_ranked = False  # Ranked mode flag

        # UI elements (created in switch_to_foreground)
        self.p = None
        self.target_label = None
        self.input_label = None
        self.stats_label = None
        self.progress_label = None
        self.infobar_left_label = None  # For lives display
        self.infobar_right_label = None  # For score/time

        # Visual feedback state
        self.error_flash_counter = 0  # Counts down when showing error

        # Name entry state (for ranked mode)
        self.player_name = ""  # Up to 12 characters

        # Multiplayer state (for future use)
        self.is_multiplayer = False
        self.lobby_id = None

    def start(self):
        """Register app with system"""
        super().start()
        # Future: register_receiver(TYPER_PROTOCOL, self.on_network_message)

    def run_foreground(self):
        """Main game loop - route to appropriate handler"""
        if self.state == "main_menu":
            self._handle_main_menu()
        elif self.state == "difficulty_select":
            self._handle_difficulty_select()
        elif self.state == "playing":
            self._handle_playing()
        elif self.state == "results":
            self._handle_results()
        elif self.state == "name_entry":
            self._handle_name_entry()
        elif self.state == "leaderboard":
            self._handle_leaderboard()
        # Future states: multiplayer_menu, lobby, multiplayer_playing

    def run_background(self):
        """Background behavior"""
        super().run_background()
        # Future: listen for multiplayer lobby broadcasts

    # ==================== Main Menu ====================

    def _handle_main_menu(self):
        """Main menu input handling"""
        if self.badge.keyboard.f1():
            # Single player (unranked)
            self.is_ranked = False
            self.is_multiplayer = False
            self.state = "difficulty_select"
            self.switch_to_foreground()
        elif self.badge.keyboard.f2():
            # Ranked mode
            self.is_ranked = True
            self.is_multiplayer = False
            self.state = "difficulty_select"
            self.switch_to_foreground()
        elif self.badge.keyboard.f3():
            # View leaderboards
            self.state = "leaderboard"
            self.switch_to_foreground()
        elif self.badge.keyboard.f4():
            # Future: Multiplayer (not implemented yet)
            self._show_not_implemented("Multiplayer coming soon!")
        elif self.badge.keyboard.f5():
            # Exit
            self.badge.display.clear()
            self.switch_to_background()

    def _show_main_menu(self):
        """Display main menu screen"""
        p = Page()
        p.create_infobar(["TyperRoyale", "v1.0"])
        p.create_content()

        # Title
        title = lvgl.label(p.content)
        title.set_text("TYPER ROYALE")
        title.set_style_text_font(lvgl.font_montserrat_16, 0)
        title.set_style_text_color(styles.hackaday_yellow, 0)
        title.align(lvgl.ALIGN.TOP_MID, 0, 5)

        # Menu options
        menu_text = lvgl.label(p.content)
        menu_text.set_text(
            "F1: Single Player\n"
            "F2: Ranked Mode\n"
            "F3: Leaderboards\n"
            "F4: Multiplayer (soon)\n"
            "F5: Exit"
        )
        menu_text.set_style_text_font(lvgl.font_montserrat_12, 0)
        menu_text.align(lvgl.ALIGN.CENTER, 0, 0)

        p.create_menubar(["Solo", "Ranked", "Scores", "Multi", "Exit"])
        p.replace_screen()
        self.p = p

    # ==================== Difficulty Selection ====================

    def _handle_difficulty_select(self):
        """Difficulty and mode selection"""
        if self.badge.keyboard.f1():
            self.mode = "score"
            self._start_game()
        elif self.badge.keyboard.f2():
            self.mode = "time"
            self._start_game()
        elif self.badge.keyboard.f3():
            self.mode = "survival"
            self._start_game()
        elif self.badge.keyboard.f4():
            self._cycle_difficulty()
        elif self.badge.keyboard.f5():
            # Back to main menu
            self.state = "main_menu"
            self.switch_to_foreground()

    def _show_difficulty_select(self):
        """Display difficulty and mode selection"""
        p = Page()
        # Capitalize first letter manually (MicroPython doesn't have .title())
        diff_display = self.difficulty[0].upper() + self.difficulty[1:]
        p.create_infobar(["Select Mode", f"Difficulty: {diff_display}"])
        p.create_content()

        # Mode descriptions
        mode_text = lvgl.label(p.content)

        if self.difficulty == "easy":
            diff_desc = "3-5 letter words"
        elif self.difficulty == "medium":
            diff_desc = "4-8 letter tech words"
        elif self.difficulty == "hard":
            diff_desc = "6-12 letter technical"
        else:  # expert
            diff_desc = "Multi-word phrases"

        mode_text.set_text(
            f"Current: {diff_desc}\n\n"
            "F1: Score Mode (60 seconds)\n"
            "F2: Time Trial (20 words)\n"
            "F3: Survival (endless)\n"
            "F4: Change Difficulty\n"
            "F5: Back"
        )
        mode_text.set_style_text_font(lvgl.font_montserrat_12, 0)
        mode_text.align(lvgl.ALIGN.TOP_LEFT, 10, 5)

        p.create_menubar(["Score", "Time", "Survive", "Diff", "Back"])
        p.replace_screen()
        self.p = p

    def _cycle_difficulty(self):
        """Cycle through difficulty levels"""
        difficulties = ['easy', 'medium', 'hard', 'expert']
        current_idx = difficulties.index(self.difficulty)
        self.difficulty = difficulties[(current_idx + 1) % len(difficulties)]
        self.switch_to_foreground()  # Refresh screen

    # ==================== Game Playing ====================

    def _start_game(self):
        """Initialize and start the game"""
        from libs.typer_game import TyperGame

        self.game = TyperGame(mode=self.mode, difficulty=self.difficulty)
        self.game.start_game()
        self.state = "playing"
        self.switch_to_foreground()

    def _handle_playing(self):
        """Handle typing input during gameplay"""
        try:
            # Check for quit (always allow)
            if self.badge.keyboard.f5():
                self.state = "main_menu"
                self.game = None
                self.switch_to_foreground()
                return

            # Check game over conditions first
            if self.game.is_game_over():
                print("Game over detected, ending game")
                self._end_game()
                return

            # Block input during error flash
            if self.error_flash_counter > 0:
                # Still consume keystrokes but ignore them
                self.badge.keyboard.read_key()
                # Update display to continue flash animation
                self._update_game_display()
                return

            # Read keyboard input
            key = self.badge.keyboard.read_key()
            if key:
                result = None

                if key == '\x08' or key == '\x7f':  # Backspace
                    result = self.game.process_backspace()
                    print(f"Backspace, input: '{self.game.user_input}'")

                elif key == '\r' or key == '\n':  # Enter
                    result = self.game.process_enter()
                    print(f"Enter result: {result}")

                    if result == 'complete':
                        # Word completed successfully
                        pass
                    elif result == 'incomplete':
                        # Word not finished yet
                        pass
                    elif result == 'game_over':
                        self._end_game()
                        return

                elif len(key) == 1:  # Single character
                    char = key.lower()

                    # Handle space for expert mode (phrases)
                    if char == ' ' or (char >= 'a' and char <= 'z'):
                        result = self.game.process_char(char)
                        print(f"Char '{char}' result: {result}, lives: {self.game.lives}, input: '{self.game.user_input}'")

                        if result == 'wrong':
                            # Wrong character - flash red for 450ms total (250ms longer than before)
                            self.error_flash_counter = 9  # Flash for ~450ms (9 * 50ms)

                            # Check if game over
                            if self.game.lives <= 0:
                                print("Lives = 0, ending game")
                                self._end_game()
                                return

            # Update display
            self._update_game_display()

        except Exception as e:
            print(f"Error in _handle_playing: {e}")
            import sys
            sys.print_exception(e)

    def _show_game_screen(self):
        """Display the game playing screen"""
        if not self.game:
            return

        p = Page()

        stats = self.game.get_stats()

        # Infobar with lives and score - use simple text instead of hearts
        lives_str = f"Lives: {self.game.lives}/3"

        if self.mode == 'score':
            right_info = f"Time: {stats['time_remaining']:.0f}s"
        else:
            right_info = f"Score: {stats['score']}"

        p.create_infobar([lives_str, right_info])

        # Store references to infobar labels for updating
        self.infobar_left_label = p.infobar_left
        self.infobar_right_label = p.infobar_right

        p.create_content()

        # Target word (what to type)
        target_label = lvgl.label(p.content)
        target_label.set_text(self.game.current_word)

        # Use available fonts only (12, 14, 16)
        word_len = len(self.game.current_word)
        if word_len <= 8:
            target_label.set_style_text_font(lvgl.font_montserrat_16, 0)
        elif word_len <= 15:
            target_label.set_style_text_font(lvgl.font_montserrat_14, 0)
        else:
            target_label.set_style_text_font(lvgl.font_montserrat_12, 0)

        target_label.set_style_text_color(styles.hackaday_yellow, 0)
        target_label.align(lvgl.ALIGN.TOP_MID, 0, 5)
        self.target_label = target_label

        # User input (what they've typed)
        input_label = lvgl.label(p.content)
        input_str = self.game.user_input
        # Show remaining characters as underscores
        remaining = len(self.game.current_word) - len(input_str)
        input_str += "_" * remaining
        input_label.set_text(input_str)

        if word_len <= 8:
            input_label.set_style_text_font(lvgl.font_montserrat_14, 0)
        elif word_len <= 15:
            input_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        else:
            input_label.set_style_text_font(lvgl.font_montserrat_12, 0)

        input_label.set_style_text_color(styles.lcd_color_fg, 0)
        input_label.align(lvgl.ALIGN.TOP_MID, 0, 40)
        self.input_label = input_label

        # Progress indicator
        progress_label = lvgl.label(p.content)
        progress_text = self.game.get_progress()

        if self.mode == 'score':
            progress_label.set_text(f"Words: {progress_text}  Streak: {stats['streak']}")
        elif self.mode == 'time':
            progress_label.set_text(f"Progress: {progress_text}  Streak: {stats['streak']}")
        else:  # survival
            progress_label.set_text(f"Words: {progress_text}  Best: {stats['best_streak']}")

        progress_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        progress_label.align(lvgl.ALIGN.BOTTOM_LEFT, 10, -5)
        self.progress_label = progress_label

        # Stats (time/score)
        stats_label = lvgl.label(p.content)
        if self.mode == 'score':
            stats_label.set_text(f"Score: {stats['score']}")
        else:
            stats_label.set_text(f"Time: {stats['time']:.1f}s")
        stats_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        stats_label.align(lvgl.ALIGN.BOTTOM_RIGHT, -10, -5)
        self.stats_label = stats_label

        p.create_menubar(["", "", "", "", "Quit"])
        p.replace_screen()
        self.p = p

    def _update_game_display(self):
        """Update game screen with current state"""
        try:
            if not self.game or not self.p:
                return

            stats = self.game.get_stats()

            # Flash entire screen red on error
            if self.error_flash_counter > 0:
                # Red background flash - very visible!
                red_color = lvgl.color_make(255, 0, 0)
                if self.p and hasattr(self.p, 'content'):
                    self.p.content.set_style_bg_color(red_color, 0)
                    self.p.content.set_style_bg_opa(255, 0)  # Full opacity
                self.error_flash_counter -= 1
            else:
                # Normal background
                if self.p and hasattr(self.p, 'content'):
                    self.p.content.set_style_bg_color(styles.lcd_color_bg, 0)
                    self.p.content.set_style_bg_opa(255, 0)

            # Update infobar (lives and score/time)
            if self.infobar_left_label:
                lives_str = f"Lives: {self.game.lives}/3"
                self.infobar_left_label.set_text(lives_str)
                # Force refresh
                self.infobar_left_label.invalidate()

            if self.infobar_right_label:
                if self.mode == 'score':
                    time_str = f"Time: {stats['time_remaining']:.0f}s"
                    self.infobar_right_label.set_text(time_str)
                    self.infobar_right_label.invalidate()
                else:
                    score_str = f"Score: {stats['score']}"
                    self.infobar_right_label.set_text(score_str)
                    self.infobar_right_label.invalidate()

            # Update target word
            if self.target_label:
                self.target_label.set_text(self.game.current_word)

            # Update user input
            if self.input_label:
                input_str = self.game.user_input
                remaining = len(self.game.current_word) - len(input_str)
                input_str += "_" * remaining
                self.input_label.set_text(input_str)

            # Update progress
            if self.progress_label:
                progress_text = self.game.get_progress()

                if self.mode == 'score':
                    self.progress_label.set_text(f"Words: {progress_text}  Streak: {stats['streak']}")
                elif self.mode == 'time':
                    self.progress_label.set_text(f"Progress: {progress_text}  Streak: {stats['streak']}")
                else:  # survival
                    self.progress_label.set_text(f"Words: {progress_text}  Best: {stats['best_streak']}")

            # Update stats
            if self.stats_label:
                if self.mode == 'score':
                    self.stats_label.set_text(f"Score: {stats['score']}")
                else:
                    self.stats_label.set_text(f"Time: {stats['time']:.1f}s")

        except Exception as e:
            print(f"Error updating display: {e}")
            import sys
            sys.print_exception(e)

    def _end_game(self):
        """End game and transition to results"""
        if self.is_ranked and self.game:
            # Check if score qualifies for leaderboard
            from libs.leaderboard import qualifies_for_leaderboard
            stats = self.game.get_stats()

            # Get score based on mode
            if self.mode == "time":
                score = stats['time']  # Lower is better
            elif self.mode == "survival":
                score = stats['words']  # Higher is better
            else:  # score mode
                score = stats['score']  # Higher is better

            if qualifies_for_leaderboard(self.badge, self.mode, self.difficulty, score):
                # Qualified! Go to name entry
                self.state = "name_entry"
                self.switch_to_foreground()
                return

        # Not ranked or didn't qualify - go to results
        self.state = "results"
        self.switch_to_foreground()

    # ==================== Results Screen ====================

    def _handle_results(self):
        """Results screen input"""
        if self.badge.keyboard.f1():
            # Play again with same settings
            self._start_game()
        elif self.badge.keyboard.f2():
            # Change mode/difficulty
            self.state = "difficulty_select"
            self.switch_to_foreground()
        elif self.badge.keyboard.f5():
            # Back to main menu
            self.state = "main_menu"
            self.game = None
            self.switch_to_foreground()

    def _show_results(self):
        """Display game results"""
        if not self.game:
            return

        stats = self.game.get_stats()

        p = Page()
        # Capitalize first letter manually (MicroPython doesn't have .title())
        mode_display = self.mode[0].upper() + self.mode[1:]
        p.create_infobar(["Game Over!", f"{mode_display} Mode"])
        p.create_content()

        # Results text - more compact layout
        results_label = lvgl.label(p.content)

        # Shorter, more compact results display
        results_text = (
            f"Score: {stats['score']}  Acc: {stats['accuracy']:.0f}%\n"
            f"Time: {stats['time']:.1f}s  Words: {stats['words']}\n"
            f"Mistakes: {stats['mistakes']}\n"
            f"Best Streak: {stats['best_streak']}"
        )

        results_label.set_text(results_text)
        results_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        results_label.align(lvgl.ALIGN.TOP_LEFT, 10, 10)

        p.create_menubar(["Again", "Change", "", "", "Menu"])
        p.replace_screen()
        self.p = p

    # ==================== Screen Management ====================

    def switch_to_foreground(self):
        """Transition to foreground - show appropriate screen"""
        super().switch_to_foreground()

        if self.state == "main_menu":
            self._show_main_menu()
        elif self.state == "difficulty_select":
            self._show_difficulty_select()
        elif self.state == "playing":
            self._show_game_screen()
        elif self.state == "results":
            self._show_results()
        elif self.state == "name_entry":
            self._show_name_entry()
        elif self.state == "leaderboard":
            self._show_leaderboard()

    def switch_to_background(self):
        """Transition to background"""
        self.p = None
        self.target_label = None
        self.input_label = None
        self.stats_label = None
        self.progress_label = None
        super().switch_to_background()

    # ==================== Name Entry (Ranked Mode) ====================

    def _handle_name_entry(self):
        """Handle name entry for high score"""
        # F1 or Enter to confirm
        if self.badge.keyboard.f1():
            if len(self.player_name) > 0:  # Must have at least 1 character
                self._save_high_score()
            return

        # Read keyboard input
        key = self.badge.keyboard.read_key()
        if key:
            if key == '\x08' or key == '\x7f':  # Backspace
                if len(self.player_name) > 0:
                    self.player_name = self.player_name[:-1]
                    self._update_name_entry_display()

            elif key == '\r' or key == '\n':  # Enter
                if len(self.player_name) > 0:
                    self._save_high_score()

            elif len(key) == 1 and len(self.player_name) < 12:  # Regular character
                char = key.upper()  # Force uppercase
                # Only accept letters, numbers, and spaces
                if char.isalpha() or char.isdigit() or char == ' ':
                    self.player_name += char
                    self._update_name_entry_display()

    def _show_name_entry(self):
        """Display name entry screen"""
        # Reset name for new entry
        self.player_name = ""

        p = Page()
        p.create_infobar(["HIGH SCORE!", "Enter Your Name"])
        p.create_content()

        # Congratulations message
        congrats = lvgl.label(p.content)
        congrats.set_text("You made the leaderboard!")
        congrats.set_style_text_font(lvgl.font_montserrat_14, 0)
        congrats.set_style_text_color(styles.hackaday_yellow, 0)
        congrats.align(lvgl.ALIGN.TOP_MID, 0, 10)

        # Name display (centered)
        self.name_label = lvgl.label(p.content)
        self.name_label.set_text("_")  # Show cursor
        self.name_label.set_style_text_font(lvgl.font_montserrat_16, 0)
        self.name_label.align(lvgl.ALIGN.CENTER, 0, 5)

        # Instructions (compact)
        instructions = lvgl.label(p.content)
        instructions.set_text("F1: Confirm")
        instructions.set_style_text_font(lvgl.font_montserrat_12, 0)
        instructions.align(lvgl.ALIGN.BOTTOM_MID, 0, -5)

        p.create_menubar(["Done", "", "", "", ""])
        p.replace_screen()
        self.p = p

    def _update_name_entry_display(self):
        """Update the name display"""
        if not hasattr(self, 'name_label') or not self.name_label:
            return

        # Show name with cursor
        if len(self.player_name) > 0:
            display_str = self.player_name + "_"
        else:
            display_str = "_"

        self.name_label.set_text(display_str)

    def _save_high_score(self):
        """Save the high score to leaderboard"""
        from libs.leaderboard import add_score

        stats = self.game.get_stats()

        # Get score and metric based on mode
        if self.mode == "time":
            score = stats['time']
            metric = f"{stats['time']:.1f}s"
        elif self.mode == "survival":
            score = stats['words']
            metric = f"{stats['words']} words"
        else:  # score mode
            score = stats['score']
            metric = f"{stats['score']} pts"

        # Save to leaderboard
        rank, total = add_score(self.badge, self.mode, self.difficulty,
                                self.player_name.strip(), score, metric)

        # Go to results (which will show the leaderboard)
        self.state = "results"
        self.switch_to_foreground()

    # ==================== Leaderboard Display ====================

    def _handle_leaderboard(self):
        """Handle leaderboard viewing"""
        # Cycle through modes
        if self.badge.keyboard.f1():
            self.mode = "score"
            self.switch_to_foreground()
        elif self.badge.keyboard.f2():
            self.mode = "time"
            self.switch_to_foreground()
        elif self.badge.keyboard.f3():
            self.mode = "survival"
            self.switch_to_foreground()
        # Cycle through difficulties
        elif self.badge.keyboard.f4():
            difficulties = ['easy', 'medium', 'hard', 'expert']
            current_idx = difficulties.index(self.difficulty)
            self.difficulty = difficulties[(current_idx + 1) % len(difficulties)]
            self.switch_to_foreground()
        elif self.badge.keyboard.f5():
            self.state = "main_menu"
            self.switch_to_foreground()

    def _show_leaderboard(self):
        """Display leaderboard screen"""
        from libs.leaderboard import get_leaderboard

        # Get leaderboard for current mode/difficulty
        leaderboard = get_leaderboard(self.badge, self.mode, self.difficulty)

        # Capitalize first letter of mode and difficulty
        mode_display = self.mode[0].upper() + self.mode[1:]
        diff_display = self.difficulty[0].upper() + self.difficulty[1:]

        p = Page()
        p.create_infobar([f"{mode_display} - {diff_display}", "Top 5"])
        p.create_content()

        # Title
        title = lvgl.label(p.content)
        title.set_text("LEADERBOARD")
        title.set_style_text_font(lvgl.font_montserrat_14, 0)
        title.set_style_text_color(styles.hackaday_yellow, 0)
        title.align(lvgl.ALIGN.TOP_MID, 0, 2)

        # Leaderboard entries
        if len(leaderboard) == 0:
            # No scores yet
            empty_msg = lvgl.label(p.content)
            empty_msg.set_text("No scores yet!\n\nPlay Ranked mode to\nset the first record.")
            empty_msg.set_style_text_font(lvgl.font_montserrat_12, 0)
            empty_msg.align(lvgl.ALIGN.CENTER, 0, 5)
        else:
            # Show top 5 scores
            leaderboard_text = ""
            for i, entry in enumerate(leaderboard):
                rank = i + 1
                name = entry["name"]
                metric = entry["metric"]
                leaderboard_text += f"{rank}. {name:12s} {metric}\n"

            scores_label = lvgl.label(p.content)
            scores_label.set_text(leaderboard_text.strip())
            scores_label.set_style_text_font(lvgl.font_montserrat_12, 0)
            scores_label.align(lvgl.ALIGN.TOP_LEFT, 10, 20)

        p.create_menubar(["Score", "Time", "Survive", "Diff", "Back"])
        p.replace_screen()
        self.p = p

    # ==================== Utility Functions ====================

    def _show_not_implemented(self, message):
        """Show 'not implemented' message"""
        # For now, just ignore - could add a popup later
        pass

    # ==================== Future Multiplayer Methods ====================

    # def on_network_message(self, message: NetworkFrame):
    #     """Handle incoming multiplayer messages"""
    #     pass
    #
    # def _show_multiplayer_menu(self):
    #     """Show multiplayer lobby browser"""
    #     pass
    #
    # def _create_lobby(self):
    #     """Create multiplayer lobby as host"""
    #     pass
    #
    # def _join_lobby(self, lobby_id):
    #     """Join existing lobby as player"""
    #     pass
