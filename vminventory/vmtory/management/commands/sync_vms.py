from django.core.management.base import BaseCommand
from vmtory.models import ESXi, VM
import pyVmomi
import requests
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

if settings.DEBUG:
    logger.setLevel(logging.DEBUG)

logger.debug("Usando configuracion: %s" % settings)

class Command(BaseCommand):
    args = '<none>'
    help = 'Sincroniza las VMs de cada ESXi cargado en el sistema.'

    def handle(self, *args, **options):
        for esxi in ESXi.objects.filter(enable=True):
            esxi.sync_vms()

