import asyncio
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, TextArea, Pretty, Rule


class ReadOnlyTextArea(TextArea):
    BINDINGS = TextArea.BINDINGS + [
        Binding("c", "copy", "Copy selected text"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_only = True


class ViewTextScreen(ModalScreen):
    """Screen to view text."""

    def __init__(self, text: str | None = None, text_generator_fn=None, language=None, *args, **kwargs):
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
            Button("Close", variant="primary", id="close"),
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
        self.app.pop_screen()

    def on_key(self, event: Message):
        if event.key in ("escape", "q"):
            event.stop()
            self.app.pop_screen()
