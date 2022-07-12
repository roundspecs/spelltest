import curses
from curses import wrapper
import os
from typing import Callable, List, Tuple

import config

show_cursor = lambda: print("\x1b[?25h")
hide_cursor = lambda: print("\x1b[?25l")


dirname = os.path.dirname(__file__)
workbooks_dir_path = os.path.join(dirname, "wordbooks")


def main(stdscr):
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    COLOR_SUCCESS = curses.color_pair(1)
    COLOR_WARNING = curses.color_pair(2)
    COLOR_ERROR = curses.color_pair(3) | curses.A_BOLD

    def home_screen(messages: List[Tuple] = []):
        existing_wordbook_files = os.listdir(workbooks_dir_path)
        existing_wordbook_names = [
            file.strip(".json") for file in existing_wordbook_files
        ]
        existing_wordbook_names_option = [(name,) for name in existing_wordbook_names]
        select_screen(
            title="Welcome to spelltest!",
            prompt="Select a wordbook",
            options=[
                *existing_wordbook_names_option,
                ("Create a new wordbook", COLOR_WARNING),
            ],
            option_functions=[
                *[
                    None,
                ]
                * len(existing_wordbook_files),
                new_wordbook_screen,
            ],
            messages=messages,
        )

    def new_wordbook_screen():
        prompt_screen(
            "Create a new wordbook",
            messages=[
                ("Wordbook names must be unique.",),
                ("Enter an empty string to exit.",),
            ],
            onComplete=handle_wordbook_creation,
            prompt="Name: ",
        )

    def select_screen(
        title: str,
        prompt: str,
        options: List[Tuple],
        option_functions: List[Callable],
        messages: List[Tuple] = [],
        title_attr: int = config.DEFAULT_TITLE_ATTR,
        prompt_attr: int = config.DEFAULT_PROMPT_ATTR,
    ):
        hide_cursor()
        selected_option_index = 0
        available_lines = curses.LINES - 3 - len(messages)
        if len(options) > available_lines:
            _stops = [
                i + available_lines - 2
                for i in range(0, len(options) - available_lines + 2)
            ]
            _stops[0] += 1
            _stops[-1] += 1
            _start = 0
            _stop = _stops[0]
        else:
            _start, _stop = 0, -1
        while True:
            stdscr.clear()

            # key bindings
            add_key_bindings(
                [
                    ("x", "back"),
                    ("enter", "select"),
                    ("arrow", "navigation"),
                    ("h", "back"),
                    ("j", "down"),
                    ("k", "up"),
                    ("l", "select"),
                ],
            )

            # title
            add_title(
                title,
                title_attr,
            )

            # messages
            for message in messages:
                stdscr.addstr(*message)
                stdscr.addstr("\n")

            # prompt
            stdscr.addstr(f"{prompt}\n", prompt_attr)

            # options
            add_ellipsis_after_options = False
            if len(options) > available_lines:
                if selected_option_index < _start:
                    _start -= 2 if _start == 2 else 1
                    _stop = _stops[_start]
                elif selected_option_index >= _stop:
                    _start += 2 if _start == 0 else 1
                    _stop = _stops[_start]

                if _start != 0:
                    stdscr.addstr("  ...\n")
                if _stop != len(options):
                    add_ellipsis_after_options = True
                _options = options[_start:_stop]
            else:
                _options = options
            for i, option in enumerate(_options):
                if i + _start == selected_option_index:
                    prefix = "> "
                    try:
                        option = (option[0], option[1] | curses.A_REVERSE)
                    except:
                        option = (*option, curses.A_REVERSE)
                else:
                    prefix = "  "
                stdscr.addstr(prefix)
                stdscr.addstr(*option)
                stdscr.addstr("\n")
            if add_ellipsis_after_options:
                stdscr.addstr("  ...")
            stdscr.refresh()
            key_pressed = stdscr.getch()
            if (
                key_pressed in [ord("j"), curses.KEY_DOWN]
                and selected_option_index != len(options) - 1
            ):
                selected_option_index += 1
            elif (
                key_pressed in [ord("k"), curses.KEY_UP] and selected_option_index != 0
            ):
                selected_option_index -= 1
            elif key_pressed in [curses.KEY_ENTER, 10, 13, ord("l")]:
                return option_functions[selected_option_index]()
            elif key_pressed in [ord("x"), ord("h")]:
                break

    def prompt_screen(
        title: str,
        onComplete: Callable,
        prompt: str,
        title_attr: int = config.DEFAULT_TITLE_ATTR,
        messages: List[Tuple] = [],
    ):
        curses.echo()
        show_cursor()
        stdscr.clear()

        # title
        add_title(
            title,
            title_attr,
        )

        # messages
        for message in messages:
            stdscr.addstr(*message)
            stdscr.addstr("\n")
        stdscr.addstr(prompt)
        stdscr.refresh()
        answer = stdscr.getstr().decode("utf-8")
        onComplete(answer)

    def handle_wordbook_creation(name: str):
        if name == "":
            return home_screen()
        existing_wordbook_files = os.listdir(workbooks_dir_path)
        existing_wordbook_names = [
            file.strip(".json") for file in existing_wordbook_files
        ]
        if name in existing_wordbook_names:
            return home_screen(
                messages=[
                    (
                        f"Error: There is already a wordbook named '{name}'.",
                        COLOR_ERROR,
                    ),
                ]
            )
        new_wordbook_path = os.path.join(workbooks_dir_path, f"{name}.json")
        with open(new_wordbook_path, "w"):
            ...
        return home_screen(
            messages=[
                (
                    f"Success: Created new wordbook named '{name}'.",
                    COLOR_SUCCESS,
                ),
            ]
        )

    def add_key_bindings(key_values: List[Tuple]):
        for key_value in key_values:
            _, x = stdscr.getyx()
            stdscr.addstr(
                curses.LINES - 1, x, f" {key_value[0]}", config.KEYBINDINGS_KEY_ATTR
            )
            _, x = stdscr.getyx()
            stdscr.addstr(
                curses.LINES - 1, x, key_value[1], config.KEYBINDINGS_VALUE_ATTR
            )

    def add_title(title: str, title_attr: int):
        whitespace = curses.COLS - len(title)
        whitespace_left = whitespace // 2
        whitespace_right = whitespace - whitespace_left
        stdscr.addstr(
            0, 0, f'{" " * whitespace_left}{title}{" " * whitespace_right}', title_attr
        )

    if curses.COLS < config.MIN_SCREEN_COLS:
        raise Exception("Error: Please increase the width of the window")
    elif curses.LINES < config.MIN_SCREEN_LINES:
        raise Exception("Error: Please increase the height of the window")
    else:
        home_screen()


if __name__ == "__main__":
    # try:
    wrapper(main)
    # except Exception as e:
    # print(e)
