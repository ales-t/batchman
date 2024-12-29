batchman -- AWS Batch job explorer and manager
==============================================

Batchman is a Textual-based terminal UI (TUI) application for exploring and managing AWS Batch jobs. It allows you to list jobs in a selected queue, view job details, expand array jobs, inspect logs, and filter jobs by name or status—all within your terminal.

## Features

* **List jobs in an AWS Batch queue**
    Display all jobs in the configured AWS Batch queue and region.

* **Filter & search**
    Filter jobs by name prefix and/or status (submitted, runnable, running, succeeded, failed, etc.).

* **Array job support**
    Expand or collapse array jobs to see and manage individual child jobs.

* **View job details**
    Inspect job definitions, environment variables, and other metadata.

* **View logs**
    Quickly stream job logs from CloudWatch Logs.

* **Job selection**
    Easily select, unselect, or clear all selections for bulk management.

* **Job termination and cloning**
    `TODO`

## Installation

```sh
git clone https://github.com/ales-t/batchman.git
cd batchman
# Option 1: pip install in editable mode
pip install -e .
# Option 2: or just run it directly (assuming dependencies installed)
python -m batchman.main
```

## Configuration

Upon first run, Batchman creates or updates a config file in `~/.batchman.yml`. You can manually edit this file to set defaults:

```yaml
job_queue_name: "my-default-queue"
region: "us-east-1"
theme: "textual-light"
display_filter: true
```

## Usage

Launch Batchman in your terminal:

```sh
batchman
```

(or `python batchman/main.py` if you installed from source without a script).

## Keyboard Shortcuts

* `a` – Select all jobs
* `d` – View job details
* `e` – Toggle expand/collapse of array jobs
* `l` – View logs
* `r` – Refresh job list
* `q` – Quit
* `space` – Toggle selection for the highlighted row
* `x` – Clear selection
* `c`, `Ctrl+C` – Copy selected text to clipboard (in job logs, details)

## Changing Queue or Region

Press `Ctrl+P` (default CommandPalette key in Textual) or run the built-in "Change queue" / "Change region" commands. Or open the command palette to search for change queue or change region.

## License

This project is provided under the Apache 2.0 License. See `LICENSE` for details.