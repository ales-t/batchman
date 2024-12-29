from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Rule, Static


class ConfirmationScreen(ModalScreen):
    """Screen to confirm an action."""

    def __init__(self, prompt_text: str, on_confirm_callback: callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_text = prompt_text
        self.confirm_callback = on_confirm_callback

        self.AUTO_FOCUS = "Button"

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.prompt_text, id="question"),
            Rule(),
            HorizontalGroup(
                Button("Confirm", variant="success", id="confirm"),
                Button("Cancel", variant="primary", id="cancel"),
            ),
            id="confirmation-screen",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()
        if event.button.id == "confirm":
            self.confirm_callback()
