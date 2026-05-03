"""Management command to seed known IPSO narratives from JSON."""
import json
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.core.models import KnownNarrative

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seed known IPSO narratives from data/narratives/known_narratives.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing narratives before seeding',
        )
        parser.add_argument(
            '--compute-embeddings',
            action='store_true',
            help='Compute embeddings for narrative example texts',
        )

    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parent.parent.parent.parent.parent / \
            'data' / 'narratives' / 'known_narratives.json'

        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {data_path}'))
            return

        with open(data_path, 'r', encoding='utf-8') as f:
            narratives_data = json.load(f)

        if options['clear']:
            deleted_count, _ = KnownNarrative.objects.all().delete()
            self.stdout.write(f'Cleared {deleted_count} existing narratives.')

        created = 0
        for item in narratives_data:
            obj, was_created = KnownNarrative.objects.get_or_create(
                title=item['title'],
                defaults={
                    'description': item['description'],
                    'category': item['category'],
                    'example_texts': item.get('example_texts', []),
                    'source': item.get('source', ''),
                    'is_active': True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} new narratives (total: {KnownNarrative.objects.count()}).'
        ))

        # Optionally compute embeddings
        if options['compute_embeddings']:
            self._compute_embeddings()

    def _compute_embeddings(self):
        """Compute and store embeddings for all active narratives."""
        from apps.analyzer.similarity import compute_embedding

        narratives = KnownNarrative.objects.filter(is_active=True)
        updated = 0

        for narrative in narratives:
            # Combine title + description + examples for embedding
            text_parts = [narrative.title, narrative.description]
            text_parts.extend(narrative.example_texts[:3])
            combined_text = ' '.join(text_parts)

            embedding = compute_embedding(combined_text)
            if embedding:
                narrative.embedding = embedding
                narrative.save(update_fields=['embedding'])
                updated += 1
                self.stdout.write(f'  Embedding computed for: {narrative.title}')

        self.stdout.write(self.style.SUCCESS(
            f'Computed embeddings for {updated} narratives.'
        ))
