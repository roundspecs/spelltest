import csv
import curses
import os
from curses import wrapper
from typing import Callable, List, Tuple

import config

show_cursor = lambda: print("\x1b[?25h")
hide_cursor = lambda: print("\x1b[?25l")

dirname = os.path.dirname(__file__)
workbooks_dir_path = os.path.join(dirname, "wordbooks")


def main(stdscr):
    curses.init_pair(1, config.COLOR_SUCCESS, curses.COLOR_BLACK)
    curses.init_pair(2, config.COLOR_WARNING, curses.COLOR_BLACK)
    curses.init_pair(3, config.COLOR_ERROR, curses.COLOR_BLACK)
    COLOR_SUCCESS = curses.color_pair(1)
    COLOR_WARNING = curses.color_pair(2)
    COLOR_ERROR = curses.color_pair(3) | curses.A_BOLD

    def home_screen(messages: List[Tuple] = []):
        existing_wordbook_names = get_existing_wordbook_names()
        existing_wordbook_names_option = [(name,) for name in existing_wordbook_names]
        select_screen(
            title="Welcome to spelltest!",
            prompt="Select a wordbook:",
            options=[
                *existing_wordbook_names_option,
                ("Create a new wordbook", COLOR_WARNING),
            ],
            option_functions=[
                *[lambda: wordbook_screen(name) for name in existing_wordbook_names],
                new_wordbook_screen,
            ],
            messages=messages,
            onExit=exit,
        )

    def new_wordbook_screen(messages: List[Tuple] = []):
        prompt_screen(
            title="Create a new wordbook",
            messages=[
                *messages,
                ("Wordbook names must be unique.",),
            ],
            prompt="Name: ",
            onComplete=handle_wordbook_creation,
            onExit=home_screen,
        )

    def wordbook_screen(name: str):
        select_screen(
            title=f"Wordbook: {name}",
            prompt="Select an option:",
            options=[
                ("Start practice",),
                ("Add new word(s)",),
                ("Remove word(s)", COLOR_ERROR),
                ("Reset score", COLOR_ERROR),
                ("Delete wordbook", COLOR_ERROR),
            ],
            # TODO
            option_functions=[
                None,
                lambda: add_word_screen(name),
            ],
            onExit=home_screen,
        )

    def add_word_screen(wordbook_name: str):
        select_screen(
            title="Add new word(s)",
            options=[
                ("Add manually",),
                ("Add from txt file",),
            ],
            option_functions=[
                lambda: add_word_manually_screen(wordbook_name),
                lambda: add_word_from_txt_screen(wordbook_name),
            ],
            onExit=lambda: wordbook_screen(wordbook_name),
        )

    def add_word_from_txt_screen(
        wordbook_name: str,
        messages: List[Tuple] = [],
    ):
        prompt_screen(
            title="Add word(s) from txt file",
            messages=[
                *messages,
                ("Enter the relative path of the txt file.",),
                ("Duplicate words will be removed automatically.",),
            ],
            prompt="Path: ",
            onComplete=lambda path: handle_add_word_from_txt(wordbook_name, path),
            onExit=lambda: add_word_screen(wordbook_name),
        )

    def add_word_manually_screen(
        wordbook_name: str,
        messages: List[Tuple] = [],
    ):
        prompt_screen(
            title="Add word(s) manually",
            messages=[
                *messages,
                ("Enter the words separated by comma",),
                ("Duplicate words will be removed automatically.",),
            ],
            prompt="Words: ",
            onComplete=lambda comma_sep_words: handle_add_word_manually(
                wordbook_name, comma_sep_words
            ),
            onExit=lambda: add_word_screen(wordbook_name),
        )

    def handle_add_word_manually(wordbook_name: str, comma_sep_words: str):
        words = [word.strip() for word in comma_sep_words.split(",")]
        insert_words_to_wordbook(wordbook_name, words)

    def handle_add_word_from_txt(wordbook_name: str, path: str):
        if not path.endswith(".txt"):
            path += ".txt"
        words = []
        try:
            with open(path) as f:
                for word in f.readlines():
                    word = word.strip()
                    if word.isalpha():
                        words.append(word)
                    else:
                        return add_word_from_txt_screen(
                            wordbook_name,
                            messages=[
                                (f"Error: '{word}' is not a valid word", COLOR_ERROR),
                            ],
                        )
        except FileNotFoundError:
            return add_word_from_txt_screen(
                wordbook_name,
                messages=[
                    (f"Error: No txt file named '{path}' found.", COLOR_ERROR),
                ],
            )
        insert_words_to_wordbook(wordbook_name, words)

    def insert_words_to_wordbook(wordbook_name: str, words: List[str]):
        wordbook_file_name = wordbook_name + ".csv"
        wordbook_path = os.path.join(workbooks_dir_path, wordbook_file_name)
        existing_words = []
        with open(wordbook_path) as csv_file:
            reader = csv.reader(csv_file)
            next(reader)
            for row in reader:
                existing_words.append(row[0])
        with open(wordbook_path, "a") as csv_file:
            writer = csv.writer(csv_file)
            for word in words:
                if word not in existing_words:
                    writer.writerow([word, 0])

    def handle_wordbook_creation(name: str):
        existing_wordbook_names = get_existing_wordbook_names()
        if name in existing_wordbook_names:
            return new_wordbook_screen(
                messages=[
                    (
                        f"Error: There is already a wordbook named '{name}'.",
                        COLOR_ERROR,
                    ),
                ]
            )
        new_wordbook_path = os.path.join(workbooks_dir_path, f"{name}.csv")
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

    def get_existing_wordbook_names():
        existing_wordbook_files = os.listdir(workbooks_dir_path)
        existing_wordbook_names = [file[:-4] for file in existing_wordbook_files]
        return existing_wordbook_names

    def select_screen(
        title: str,
        options: List[Tuple],
        option_functions: List[Callable],
        onExit: Callable,
        prompt: str = "Select an option",
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
                    ("x", "exit"),
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
                key_pressed in config.KEYS["down"]
                and selected_option_index != len(options) - 1
            ):
                selected_option_index += 1
            elif key_pressed in config.KEYS["up"] and selected_option_index != 0:
                selected_option_index -= 1
            elif key_pressed in config.KEYS["select"]:
                return option_functions[selected_option_index]()
            elif key_pressed in config.KEYS["back"]:
                onExit()
            elif key_pressed in config.KEYS["exit"]:
                exit()

    def prompt_screen(
        title: str,
        onComplete: Callable,
        prompt: str,
        onExit: Callable,
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
        messages = [("Enter empty string to exit",)] + messages
        for message in messages:
            stdscr.addstr(*message)
            stdscr.addstr("\n")
        stdscr.addstr(prompt)
        stdscr.refresh()
        answer = stdscr.getstr().decode("utf-8")
        if answer == "":
            onExit()
        else:
            onComplete(answer)

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
