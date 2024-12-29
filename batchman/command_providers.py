from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from batchman.lib.batch import get_job_queue_names, get_region_names


class BaseSelectCommand(Provider):
    def __init__(self, *args, set_selected, help_str, item_getter, eager=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_getter = item_getter
        self.set_selected = set_selected
        self.help = help_str
        self.eager = eager

    async def startup(self):
        worker = self.app.run_worker(self.item_getter, thread=True)
        self.items = await worker.wait()

    async def discover(self):
        if self.eager:
            for item in self.items:
                yield DiscoveryHit(item, partial(self.set_selected, item))

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        for item in self.items:
            command = item
            score = matcher.match(command)

            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(command),
                    partial(self.set_selected, item),
                    help=self.help,
                )


class SelectJobQueueCommand(BaseSelectCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            help_str="Change job queue",
            set_selected=lambda x: self.app.set_job_queue(x),
            item_getter=lambda: get_job_queue_names(self.app.batch_client),
            **kwargs,
        )


class SelectRegionCommand(BaseSelectCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            item_getter=get_region_names,
            set_selected=lambda x: self.app.set_region(x),
            help_str="Change region",
            **kwargs,
        )


class EagerSelectRegionCommand(SelectRegionCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, eager=True, **kwargs)


class EagerSelectJobQueueCommand(SelectJobQueueCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, eager=True, **kwargs)
