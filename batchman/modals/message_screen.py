from textual.app import ComposeResult
from textual.containers import Center, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Rule, Static


class MessageScreen(ModalScreen):
    """Screen to show a message."""

    def __init__(self, text: str, fatal: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text
        self.fatal = fatal

        self.AUTO_FOCUS = "Button"

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.text, id="message"),
            Rule(),
            Center(
                Button("OK", variant="primary", id="ok", classes="ok-button"),
            ),
            id="message-screen",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()
        if self.fatal:
            self.app.exit()
