import customtkinter as ctk
from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
import os

main_dir = os.path.dirname(os.path.realpath(__file__))
words_path = os.path.join(main_dir,"valid_wordle_words.txt")

with open(words_path, "r", encoding="utf-8") as file:
    words = [line.strip() for line in file]


class WordleLabel(ctk.CTkFrame):
    def __init__(
        self,
        master: WordleTextbox,  # noqa: F821
        index: int = 0,
        *args,
        **kwargs,
    ):
        super().__init__(master, *args, width=90, height=80, **kwargs)
        self.master: WordleTextbox = master
        self.grid_propagate(False)
        self.columnconfigure(0, weight=1)
        self.configure(fg_color="White")

        self.label = ctk.CTkLabel(
            self, text="", text_color="white", font=("Sans-Serif", 40, "bold")
        )
        self.label.grid(row=0, column=0)

        self.optionmenu = ctk.CTkOptionMenu(
            self,
            width=78,
            values=["Gray", "Yellow", "Green"],
            command=self.color_picker,
        )
        self._color_options = {
            "Gray": "#787c7f",  # Letter either doesn't exist or doesn't exist another time if used more than once in that word
            "Yellow": "#c8b653",  # Letter exists *somewhere* in the word
            "Green": "#6ca965",  # Letter exists in that spot of the word
            "White": "#ffffff",  # Letter is empty
            "Black": "#000000",  # Color hasn't been set yet
            "Red": "#ff0000",  # Error or inconsistency
        }
        self.optionmenu.grid(row=1, column=0)
        self.optionmenu.grid_remove()
        self.optionmenu.set("White")

        self.index = index

    def color_picker(self, choice: str):
        self.configure(fg_color=self._color_options[choice])
        self.master.update_color(self.index, choice)
        if choice != "Black":
            self.master.master.update_text()
        self.master.unlock_check()

    @property
    def color(self):
        return self.optionmenu.get()

    @color.setter
    def color(self, color: str):
        if color not in list(self._color_options.keys()):
            return
        self.optionmenu.set(color)
        self.color_picker(color)

    @property
    def letter(self) -> str:
        return self.label.cget("text")

    def change_letter(self, letter: str):
        prev_letter = self.letter
        if letter == prev_letter or (letter and not letter.isalpha()):
            return

        prev_letter_colors = self.master.master.letter_dictionaries(
            self.master.index - 1
        )[self.index]

        self.label.configure(text=letter)
        if letter:
            
            if self.color in ("White", "Red"):
                self.color = prev_letter_colors[letter]
                self.optionmenu.grid()
        else:
            self.color = "White"
            self.optionmenu.grid_remove()


class WordleTextbox(ctk.CTkFrame):
    def __init__(
        self,
        master: App,  # noqa: F821
        index: int = 0,
        *args,
        **kwargs,
    ):
        super().__init__(master, *args, width=600, height=150, **kwargs)
        self.master: App = master
        self.entry = ctk.CTkEntry(
            self,
            validate="key",
            validatecommand=(self.register(self.validate_input), "%P"),
        )
        self.entry.place(x=-100,y=-100)
        self.labels: list[WordleLabel] = []
        for i in range(5):
            self.labels.append(WordleLabel(self, i))
            self.labels[i].grid(row=0, column=i)
            self.labels[i].bind("<Button-1>", lambda _: self.entry.focus())
            self.labels[i].label.bind("<Button-1>", lambda _: self.entry.focus())
        self.index = index
        self.label_values = [("", "White") for i in range(5)]

    def validate_input(self, text: str):
        if (text and not all(char.isalpha() for char in text)) or (
            length := len(text)
        ) > 5:
            return False
        index = self.index
        prev_text = self.entry.get()
        prev_length = len(prev_text)
        for i in range(5):
            letter = text[i].upper() if i < length else ""
            lb = self.labels[i]
            if letter != (prev_text[i].upper() if i < prev_length else ""):
                lb.change_letter(letter if i < length else "")
                self.label_values[i] = (letter, lb.color)
            if length == 5 and text.lower() not in words:
                lb.color_picker("Red")
        if prev_length == 5 and length == 4:
            self.master.clear_rows(index + 1)
        self.unlock_check()
        return True

    def unlock_check(self):
        colors = [letter[1] for letter in self.label_values]
        if all(color not in ("Red", "Black", "White") for color in colors):
            self.master.unlock_textbox(self.index + 1)

    def update_color(self, index: int, color: str):
        letter = self.label_values[index][0]
        self.label_values[index] = (letter, color)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("500x600")
        self.title("Wordle helper")
        self.columnconfigure(0, weight=1)

        self.clear_button = ctk.CTkButton(self,text="Clear",command=lambda: self.clear_rows(0))
        self.clear_button.grid(row=0,column=0)

        self.textboxes: list[WordleTextbox] = []
        for i in range(5):
            tb = WordleTextbox(self, i)
            tb.grid(row=i+1, column=0)
            if i > 0:
                tb.entry.configure(state="disabled")
            self.textboxes.append(tb)

        self.valid_words_label = ctk.CTkLabel(self,text=f"Valid word count: {len(words)}")
        self.valid_words_label.grid(row=6, column=0)
        self.textbox = ctk.CTkTextbox(self, width=500, wrap="word")
        self.textbox.grid(row=7, column=0)
        self.word_char_counts = {}
        for word in words:
            self.word_char_counts[word] = self.char_count(word)
        self.textbox.insert("0.0", ", ".join(words[:2000]))
        self.textbox.configure(state="disabled")

    @property
    def textbox_values(self):
        """
        A list of the textbox values in the structure:
        `l[row][letter_index] = (letter, color)`
        """
        return [self.textboxes[i].label_values for i in range(5)]

    def letter_dictionaries(self, last_row: int = 0):
        """
        Returns a list of the textbox values (upto `last_row`) unified into dictionaries

        Parameters
        ----------
        last_row : int, optional
            _description_, by default 0

        Returns
        -------
        list[dict[str, str]]
            A list of dictionaries with the structure `l[letter_index] = {letter: color}``
        """
        tvs = self.textbox_values[: last_row + 1]
        result: list[dict[str, str]] = [defaultdict(lambda: "Black") for _ in range(5)]

        for tv in tvs:
            for i in range(5):
                if result[i][tv[i][0]] == "Black":
                    result[i][tv[i][0]] = tv[i][1]

        return result

    def clear_rows(self, start_index: int):
        """
        Clears all rows up to `start_index`
        """
        if start_index > 4:
            return
        for i in range(start_index, 5):
            tb = self.textboxes[i]
            if not tb.entry.get():
                continue
            
            tb.validate_input("")
            tb.entry.delete(0,"end")
            if i != 0:
                tb.entry.configure(state="disabled")

    def unlock_textbox(self, index: int):
        """
        Unlocks the `index`th textbox

        Parameters
        ----------
        index : int
            _description_
        """
        self.textboxes[min(index, 4)].entry.configure(state="normal")

    def char_count(self, it: Iterable[str]) -> defaultdict[str, int]:
        """
        Counts the individual letters of an iterable of strings

        Parameters
        ----------
        it : Iterable[str]
            Any iterable of strings, even a string.

        Returns
        -------
        defaultdict[str,int]
            A dictionary of the count of each letter
        """
        d: defaultdict[str,int] = defaultdict(int)
        for string in it:
            for (
                letter
            ) in string:  # Safeguard against lists of strings more than 1 char long
                d[letter] += 1
        return d

    def update_text(self):
        t = self.textbox
        t.configure(state="normal")
        t.delete("0.0", "end")

        filtered_words = deepcopy(words)
        tvs = self.textbox_values

        for tv in tvs:
            if not any(tv[i][0] for i in range(5)):
                break
            min_counts = self.char_count(
                letter.lower() for letter, color in tv if color in ("Green", "Yellow")
            )
            for i in range(5):
                letter, color = tv[i]
                letter = letter.lower()
                if color == "Green":
                    filtered_words = [
                        word for word in filtered_words if word[i] == letter
                    ]
                elif color == "Yellow":
                    filtered_words = [
                        word
                        for word in filtered_words
                        if word[i] != letter and self.word_char_counts[word][letter] > 0
                    ]
                elif color == "Gray":
                    filtered_words = [
                        word
                        for word in filtered_words
                        if self.word_char_counts[word][letter] == min_counts[letter]
                    ]
        self.valid_words_label.configure(text=f"Valid word count: {len(filtered_words)}")
        t.insert("0.0", ", ".join(filtered_words[: min(len(filtered_words), 2000)]))
        t.configure(state="disabled")


app = App()
app.mainloop()
