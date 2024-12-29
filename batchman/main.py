import atexit
from dataclasses import dataclass
from functools import partial
from typing import Iterable
from textual.screen import Screen
from textual.app import ComposeResult, App, SystemCommand
from textual.command import DiscoveryHit, Hit, Hits, Provider, CommandPalette
from textual.containers import HorizontalGroup, VerticalScroll
from textual.widgets import Footer, Header, Rule

import boto3
import pathlib
import yaml

from batchman.widgets.job_filter import JobFilter
from batchman.widgets.job_table import JobTable
from batchman.lib.batch import get_job_queue_names, get_region_names


CONFIG_LOCATION = pathlib.Path.home() / ".batchman.yml"


@dataclass
class Config:
    job_queue_name: str | None = "default"
    region: str | None = "eu-west-1"
    theme: str | None = "textual-light"
    display_filter: bool = True

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_LOCATION.exists():
            return cls()

        with open(CONFIG_LOCATION, "r") as file:
            data = yaml.safe_load(file)

        return cls(**data)

    def save(self) -> None:
        with open(CONFIG_LOCATION, "w") as file:
            yaml.safe_dump(self.__dict__, file)


class SelectJobQueueCommand(Provider):
    eager = False

    async def startup(self) -> None:
        worker = self.app.run_worker(lambda: get_job_queue_names(self.app.boto_client), thread=True)
        self.queue_names = await worker.wait()

    async def discover(self):
        if self.eager:
            for queue_name in self.queue_names:
                yield DiscoveryHit(queue_name, partial(self.app.set_job_queue, queue_name))

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        for queue_name in self.queue_names:
            command = queue_name
            score = matcher.match(command)

            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(command),
                    partial(self.app.set_job_queue, queue_name),
                    help="Change job queue",
                )


class SelectRegionCommand(Provider):
    eager = False

    async def startup(self) -> None:
        worker = self.app.run_worker(get_region_names, thread=True)
        self.region_names = await worker.wait()

    async def discover(self):
        if self.eager:
            for region_name in self.region_names:
                yield DiscoveryHit(region_name, partial(self.app.set_region, region_name))

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        for region_name in self.region_names:
            command = region_name
            score = matcher.match(command)

            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(command),
                    partial(self.app.set_region, region_name),
                    help="Change region",
                )


class EagerSelectRegionCommand(SelectRegionCommand):
    eager = True


class EagerSelectJobQueueCommand(SelectJobQueueCommand):
    eager = True


class BatchmanApp(App):
    BINDINGS = [
        ("a", "select_all", "Select all jobs"),
        # ("c", "change_queue", "Change job queue"),
        ("d", "view_details", "View job details"),
        ("e", "toggle_expand_array_job", "Toggle array job expansion"),
        # ("f", "toggle_filter", "Toggle filter visibility"),
        ("l", "view_logs", "View job logs"),
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("space", "toggle_selection", "Toggle selection"),
        ("x", "clear_selection", "Clear selection"),
    ]

    COMMANDS = App.COMMANDS | {SelectJobQueueCommand} | {SelectRegionCommand}

    CSS_PATH = "batchman.tcss"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.AUTO_FOCUS = "JobTable"

        self.config = Config.load()
        self.theme = self.config.theme
        atexit.register(self.config.save)

        self.boto_client = self.get_boto_client()

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Change job queue",
            "Change the current job queue",
            self.action_change_queue,
        )
        yield SystemCommand(
            "Change region",
            "Change the current region",
            self.action_change_region,
        )
        yield SystemCommand(
            "Toggle filter",
            "Toggle filter visibility",
            self.action_toggle_filter,
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with HorizontalGroup():
            with VerticalScroll():
                yield JobTable()
            yield Rule(orientation="vertical", line_style="heavy")
            yield JobFilter()
        yield Footer()

    def update_header(self):
        self.title = f"Batchman - {self.config.job_queue_name}"

    def set_job_queue(self, job_queue: str):
        self.config.job_queue_name = job_queue
        self.update_header()
        self.query_one(JobTable).refresh_jobs()

    def get_boto_client(self):
        return boto3.client("batch", region_name=self.config.region)

    def set_region(self, region: str):
        self.config.region = region
        self.boto_client = self.get_boto_client()
        self.update_header()
        self.query_one(JobTable).refresh_jobs()

    #
    # Event handlers
    #
    def on_mount(self):
        self.update_header()
        self.theme_changed_signal.subscribe(self, self.on_theme_changed)
        try:
            self.query_one(JobFilter).display = self.config.display_filter
        except:
            ...

    def on_job_filter_changed(self, message: JobFilter.Changed):
        self.query_one(JobTable).update_filter_settings(message.filter_settings)

    def on_theme_changed(self, signal):
        self.config.theme = self.theme

    #
    # Actions
    #
    def action_change_queue(self) -> None:
        self.push_screen(CommandPalette(providers=[EagerSelectJobQueueCommand], placeholder="Select job queue"))

    def action_change_region(self) -> None:
        self.push_screen(CommandPalette(providers=[EagerSelectRegionCommand], placeholder="Select region"))

    def action_select_all(self) -> None:
        self.query_one(JobTable).select_all()

    def action_clear_selection(self) -> None:
        self.query_one(JobTable).clear_selection()

    def action_toggle_selection(self) -> None:
        job_table = self.query_one(JobTable)
        job_table.toggle_selected(job_table.cursor_row)

    def action_toggle_expand_array_job(self) -> None:
        job_table = self.query_one(JobTable)
        job_table.toggle_expand_array_job(job_table.cursor_row)

    def action_view_details(self) -> None:
        self.query_one(JobTable).view_job_details()

    def action_view_logs(self) -> None:
        self.query_one(JobTable).view_job_logs()

    def action_refresh(self) -> None:
        self.query_one(JobTable).refresh_jobs()

    def action_quit(self) -> None:
        self.exit()

    def action_toggle_filter(self) -> None:
        job_filter = self.query_one(JobFilter)
        job_filter.display = not job_filter.display
        self.config.display_filter = job_filter.display


def main():
    app = BatchmanApp()
    app.run()


if __name__ == "__main__":
    main()
