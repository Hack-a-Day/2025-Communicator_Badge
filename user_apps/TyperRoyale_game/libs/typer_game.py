"""TyperRoyale game state manager"""

import time

class TyperGame:
    """Manages single-player TyperRoyale game state"""

    def __init__(self, mode='score', difficulty='medium'):
        """
        Initialize game

        Args:
            mode: 'score' (60s timed), 'time' (20 words), or 'survival' (endless)
            difficulty: 'easy', 'medium', 'hard', or 'expert'
        """
        self.mode = mode
        self.difficulty = difficulty

        # Game state
        self.lives = 3
        self.score = 0
        self.words_typed = 0
        self.mistakes = 0
        self.streak = 0
        self.best_streak = 0

        # Timing
        self.start_time = None
        self.word_start_time = None
        self.total_time = 0

        # Current word tracking
        self.current_word = ""
        self.user_input = ""
        self.words = []
        self.word_index = 0

    def start_game(self):
        """Initialize and start the game"""
        from libs.words import get_words

        # Determine word count based on mode
        if self.mode == 'score':
            word_count = 100  # More than enough for 60s
        elif self.mode == 'time':
            word_count = 20
        elif self.mode == 'survival':
            word_count = 100  # Will keep adding more
        else:
            word_count = 20

        self.words = get_words(self.difficulty, word_count)
        self.word_index = 0
        self.start_time = time.time()
        self.next_word()

    def next_word(self):
        """Load next word"""
        if self.word_index < len(self.words):
            self.current_word = self.words[self.word_index]
            self.user_input = ""
            self.word_start_time = time.time()
            self.word_index += 1
            return True
        else:
            # For survival mode, get more words
            if self.mode == 'survival':
                from libs.words import get_random_word
                self.current_word = get_random_word(self.difficulty)
                self.user_input = ""
                self.word_start_time = time.time()
                return True
            return False

    def process_char(self, char):
        """
        Process a single character input

        Args:
            char: character to add to input

        Returns:
            'correct' if char matches expected, 'wrong' if mistake, 'typing' otherwise
        """
        self.user_input += char

        # Check if input still matches the target word
        if self.current_word.startswith(self.user_input):
            return 'correct'
        else:
            # Wrong character - remove it and record mistake
            self.user_input = self.user_input[:-1]
            self.mistakes += 1
            self.lives -= 1
            self.streak = 0
            return 'wrong'

    def process_backspace(self):
        """Remove last character"""
        if len(self.user_input) > 0:
            self.user_input = self.user_input[:-1]
        return 'backspace'

    def process_enter(self):
        """
        Submit current word

        Returns:
            'complete' if word correct and complete
            'incomplete' if word not finished
            'game_over' if game should end
        """
        # Check if word is complete and correct
        if self.user_input == self.current_word:
            # Correct word!
            word_time = time.time() - self.word_start_time
            self.words_typed += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)

            # Calculate score
            base_score = 10
            time_bonus = max(0, int(50 - word_time))  # Up to 50 bonus points for speed
            accuracy_bonus = 20  # No mistakes on this word
            streak_bonus = min(self.streak * 5, 50)  # Cap at 50 bonus

            word_score = base_score + time_bonus + accuracy_bonus + streak_bonus
            self.score += word_score

            # Check if game should continue
            if self.is_game_over():
                return 'game_over'

            # Load next word
            if self.next_word():
                return 'complete'
            else:
                return 'game_over'
        else:
            # Word not complete yet
            return 'incomplete'

    def is_game_over(self):
        """Check if game should end"""
        # Check lives
        if self.lives <= 0:
            return True

        # Check mode-specific conditions
        if self.mode == 'score':
            # 60 second time limit
            elapsed = time.time() - self.start_time
            return elapsed >= 60.0
        elif self.mode == 'time':
            # All words typed
            return self.word_index >= len(self.words) and not self.current_word
        elif self.mode == 'survival':
            # Only lives matter
            return False

        return False

    def get_elapsed_time(self):
        """Get elapsed game time in seconds"""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    def get_word_time(self):
        """Get time spent on current word"""
        if self.word_start_time:
            return time.time() - self.word_start_time
        return 0.0

    def get_time_remaining(self):
        """Get time remaining (for score mode)"""
        if self.mode == 'score' and self.start_time:
            elapsed = time.time() - self.start_time
            return max(0.0, 60.0 - elapsed)
        return 0.0

    def get_accuracy(self):
        """Calculate accuracy percentage"""
        total_attempts = self.words_typed + self.mistakes
        if total_attempts == 0:
            return 100.0
        return (self.words_typed / total_attempts) * 100.0

    def get_stats(self):
        """Get complete game statistics"""
        return {
            'score': self.score,
            'time': self.get_elapsed_time(),
            'time_remaining': self.get_time_remaining(),
            'words': self.words_typed,
            'mistakes': self.mistakes,
            'accuracy': self.get_accuracy(),
            'streak': self.streak,
            'best_streak': self.best_streak,
            'lives': self.lives,
            'mode': self.mode,
            'difficulty': self.difficulty
        }

    def get_progress(self):
        """Get progress through word list (for time/survival mode)"""
        if self.mode == 'time':
            total = len(self.words)
            return f"{self.words_typed}/{total}"
        elif self.mode == 'survival':
            return f"{self.words_typed}"
        else:
            return f"{self.words_typed}"
