import json
from dataclasses import dataclass
from datetime import datetime

from natsort import natsorted
from textual import log, work
from textual.coordinate import Coordinate
from textual.message import Message
from textual.widgets import DataTable

from batchman.lib.batch import (
    UnauthorizedError,
    get_array_child_jobs,
    get_jobs,
    get_jobs_details,
    get_log_events,
    get_log_stream_name,
    kill_jobs,
)
from batchman.modals.confirmation_screen import ConfirmationScreen
from batchman.modals.message_screen import MessageScreen
from batchman.modals.view_text_screen import (
    ViewTextScreen,
    ViewTextScreenWithSaveButton,
)
from batchman.widgets.job_filter import FilterSettings


@dataclass
class JobRecord:
    job: dict
    selected: bool
    is_array_job: bool
    is_expanded: bool = False
    parent_job: "JobRecord" = None


def utc_from_timestamp(timestamp: int) -> str:
    return datetime.fromtimestamp(float(timestamp) / 1000).strftime("%Y-%m-%d %H:%M:%S")


def inject_highlighted_job(fn):
    """Decorator to inject the currently highlighted job into the function arguments.

    Handles the corner cases so we don't need to repeat ourselves.
    """

    def wrapper(self, *args, **kwargs):
        index = self.cursor_row
        if self.row_count > 0 and index is not None:
            job_record = self.get_job_by_row(index)
            return fn(self, job_record, index, *args, **kwargs)
        else:
            self.app.notify("No job selected", severity="warning")

    return wrapper


class JobTable(DataTable):
    class ErrorStateMessage(Message):
        def __init__(self, message: str, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.message = message

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_settings = FilterSettings("", [])
        self.jobs = []
        self.sorted_by = None
        self.sort_reversed = False

    def on_mount(self):
        super().on_mount()
        self.cursor_type = "row"
        self.add_columns("Selected", "Job Name", "Job ID", "Created At", "Status")
        self.refresh_jobs()

    @work(thread=True, exclusive=True, exit_on_error=False)
    def update(self):
        self.clear()
        self.jobs.clear()

        try:
            for job in get_jobs(self.app.batch_client, self.app.config.job_queue_name):
                visible = self.job_should_be_visible(job)
                self.jobs.append(JobRecord(job=job, selected=False, is_array_job="arrayProperties" in job))
                if visible:
                    self.draw_row(self.jobs[-1])
                    self.loading = False
            self.app.notify("All jobs loaded", severity="information", timeout=1)
        except UnauthorizedError:
            self.post_message(self.ErrorStateMessage("Unauthorized. Did you forget to login?"))
        except Exception as e:
            self.post_message(self.ErrorStateMessage(f"Error loading jobs: {e}"))
        finally:
            self.loading = False
            self.focus()

    def draw_row(self, job: JobRecord):
        job_name = job.job["jobName"]
        if job.is_array_job:
            if job.parent_job is None:  # parent job
                job_name = f"[b][yellow]+[/b][/yellow] {job_name} ({job.job['arrayProperties']['size']} tasks)"
            else:  # child job
                job_name = f"[b][yellow]|[/b][/yellow] {job_name}"

        self.add_row(
            "X" if job.selected else " ",
            job_name,
            job.job["jobId"],
            # convert times to UTC
            utc_from_timestamp(job.job["createdAt"]),
            job.job["status"],
        )

    def on_job_table_error_state_message(self, message):
        self.app.push_screen(MessageScreen(message.message, fatal=True))

    def job_should_be_visible(self, job: dict) -> bool:
        return self.filter_settings.job_matches(job)

    def redraw_rows(self):
        self.clear()
        for job in self.jobs:
            if self.job_should_be_visible(job.job):
                self.draw_row(job)

    def get_job_by_row(self, index: int) -> JobRecord:
        job_id_in_row = self.get_cell_at(Coordinate(index, 2))

        for job in self.jobs:
            if job.job["jobId"] == job_id_in_row:
                return job

        raise ValueError(f"Job with ID {job_id_in_row} not found")

    def get_job_index(self, job_id: str) -> int:
        # note that this assumes identical zero-based indexing of rows in the DataTable
        for index, job in enumerate(self.jobs):
            if job.job["jobId"] == job_id:
                return index

        raise ValueError(f"Job with ID {job_id} not found")

    @inject_highlighted_job
    def toggle_selected(self, job_record: JobRecord, index: int):
        job_record.selected = not job_record.selected

        new_value = "X" if job_record.selected else " "
        self.update_cell_at(Coordinate(index, 0), new_value)

    @inject_highlighted_job
    def toggle_expand_array_job(self, job: JobRecord, index: int):
        if job.is_array_job:
            if job.parent_job:
                self.collapse_array_job(self.get_job_index(job.parent_job.job["jobId"]))
            elif job.is_expanded:
                self.collapse_array_job(index)
            else:
                self.app.notify(f"Expanding array job {job.job['jobName']}, hang tight...", severity="information")
                self.expand_array_job(index)
        else:
            self.app.notify("Can only expand array jobs", severity="warning")

    def collapse_array_job(self, index: int):
        job = self.get_job_by_row(index)
        self.jobs = [j for j in self.jobs if j.parent_job != job]
        job.is_expanded = False
        self.redraw_rows()
        self.cursor_coordinate = Coordinate(index, 0)

    @work(thread=True, exclusive=True)
    async def expand_array_job(self, index: int):
        job = self.get_job_by_row(index)

        child_jobs = natsorted(get_array_child_jobs(self.app.batch_client, job.job), key=lambda x: x["jobId"])

        self.jobs = (
            self.jobs[: index + 1]
            + [JobRecord(job=child_job, selected=False, is_array_job=True, parent_job=job) for child_job in child_jobs]
            + self.jobs[index + 1 :]
        )
        self.jobs[index].is_expanded = True

        self.redraw_rows()
        self.cursor_coordinate = Coordinate(index, 0)
        self.app.notify(f"Array job {job.job['jobName']} expanded.", severity="information")

    # # This is usually not desirable because it's too easy to accidentally select a row
    # def on_data_table_row_selected(self, event: DataTable.RowSelected):
    #     self.toggle_selected(event.cursor_row)

    def select_all(self):
        for job in self.jobs:
            if self.job_should_be_visible(job.job):
                job.selected = True

        self.redraw_rows()

    def clear_selection(self):
        for job in self.jobs:
            job.selected = False

        self.redraw_rows()

    @inject_highlighted_job
    def view_job_details(self, job_record: JobRecord, index: int):
        job_details = get_jobs_details(self.app.batch_client, [job_record.job["jobArn"]])[0]
        serialized_details = json.dumps(job_details, ensure_ascii=False, indent=4)
        self.app.push_screen(ViewTextScreen(serialized_details, language="json"))

    @inject_highlighted_job
    def view_job_logs(self, job_record: JobRecord, index: int):
        job_details = get_jobs_details(self.app.batch_client, [job_record.job["jobArn"]])[0]
        job_name = job_details["jobName"]
        log_stream_name = get_log_stream_name(job_details)

        if log_stream_name:
            self.app.push_screen(
                ViewTextScreenWithSaveButton(
                    text_generator_fn=lambda: get_log_events(log_stream_name),
                    default_file_name=f"{job_name}.log",
                )
            )
        elif job_record.is_array_job and not job_record.parent_job:
            # this is a parent array job
            self.app.notify("Log stream not available for array jobs", severity="warning")
        else:
            self.app.notify("No logs available", severity="warning")

    def refresh_jobs(self):
        if not self.loading:
            self.loading = True
            # the exclusive flag doesn't really work for some reason so we "lock" by checking the loading flag
            self.update()

    def _get_selected_jobs(self, select_highlighted=False):
        selected_jobs = [job.job for job in self.jobs if job.selected and self.job_should_be_visible(job.job)]
        if not selected_jobs:
            if self.row_count > 0 and self.cursor_row is not None and select_highlighted:
                highlighted_job = self.get_job_by_row(self.cursor_row)
                highlighted_job.selected = True
                self.redraw_rows()
                selected_jobs = [highlighted_job.job]
            else:
                self.app.notify("No jobs selected", severity="warning")
                return None
        return selected_jobs

    def kill_selected_jobs(self):
        selected_jobs = self._get_selected_jobs(select_highlighted=True)
        if selected_jobs is None:
            return

        def run_kill_jobs():
            self.run_worker(kill_jobs(self.app.batch_client, [job["jobId"] for job in selected_jobs]), thread=True)
            self.refresh_jobs()

        self.app.push_screen(
            ConfirmationScreen(
                f"Kill {len(selected_jobs)} selected jobs?",
                run_kill_jobs,
                selected_jobs,
            )
        )

    def clone_selected_jobs(self):
        self.app.notify("Cloning jobs is not yet supported", severity="warning")

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected):
        # sort by column that was clicked
        sort_keys = dict(enumerate(["selected", "jobName", "jobId", "createdAt", "status"]))
        sort_key = sort_keys[event.column_index]

        if sort_key == "selected":
            return  # not supported for now

        if self.sorted_by == sort_key:
            self.sort_reversed = not self.sort_reversed
        else:
            self.sorted_by = sort_key
            self.sort_reversed = False

        self.jobs.sort(key=lambda x: x.job[sort_key], reverse=self.sort_reversed)
        self.redraw_rows()

    def update_filter_settings(self, filter_settings: FilterSettings):
        self.filter_settings = filter_settings
        self.redraw_rows()
