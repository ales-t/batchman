from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, HorizontalGroup
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Rule, Static, TextArea

from batchman.modals.text_input_screen import TextInputScreen


class ReadOnlyTextArea(TextArea):
    BINDINGS = TextArea.BINDINGS + [
        Binding("c", "copy", "Copy selected text"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_only = True


class ViewTextScreen(ModalScreen):
    """Screen to view text."""

    def __init__(
        self,
        *args,
        text: str | None = None,
        text_generator_fn=None,
        language: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.AUTO_FOCUS = "ReadOnlyTextArea"

        self.text = ""
        self.language = language

        if text:
            self.text = text
        elif text_generator_fn:
            self.generator_fn = text_generator_fn
        else:
            raise ValueError("No text or text generator function provided")

    def compose(self) -> ComposeResult:
        yield Grid(
            ReadOnlyTextArea(self.text, id="text", language=self.language),
            Rule(),
            HorizontalGroup(
                Button("Close", variant="primary", id="close"),
            ),
            id="view-text-screen",
        )

    def on_mount(self):
        if hasattr(self, "generator_fn"):
            self.query_one("#text").loading = True
            self.generate()

    @work(thread=True)
    def generate(self):
        text_widget = self.query_one("#text")
        for line in self.generator_fn():
            self.text = "\n".join([self.text, line])
        text_widget.text = self.text
        text_widget.loading = False
        text_widget.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.app.pop_screen()

    def on_key(self, event: Message):
        if event.key in ("escape", "q"):
            event.stop()
            self.app.pop_screen()


class ViewTextScreenWithSaveButton(ViewTextScreen):
    def __init__(
        self,
        *args,
        default_file_name: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.default_file_name = default_file_name

    def compose(self):
        yield Grid(
            ReadOnlyTextArea(self.text, id="text", language=self.language),
            Rule(),
            HorizontalGroup(
                Button("Close", variant="primary", id="close"),
                Static("", classes="spacer"),
                Button("Save to file", variant="success", id="save-to-file"),
            ),
            id="view-text-screen",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # this is the strangest behavior: inheritance registers both event handlers (parent and child class)
        # (which means closing is handled in the base class and we shouldn't do it here)
        if event.button.id == "save-to-file":
            self.show_file_save_dialog()

    def show_file_save_dialog(self):
        def save_file_callback(file_path: str):
            try:
                with open(file_path, "w") as f:
                    f.write(self.text)
                self.app.notify(f"File saved to {file_path}", severity="success")
            except Exception as e:
                self.app.notify(f"Failed to save file: {e}", severity="error")

        self.app.push_screen(TextInputScreen("Enter file path", save_file_callback, self.default_file_name))
