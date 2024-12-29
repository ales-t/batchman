from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from batchman.lib.batch import get_job_queue_names, get_region_names


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
