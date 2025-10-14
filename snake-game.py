import pygame
import random
import os
import json

DEFAULT_SCREEN_WIDTH = 640
DEFAULT_SCREEN_HEIGHT = 480
GRID_SIZE = 20

FONT_NAME = "arial"
HIGHSCORE_FILE = "highscores.txt"
SETTINGS_FILE = "settings.json"
MAX_NAME_LENGTH = 10
MAX_HIGHSCORES = 10

BACKGROUND_COLOR = (20, 20, 20)
SNAKE_COLOR = (40, 200, 40)
SNAKE_HEAD_COLOR = (20, 160, 20)
FOOD_COLOR = (220, 60, 60)
TEXT_COLOR = (230, 230, 230)
ACCENT_COLOR = (100, 180, 255)
MENU_SELECT_COLOR = (255, 215, 0)
DIM_TEXT_COLOR = (180, 180, 180)

MIN_WINDOW_WIDTH = DEFAULT_SCREEN_WIDTH
MIN_WINDOW_HEIGHT = DEFAULT_SCREEN_HEIGHT

STATE_MENU = "menu"
STATE_SPEED = "speed"
STATE_GAME = "game"
STATE_GAMEOVER = "gameover"
STATE_HIGHSCORES = "highscores"
STATE_NAMEENTRY = "nameentry"

def load_highscores():
    scores = []
    if os.path.exists(HIGHSCORE_FILE):
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",", 1)
                if len(parts) == 2:
                    name, score_str = parts
                    try:
                        score = int(score_str)
                        scores.append((name, score))
                    except ValueError:
                        pass
    scores.sort(key=lambda s: s[1], reverse=True)
    return scores[:MAX_HIGHSCORES]

def save_highscore(name, score):
    scores = load_highscores()
    scores.append((name, score))
    scores.sort(key=lambda s: s[1], reverse=True)
    scores = scores[:MAX_HIGHSCORES]
    with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
        for n, s in scores:
            f.write(f"{n},{s}\n")

def load_settings():
    defaults = {
        "speed_level": 5,
        "fullscreen": False,
        "window_size": [DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT],
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = defaults.copy()
            if isinstance(data, dict):
                if "speed_level" in data and isinstance(data["speed_level"], int):
                    settings["speed_level"] = max(1, min(10, data["speed_level"]))
                if "fullscreen" in data and isinstance(data["fullscreen"], bool):
                    settings["fullscreen"] = data["fullscreen"]
                if "window_size" in data and isinstance(data["window_size"], (list, tuple)) and len(data["window_size"]) == 2:
                    w, h = int(data["window_size"][0]), int(data["window_size"][1])
                    settings["window_size"] = [max(MIN_WINDOW_WIDTH, w), max(MIN_WINDOW_HEIGHT, h)]
            return settings
        except Exception:
            return defaults
    else:
        return defaults

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass

def draw_text(surface, text, size, color, x, y, center=False, bold=False):
    font = pygame.font.SysFont(FONT_NAME, size, bold=bold)
    label = font.render(text, True, color)
    rect = label.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(label, rect)

def speed_to_fps(speed_level):
    return int(6 + (speed_level - 1) * (16 / 9))

def clamp_name_to_letters(name):
    return "".join([ch for ch in name if ch.isalpha()])[:MAX_NAME_LENGTH]

class SnakeGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Snake")

        self.settings = load_settings()
        self.speed_level = self.settings.get("speed_level", 5)
        self.fullscreen = self.settings.get("fullscreen", False)
        self.prev_window_size = tuple(self.settings.get("window_size", [DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT]))

        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        if self.fullscreen:
            info = pygame.display.Info()
            width, height = info.current_w or DEFAULT_SCREEN_WIDTH, info.current_h or DEFAULT_SCREEN_HEIGHT
        else:
            width, height = self.prev_window_size

        self.screen = pygame.display.set_mode((width, height), flags)
        self.screen_width, self.screen_height = self.screen.get_size()
        self.grid_size = GRID_SIZE
        self.grid_width = self.screen_width // self.grid_size
        self.grid_height = self.screen_height // self.grid_size

        self.clock = pygame.time.Clock()
        self.fps = speed_to_fps(self.speed_level)

        self.state = STATE_MENU
        self.menu_index = 0

        self.highscores = load_highscores()

        self.reset_game()

        self.entered_name = ""
        self.next_state_after_name = STATE_MENU
        self.gameover_options = ["Start Again", "Back to Menu"]
        self.gameover_index = 0

        self.snd_eat = None
        try:
            pygame.mixer.init()
        except Exception:
            pass

        self.update_menu_labels()

    def update_menu_labels(self):
        fs_label = "Fullscreen: On" if self.fullscreen else "Fullscreen: Off"
        self.menu_options = ["Start Game", fs_label, "Adjust Snake Speed", "High Scores", "Quit"]

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.prev_window_size = (self.screen_width, self.screen_height)
            info = pygame.display.Info()
            w, h = info.current_w or DEFAULT_SCREEN_WIDTH, info.current_h or DEFAULT_SCREEN_HEIGHT
            pygame.display.set_mode((w, h), pygame.FULLSCREEN)
            self.fullscreen = True
        else:
            w = max(self.prev_window_size[0], MIN_WINDOW_WIDTH)
            h = max(self.prev_window_size[1], MIN_WINDOW_HEIGHT)
            pygame.display.set_mode((w, h), pygame.RESIZABLE)
            self.fullscreen = False

        self.screen = pygame.display.get_surface()
        self.screen_width, self.screen_height = self.screen.get_size()
        self.grid_width = self.screen_width // self.grid_size
        self.grid_height = self.screen_height // self.grid_size

        self.settings["fullscreen"] = self.fullscreen
        self.settings["window_size"] = [self.screen_width, self.screen_height]
        save_settings(self.settings)
        self.update_menu_labels()

    def reset_game(self):
        self.grid_width = max(1, self.screen_width // self.grid_size)
        self.grid_height = max(1, self.screen_height // self.grid_size)
        self.snake = [(self.grid_width // 2, self.grid_height // 2)]
        self.direction = (1, 0)
        self.pending_direction = self.direction
        self.food = self.random_food_position(self.snake)
        self.score = 0
        self.grow = 0

    def random_food_position(self, snake):
        if self.grid_width <= 0 or self.grid_height <= 0:
            return (0, 0)
        while True:
            pos = (random.randint(0, self.grid_width - 1), random.randint(0, self.grid_height - 1))
            if pos not in snake:
                return pos

    def draw_grid(self):
        for x in range(0, self.screen_width, self.grid_size):
            pygame.draw.line(self.screen, (30, 30, 30), (x, 0), (x, self.screen_height))
        for y in range(0, self.screen_height, self.grid_size):
            pygame.draw.line(self.screen, (30, 30, 30), (0, y), (self.screen_width, y))

    def draw_snake(self):
        for i, (x, y) in enumerate(self.snake):
            rect = pygame.Rect(x * self.grid_size, y * self.grid_size, self.grid_size, self.grid_size)
            color = SNAKE_HEAD_COLOR if i == 0 else SNAKE_COLOR
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BACKGROUND_COLOR, rect, 1)

    def draw_food(self):
        x, y = self.food
        rect = pygame.Rect(x * self.grid_size, y * self.grid_size, self.grid_size, self.grid_size)
        pygame.draw.rect(self.screen, FOOD_COLOR, rect)

    def draw_hud(self):
        draw_text(self.screen, f"Score: {self.score}", 20, TEXT_COLOR, 10, 10)
        font = pygame.font.SysFont(FONT_NAME, 20)
        label = font.render(f"Speed: {self.speed_level}", True, TEXT_COLOR)
        self.screen.blit(label, (self.screen_width - 10 - label.get_width(), 10))

    def handle_menu_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(self.menu_options)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
            elif event.key == pygame.K_RETURN:
                choice = self.menu_options[self.menu_index]
                if choice == "Start Game":
                    self.reset_game()
                    self.state = STATE_GAME
                elif choice.startswith("Fullscreen"):
                    self.toggle_fullscreen()
                elif choice == "Adjust Snake Speed":
                    self.state = STATE_SPEED
                elif choice == "High Scores":
                    self.highscores = load_highscores()
                    self.state = STATE_HIGHSCORES
                elif choice == "Quit":
                    self.settings["speed_level"] = self.speed_level
                    if not self.fullscreen:
                        self.settings["window_size"] = [self.screen_width, self.screen_height]
                    save_settings(self.settings)
                    pygame.quit()
                    raise SystemExit
            elif event.key == pygame.K_ESCAPE:
                self.settings["speed_level"] = self.speed_level
                if not self.fullscreen:
                    self.settings["window_size"] = [self.screen_width, self.screen_height]
                save_settings(self.settings)
                pygame.quit()
                raise SystemExit

    def render_menu(self):
        self.update_menu_labels()
        self.screen.fill(BACKGROUND_COLOR)
        draw_text(self.screen, "simple snake", 48, ACCENT_COLOR, self.screen_width // 2, 90, center=True, bold=True)
        for i, option in enumerate(self.menu_options):
            color = MENU_SELECT_COLOR if i == self.menu_index else TEXT_COLOR
            draw_text(self.screen, option, 28, color, self.screen_width // 2, 180 + i * 40, center=True)
        draw_text(self.screen, "use [up] and [down] arrow keys to navigate.", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 60, center=True)

        draw_text(self.screen, "use [Enter] key to select. use [esc] key to quit", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 30, center=True)

    def handle_speed_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.speed_level = max(1, self.speed_level - 1)
                self.fps = speed_to_fps(self.speed_level)
                self.settings["speed_level"] = self.speed_level
                save_settings(self.settings)
            elif event.key == pygame.K_RIGHT:
                self.speed_level = min(10, self.speed_level + 1)
                self.fps = speed_to_fps(self.speed_level)
                self.settings["speed_level"] = self.speed_level
                save_settings(self.settings)
            elif event.key == pygame.K_ESCAPE:
                self.state = STATE_MENU
            elif event.key == pygame.K_RETURN:
                self.state = STATE_MENU

    def render_speed(self):
        self.screen.fill(BACKGROUND_COLOR)
        draw_text(self.screen, "Adjust Snake Speed", 36, ACCENT_COLOR, self.screen_width // 2, 100, center=True, bold=True)
        draw_text(self.screen, f"Speed: {self.speed_level}", 32, TEXT_COLOR, self.screen_width // 2, 170, center=True)
        draw_text(self.screen, "use [Left] and [Right] arrow keys to change snake speed (1-10).", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 60, center=True)

        draw_text(self.screen, "press [Enter] or [Esc] key to return", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 30, center=True)

    def handle_highscores_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = STATE_MENU

    def render_highscores(self):
        self.screen.fill(BACKGROUND_COLOR)
        draw_text(self.screen, "High Scores", 36, ACCENT_COLOR, self.screen_width // 2, 80, center=True, bold=True)
        if not self.highscores:
            draw_text(self.screen, "No scores yet.", 24, TEXT_COLOR, self.screen_width // 2, 150, center=True)
        else:
            y = 150
            for i, (name, score) in enumerate(self.highscores, start=1):
                draw_text(self.screen, f"{i}. {name} - {score}", 24, TEXT_COLOR, self.screen_width // 2, y, center=True)
                y += 32
        draw_text(self.screen, "Esc to return", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 40, center=True)

    def handle_game_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and self.direction != (0, 1):
                self.pending_direction = (0, -1)
            elif event.key == pygame.K_DOWN and self.direction != (0, -1):
                self.pending_direction = (0, 1)
            elif event.key == pygame.K_LEFT and self.direction != (1, 0):
                self.pending_direction = (-1, 0)
            elif event.key == pygame.K_RIGHT and self.direction != (-1, 0):
                self.pending_direction = (1, 0)
            elif event.key == pygame.K_ESCAPE:
                self.state = STATE_MENU

    def update_game(self):
        self.direction = self.pending_direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        self.grid_width = max(1, self.screen_width // self.grid_size)
        self.grid_height = max(1, self.screen_height // self.grid_size)

        if not (0 <= new_head[0] < self.grid_width and 0 <= new_head[1] < self.grid_height):
            self.state = STATE_GAMEOVER
            self.gameover_index = 0
            return

        if new_head in self.snake:
            self.state = STATE_GAMEOVER
            self.gameover_index = 0
            return

        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 10
            self.grow += 1
            self.food = self.random_food_position(self.snake)
            if self.snd_eat:
                try:
                    self.snd_eat.play()
                except Exception:
                    pass
        if self.grow > 0:
            self.grow -= 1
        else:
            self.snake.pop()

    def render_game(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_grid()
        self.draw_snake()
        self.draw_food()
        self.draw_hud()

    def handle_gameover_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.gameover_index = (self.gameover_index - 1) % len(self.gameover_options)
            elif event.key == pygame.K_DOWN:
                self.gameover_index = (self.gameover_index + 1) % len(self.gameover_options)
            elif event.key == pygame.K_RETURN:
                choice = self.gameover_options[self.gameover_index]
                if choice == "Start Again":
                    self.reset_game()
                    self.state = STATE_GAME
                elif choice == "Back to Menu":
                    self.entered_name = ""
                    self.state = STATE_NAMEENTRY
            elif event.key == pygame.K_ESCAPE:
                self.entered_name = ""
                self.state = STATE_NAMEENTRY

    def render_gameover(self):
        self.screen.fill(BACKGROUND_COLOR)
        draw_text(self.screen, "Game Over", 48, ACCENT_COLOR, self.screen_width // 2, 120, center=True, bold=True)
        draw_text(self.screen, f"Score: {self.score}", 32, TEXT_COLOR, self.screen_width // 2, 180, center=True)

        for i, option in enumerate(self.gameover_options):
            color = MENU_SELECT_COLOR if i == self.gameover_index else TEXT_COLOR
            draw_text(self.screen, option, 28, color, self.screen_width // 2, 250 + i * 40, center=True)

        draw_text(self.screen, "Up/Down to choose, Enter to confirm", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 40, center=True)

    def handle_nameentry_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                name = self.entered_name if self.entered_name else "Player"
                save_highscore(name, self.score)
                self.highscores = load_highscores()
                self.state = STATE_MENU
            elif event.key == pygame.K_BACKSPACE:
                self.entered_name = self.entered_name[:-1]
            elif event.key == pygame.K_ESCAPE:
                name = self.entered_name if self.entered_name else "Player"
                save_highscore(name, self.score)
                self.highscores = load_highscores()
                self.state = STATE_MENU
            else:
                ch = event.unicode
                if ch and ch.isalpha() and len(self.entered_name) < MAX_NAME_LENGTH:
                    self.entered_name += ch

    def render_nameentry(self):
        self.screen.fill(BACKGROUND_COLOR)
        draw_text(self.screen, "Enter your name", 36, ACCENT_COLOR, self.screen_width // 2, 140, center=True, bold=True)
        draw_text(self.screen, f"(letters only, max {MAX_NAME_LENGTH})", 20, DIM_TEXT_COLOR, self.screen_width // 2, 180, center=True)
        display_name = self.entered_name if self.entered_name else "_"
        draw_text(self.screen, display_name, 32, TEXT_COLOR, self.screen_width // 2, 230, center=True)
        draw_text(self.screen, "Enter to save, Esc to cancel", 18, DIM_TEXT_COLOR, self.screen_width // 2, self.screen_height - 40, center=True)

    def run(self):
        while True:
            self.update_menu_labels()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.settings["speed_level"] = self.speed_level
                    if not self.fullscreen:
                        self.settings["window_size"] = [self.screen_width, self.screen_height]
                    save_settings(self.settings)
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    new_w = max(MIN_WINDOW_WIDTH, event.w)
                    new_h = max(MIN_WINDOW_HEIGHT, event.h)
                    pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                    self.screen = pygame.display.get_surface()
                    self.screen_width, self.screen_height = self.screen.get_size()
                    self.grid_width = max(1, self.screen_width // self.grid_size)
                    self.grid_height = max(1, self.screen_height // self.grid_size)
                    self.settings["window_size"] = [self.screen_width, self.screen_height]
                    save_settings(self.settings)

                if self.state == STATE_MENU:
                    self.handle_menu_events(event)
                elif self.state == STATE_SPEED:
                    self.handle_speed_events(event)
                elif self.state == STATE_HIGHSCORES:
                    self.handle_highscores_events(event)
                elif self.state == STATE_GAME:
                    self.handle_game_events(event)
                elif self.state == STATE_GAMEOVER:
                    self.handle_gameover_events(event)
                elif self.state == STATE_NAMEENTRY:
                    self.handle_nameentry_events(event)

            if self.state == STATE_GAME:
                self.update_game()

            if self.state == STATE_MENU:
                self.render_menu()
            elif self.state == STATE_SPEED:
                self.render_speed()
            elif self.state == STATE_HIGHSCORES:
                self.render_highscores()
            elif self.state == STATE_GAME:
                self.render_game()
            elif self.state == STATE_GAMEOVER:
                self.render_gameover()
            elif self.state == STATE_NAMEENTRY:
                self.render_nameentry()

            pygame.display.flip()
            self.clock.tick(self.fps if self.state == STATE_GAME else 60)

if __name__ == "__main__":
    SnakeGame().run()
