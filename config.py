import curses

MIN_SCREEN_COLS = 50
MIN_SCREEN_LINES = 10

KEYS = {
    "select": [curses.KEY_ENTER, 10, 13, ord("l"), curses.KEY_RIGHT],
    "down": [ord("j"), curses.KEY_DOWN],
    "up": [ord("k"), curses.KEY_UP],
    "back": [ord("h"), curses.KEY_LEFT],
    "exit": [ord("x")],
}

COLOR_SUCCESS = curses.COLOR_GREEN
COLOR_WARNING = curses.COLOR_YELLOW
COLOR_ERROR = curses.COLOR_RED

DEFAULT_TITLE_ATTR = curses.A_REVERSE
DEFAULT_PROMPT_ATTR = curses.A_BOLD
KEYBINDINGS_KEY_ATTR = curses.A_NORMAL
KEYBINDINGS_VALUE_ATTR = curses.A_REVERSE
