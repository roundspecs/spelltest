import curses

MIN_SCREEN_COLS = 50
MIN_SCREEN_LINES = 10

# curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
# curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
# curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
# COLOR_SUCCESS = curses.color_pair(1)
# COLOR_WARNING = curses.color_pair(2)
# COLOR_ERROR = curses.color_pair(3)

DEFAULT_TITLE_ATTR = curses.A_REVERSE
DEFAULT_PROMPT_ATTR = curses.A_BOLD
KEYBINDINGS_KEY_ATTR = curses.A_NORMAL
KEYBINDINGS_VALUE_ATTR = curses.A_REVERSE
