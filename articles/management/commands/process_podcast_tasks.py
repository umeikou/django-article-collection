import time
import uuid
from django.core.management.base import BaseCommand
from articles.podcast import PodcastWorker


class Command(BaseCommand):
    help = 'Process one SQLite-safe Xiaoyuzhou podcast task at a time.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--worker-id', default='')
        parser.add_argument('--max-tasks', type=int, default=0)

    def handle(self, *args, **options):
        if not options['once'] and not options['loop']:
            options['once'] = True
        worker = PodcastWorker(options['worker_id'] or f'podcast-{uuid.uuid4().hex[:12]}')
        completed = 0
        while True:
            task = worker.claim()
            if task:
                worker.process(task)
                completed += 1
                if options['once'] or (options['max_tasks'] and completed >= options['max_tasks']):
                    return
            elif options['once'] or (options['max_tasks'] and completed >= options['max_tasks']):
                return
            else:
                time.sleep(5)
