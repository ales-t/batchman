from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Rule, Static


class TextInputScreen(ModalScreen):
    """Screen to input text."""

    def __init__(
        self, prompt_text: str, on_confirm_callback: callable, default_text: str | None = None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.prompt_text = prompt_text
        self.input_text = default_text or ""
        self.confirm_callback = on_confirm_callback

        self.AUTO_FOCUS = "Input"

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.prompt_text, id="question"),
            Input(self.input_text, id="input"),
            Rule(),
            HorizontalGroup(
                Button("Confirm", variant="success", id="confirm"),
                Static("", classes="spacer"),
                Button("Cancel", variant="primary", id="cancel"),
            ),
            id="text-input-screen",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()
        if event.button.id == "confirm":
            self.confirm_callback(self.query_one("#input").value)
