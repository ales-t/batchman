import boto3
import botocore.exceptions
import itertools
from joblib import Parallel, delayed


class UnauthorizedError(Exception): ...


def batches(data_set, batch_size: int):
    """A generator which yields batches from the data set. When end of data
    set is reached, the batch may be truncated.

    Args:
        batch_size: number of elements per batch
        data_set: Which data set to read.

    Returns:
        Lists of instances.
    """
    if batch_size <= 0:
        yield list(data_set)  # no batching
        return

    out = []
    for item in data_set:
        out.append(item)
        if len(out) == batch_size:
            yield out
            out = []

    if out:
        yield out  # last truncated batch


def flatten(lst: list[list]) -> list:
    """Flatten a list."""
    return list(itertools.chain.from_iterable(lst))


def get_log_events(log_stream_name: str):
    client = boto3.client("logs")
    next_token = None

    while True:
        extra_args = {"nextToken": next_token} if next_token else {"startFromHead": True}
        reponse = client.get_log_events(
            logGroupName="/aws/batch/job",
            logStreamName=log_stream_name,
            **extra_args,
        )

        if not reponse["events"]:
            break

        for event in reponse["events"]:
            yield event["message"]

        next_token = reponse.get("nextForwardToken")


def get_log_stream_name(job_details: dict) -> str | None:
    return job_details["container"].get("logStreamName")


def get_array_child_jobs(client: boto3.client, parent_job: dict | None = None) -> list[dict]:
    all_states = ["SUCCEEDED", "FAILED", "RUNNABLE", "RUNNING", "PENDING", "STARTING"]
    for status in all_states:
        query_params = {"arrayJobId": parent_job["jobArn"], "jobStatus": status}
        yield from execute_paginated_job_query(client, query_params)


def get_jobs(client: boto3.client, queue_name: str):
    query_params = {"jobQueue": queue_name, "filters": [{"name": "AFTER_CREATED_AT", "values": ["0"]}]}
    yield from execute_paginated_job_query(client, query_params)


def execute_paginated_job_query(client: boto3.client, query_params: dict):
    while True:
        try:
            response = client.list_jobs(**query_params)
        except botocore.exceptions.UnauthorizedSSOTokenError:
            raise UnauthorizedError()
        except Exception:
            raise  # explicit re-raise

        for job in response["jobSummaryList"]:
            yield job

        if "nextToken" in response:
            query_params["nextToken"] = response["nextToken"]
        else:
            break


def get_jobs_details(client: boto3.client, job_arns: list[str]) -> list[dict]:
    # fetch details in parallel
    jobs_details = Parallel()(
        delayed(client.describe_jobs)(jobs=batch) for batch in batches((j for j in job_arns), 100)
    )

    jobs_details = flatten([response["jobs"] for response in jobs_details])
    return jobs_details


def get_job_queues(client: boto3.client) -> list[dict]:
    return client.describe_job_queues()["jobQueues"]


def get_job_queue_names(client: boto3.client) -> list[str]:
    return [queue["jobQueueName"] for queue in get_job_queues(client)]


def get_region_names() -> list[str]:
    client = boto3.client("ec2")
    return [region["RegionName"] for region in client.describe_regions()["Regions"]]
