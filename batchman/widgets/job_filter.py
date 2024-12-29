from dataclasses import dataclass
from textual.containers import Vertical
from textual.widgets import Label, Input, SelectionList, Static, Rule
from textual.message import Message


@dataclass
class FilterSettings:
    job_name: str
    statuses: list[str]

    def job_matches(self, job: dict) -> bool:
        if self.job_name and not job["jobName"].startswith(self.job_name):
            return False

        if self.statuses and job["status"] not in self.statuses:
            return False

        return True


class JobFilter(Static):
    class Changed(Message):
        def __init__(self, filter_settings: FilterSettings):
            self.filter_settings = filter_settings
            super().__init__()

    def compose(self):
        yield Vertical(
            Label("[b] Filter [/b]"),
            Rule(),
            Label("Job Name", classes="filter-type-label"),
            Input(placeholder="Name prefix...", id="job_name_filter"),
            Label("Status", classes="filter-type-label"),
            SelectionList(
                ("SUBMITTED", "SUBMITTED"),
                ("PENDING", "PENDING"),
                ("RUNNABLE", "RUNNABLE"),
                ("STARTING", "STARTING"),
                ("RUNNING", "RUNNING"),
                ("SUCCEEDED", "SUCCEEDED"),
                ("FAILED", "FAILED"),
                id="status_filter",
            ),
            id="filter-vertical",
        )

    def send_filter_update(self) -> None:
        filter_settings = FilterSettings(
            job_name=self.query_one("#job_name_filter", Input).value,
            statuses=[s for s in self.query_one("#status_filter", SelectionList).selected],
        )

        self.post_message(JobFilter.Changed(filter_settings))

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged):
        self.send_filter_update()

    def on_input_changed(self, event: Input.Changed):
        self.send_filter_update()
