from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, OptionList


class SelectorScreen(ModalScreen):
    """Screen to select something."""

    def __init__(self, prompt_text: str, getter_fn: callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_text = prompt_text
        self.getter_fn = getter_fn
        self.selected = None

        self.AUTO_FOCUS = "OptionList"

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.prompt_text, id="question"),
            OptionList(*sorted(self.getter_fn()), id="selector"),
            HorizontalGroup(
                Button("Submit", variant="success", id="submit"),
                Button("Cancel", variant="primary", id="cancel"),
            ),
            id="selector-screen",
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.selected = event.option.prompt
        self.app.pop_screen()
        self.app.set_job_queue(self.selected)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self.selected = event.option.prompt

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()
        if event.button.id == "submit":
            self.app.set_job_queue(self.selected)
