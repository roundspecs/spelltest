import csv
import curses
import json
import pyttsx3
import os
import requests
from curses import wrapper
from typing import Any, Callable, Dict, List, Tuple

import config
import playsound

tts = pyttsx3.init()
tts.setProperty('rate', config.TTS_RATE)

def speak(text):
  tts.say(text)
  tts.runAndWait()

show_cursor = lambda: print("\x1b[?25h")
hide_cursor = lambda: print("\x1b[?25l")

dirname = os.path.dirname(__file__)
wordbooks_dir_path = os.path.join(dirname, "wordbooks")

# TODO: Redesign to class

def get_word_details(word: str) -> dict[str, str | List[dict]]:
    response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
    word_details = {
        "word": word,
        "phonetics": [],
        "meanings": [],
    }
    if response.status_code == 200:
        response_data: Dict = response.json()[0]
        for item in response_data.get("phonetics", []):
            word_details["phonetics"].append(
                {
                    "audio": item.get("audio", ""),
                    "text": item.get("text", ""),
                }
            )
        for meaning in response_data.get("meanings", []):
            parts_of_speech = meaning.get("partOfSpeech", None)
            definitions = []
            synonyms = []
            antonyms = []
            for definition in meaning.get("definitions", []):
                d = definition.get("definition", False)
                if type(d) == str and word not in d.lower():
                    definitions.append(d)
                synonyms.extend(definition.get("synonyms"))
                antonyms.extend(definition.get("antonyms"))
            synonyms.extend(meaning.get("synonyms"))
            antonyms.extend(meaning.get("antonyms"))
            word_details["meanings"].append(
                {
                    "partsOfSpeech": parts_of_speech,
                    "definitions": definitions,
                    "synonyms": synonyms,
                    "antonyms": antonyms,
                }
            )
    # print(json.dumps(word_details, indent=2))
    # print(word_details)
    return word_details


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
                *[lambda index: wordbook_screen(existing_wordbook_names[index])]
                * len(existing_wordbook_names),
                lambda _: new_wordbook_screen(),
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
                ("Start practice (might take a little time to load)",),
                ("Add new word(s)",),
                ("Remove word(s)", COLOR_ERROR),
                ("Reset score", COLOR_ERROR),
                ("Delete wordbook", COLOR_ERROR),
            ],
            option_functions=[
                lambda _: practice_screen(name),
                lambda _: add_word_screen(name),
                lambda _: remove_words_screen(name),
            ],
            onExit=home_screen,
        )

    def practice_screen(wordbook_name: str):
        wordbook_path = get_wordbook_path(wordbook_name)
        words, scores = get_existing_words_n_scores(wordbook_path)
        class ExitException(Exception):...

        def on_exit():
            raise ExitException()

        def on_complete(input_spelling, word_details):
            if input_spelling == 'r':
                take_test(word_details)
            elif input_spelling == '':
                return
        
        def get_phonetics_n_pronounce(phonetics, word):
            all_phonetics = []
            spoke = False
            for item in phonetics:
                audio = item.get("audio")
                if audio:
                    playsound.playsound(audio)
                    spoke = True
                text = item.get("text")
                if text:
                    all_phonetics.append(item.get("text"))
            if not spoke:
                speak(word)
            return ', '. join(all_phonetics)

        def get_meaning_messages(meanings):
            messages = []
            for meaning in meanings:
                messages.append((meaning.get("partsOfSpeech"), curses.A_ITALIC | curses.A_DIM))
                definitions = meaning.get("definitions")
                if definitions:
                    messages.append((" Definitions:", COLOR_WARNING))
                for definition in definitions:
                    messages.append((f" - {definition}",))
                synonyms = meaning.get("synonyms")
                if synonyms:
                    messages.append((" synonyms:", COLOR_WARNING))
                for synonym in synonyms:
                    messages.append((f" - {synonym}",))
                antonyms = meaning.get("antonyms")
                if antonyms:
                    messages.append((" antonyms:", COLOR_WARNING))
                for antonym in antonyms:
                    messages.append((f" - {antonym}",))
                
            return messages

        def take_test(word_details):
            prompt_screen(
                title=f"{wordbook_name}: Practice",
                messages=[
                    ("Enter 'r' to repeat.",),
                    (f"Phonetics: {get_phonetics_n_pronounce(word_details['phonetics'], word_details['word'])}", COLOR_WARNING),
                    *get_meaning_messages(word_details['meanings']),
                ],
                prompt="Spelling: ",
                onComplete=lambda input_spelling:on_complete(input_spelling, word_details),
                onExit=on_exit,
            )

        try:
            while True:
                min_score = min(scores)
                for word, score in zip(words, scores):
                    if score == min_score:
                        word_details = get_word_details(word)
                        take_test(word_details)
        except ExitException:
            wordbook_screen(wordbook_name)

    def add_word_screen(wordbook_name: str, messages: List[Tuple] = []):
        select_screen(
            title="Add new word(s)",
            messages=messages,
            options=[
                ("Add manually",),
                ("Add from txt file",),
            ],
            option_functions=[
                lambda _: add_word_manually_screen(wordbook_name),
                lambda _: add_word_from_txt_screen(wordbook_name),
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

    def remove_words_screen(wordbook_name: str):
        wordbook_path = get_wordbook_path(wordbook_name)
        existing_words = get_existing_words(wordbook_path)
        options = []
        for word in existing_words:
            options.append((word,))
        select_screen(
            title="Remove Words",
            # title_attr=COLOR_ERROR | config.DEFAULT_TITLE_ATTR,
            prompt="Select the word you want to delete:",
            options=options,
            option_functions=[
                lambda index: handle_remove_word(
                    wordbook_name, wordbook_path, existing_words[index]
                )
            ]
            * len(options),
            onExit=lambda: wordbook_screen(wordbook_name),
        )

    def handle_remove_word(wordbook_name: str, wordbook_path: str, word_to_remove: str):
        existing_rows = []
        with open(wordbook_path, "r") as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                existing_rows.append(row)
        header, entries = existing_rows[:1], existing_rows[1:]
        new_entries = []
        for entry in entries:
            if entry[0] != word_to_remove:
                new_entries.append(entry)
        with open(wordbook_path, "w") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(header)
            writer.writerows(new_entries)
        remove_words_screen(wordbook_name)

    def handle_add_word_manually(wordbook_name: str, comma_sep_words: str):
        words = [word.strip() for word in comma_sep_words.split(",")]
        insert_words_to_wordbook(wordbook_name, words)
        add_word_screen(
            wordbook_name, messages=[("Success: Added the words.", COLOR_SUCCESS)]
        )

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
        wordbook_path = get_wordbook_path(wordbook_name)
        existing_words = get_existing_words(wordbook_path)
        with open(wordbook_path, "a") as csv_file:
            writer = csv.writer(csv_file)
            for word in words:
                if word not in existing_words:
                    writer.writerow([word, 0])

    def get_wordbook_path(wordbook_name):
        wordbook_file_name = wordbook_name + ".csv"
        wordbook_path = os.path.join(wordbooks_dir_path, wordbook_file_name)
        return wordbook_path

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
        new_wordbook_path = os.path.join(wordbooks_dir_path, f"{name}.csv")
        with open(new_wordbook_path, "w") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["word", "score"])
        return home_screen(
            messages=[
                (
                    f"Success: Created new wordbook named '{name}'.",
                    COLOR_SUCCESS,
                ),
            ]
        )

    def get_existing_words(wordbook_path):
        existing_words = []
        with open(wordbook_path) as csv_file:
            reader = csv.reader(csv_file)
            next(reader)
            for row in reader:
                existing_words.append(row[0])
        return existing_words

    def get_existing_words_n_scores(wordbook_path):
        existing_words = []
        scores = []
        with open(wordbook_path) as csv_file:
            reader = csv.reader(csv_file)
            next(reader)
            for row in reader:
                existing_words.append(row[0])
                scores.append(int(row[1]))
        return existing_words, scores

    def get_existing_wordbook_names():
        existing_wordbook_files = os.listdir(wordbooks_dir_path)
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
                return option_functions[selected_option_index](selected_option_index)
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
    # get_word_details("hello")
