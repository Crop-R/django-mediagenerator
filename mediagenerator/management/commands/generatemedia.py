from ...api import generate_media, prepare_media
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Combines and compresses your media files and saves them in _generated_media.'

    requires_model_validation = False

    def handle(self, *args, **options):
        prepare_media()
        generate_media()
