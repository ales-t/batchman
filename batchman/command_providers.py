from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from batchman.lib.batch import get_job_queue_names, get_region_names


class BaseSelectCommand(Provider):
    eager = False

    @property
    def fetch_fn(self):
        raise NotImplementedError()

    @property
    def set_fn(self):
        raise NotImplementedError()

    @property
    def help_text(self):
        raise NotImplementedError()

    async def startup(self) -> None:
        worker = self.app.run_worker(self.fetch_fn, thread=True)
        self.item_names = await worker.wait()

    async def discover(self):
        if self.eager:
            for queue_name in self.item_names:
                yield DiscoveryHit(queue_name, partial(self.set_fn, queue_name))

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        for item_name in self.item_names:
            command = item_name
            score = matcher.match(command)

            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(command),
                    partial(self.set_fn, item_name),
                    help=self.help_text,
                )


class SelectJobQueueCommand(BaseSelectCommand):
    @property
    def fetch_fn(self):
        return lambda: get_job_queue_names(self.app.batch_client)

    @property
    def set_fn(self):
        return self.app.set_job_queue

    @property
    def help_text(self):
        return "Change job queue"


class SelectRegionCommand(BaseSelectCommand):
    @property
    def fetch_fn(self):
        return get_region_names

    @property
    def set_fn(self):
        return self.app.set_region

    @property
    def help_text(self):
        return "Change region"


class EagerSelectRegionCommand(SelectRegionCommand):
    eager = True


class EagerSelectJobQueueCommand(SelectJobQueueCommand):
    eager = True
