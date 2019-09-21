from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import datetime
from pyVim import connect
import pyVmomi
import atexit
import requests
import logging
# Modificamos SSL para que no valide el certificado de los ESXi.
import ssl
# Disabling SSL certificate verification
context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
context.verify_mode = ssl.CERT_NONE

logger = logging.getLogger(__name__)
if settings.DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    logger.format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'


class Location(models.Model):
    name = models.CharField(_('Name'), max_length=200)

    def __str__(self):
        return u'%s' % (self.name)    

class ESXi(models.Model):
    name = models.CharField(_('Name'), max_length=200)
    hostname = models.CharField(_('Hostname'), max_length=200)
    user = models.CharField(_('User'), max_length=200, default='root')
    password = models.CharField(_('Password'), max_length=200)
    tooltip = models.CharField(_('Tooltip'), max_length=200, blank=True)
    port = models.IntegerField(_('Port'), default=443)
    enable = models.BooleanField(_('Enabled'), default=True)
    location = models.ForeignKey(Location, default='', blank=True)

    class Meta:
        verbose_name = 'ESXi'
        verbose_name_plural = "ESXis"

    def __str__(self):
        return u'%s' % (self.name)

    def connect(self):
        # try:
        service_instance = connect.SmartConnect(host=self.hostname,
                                                user=self.user,
                                                pwd=self.password,
                                                port=int(self.port),
                                                sslContext=context,
                                                )
        return 0, service_instance

    def get_all_vms(self):
        result, service_instance = self.connect()
        logger.debug("Connection with %s resulted in: %s" % (self.name, result))
        if result == 0:
            atexit.register(connect.Disconnect, service_instance)
            content = service_instance.RetrieveContent()
            logger.debug("Content: %s" % content)
            try:
                children = content.rootFolder.childEntity
                logger.debug("Children: %s" % children)
            except:
                logger.warning("Can't get information of the VM %s" % self.name)
                return 2, "Can't get information of the VM %" % self.name
            for child in children:
                if hasattr(child, 'vmFolder'):
                    datacenter = child
                    logger.debug("Using datacenter: %s" % datacenter)
                else:
                    # some other non-datacenter type object
                    continue

                vm_folder = datacenter.vmFolder
                logger.debug("VM Folder: %s" % vm_folder)
                logger.debug("VM Folder: %s" % vm_folder)
                vm_list = vm_folder.childEntity
                logger.debug("Child Entity: %s" % vm_list)
                logger.debug("Child Entity: %s" % vm_list)
        else:
            return result, service_instance
        return 0, vm_list

    def get_vm_by_uuid(self, uuid):
        result, service_instance = self.connect()
        if result == 0:
            atexit.register(connect.Disconnect, service_instance)
            content = service_instance.RetrieveContent()
            try:
                logger.debug('Searching VM with UUID %s' % uuid)
                # Workaround because vcsim doesn't implement FindAllbyUuid
                if content.about.name == 'VMware ESXi (govmomi simulator)':
                    vm_list = [content.searchIndex.FindByUuid(uuid=uuid, vmSearch=True)]
                else:
                    vm_list = content.searchIndex.FindAllByUuid(uuid=uuid, vmSearch=True)
                logger.debug(vm_list)
            except:
                logger.debug('Can not find VM with UUID %s' % uuid)
                return 404, []
        else:
            return result, service_instance
        return 0, vm_list

    def get_vm(self, vm_db):
        # maxdepth = 10
        result, vm_list = self.get_vm_by_uuid(vm_db.uuid)
        if len(vm_list)>1:
            logger.warning("Found more than 1 VM with UUID %s while searching: %s" % (vm_db.uuid, vm_db))
        if result == 0:
            for vm in vm_list:
                if vm.summary.config.instanceUuid == vm_db.iuuid and vm.summary.config.uuid == vm_db.uuid:
                    config = vm.summary.config
                    runtime = vm.summary.runtime
                    guest = vm.summary.guest
                    storage = vm.summary.storage
                    snapshots = vm.snapshot
                    uptime = vm.summary.quickStats.uptimeSeconds

                    newvm = VM(hypervisor=self,
                               uuid=config.uuid,
                               name=config.name,
                               path=config.vmPathName,
                               guest=config.guestFullName,
                               cpus=config.numCpu,
                               ram=config.memorySizeMB,
                               annotation=config.annotation,
                               uptime=uptime,
                               state=True if runtime.powerState == 'poweredOn' else False,
                               )
                    if storage:
                        capacity = []
                        for device in vm.config.hardware.device:
                            if isinstance(device, pyVmomi.vim.vm.device.VirtualDisk):
                                capacity.append('1x%.2f GB' % (device.capacityInKB / 1024 / 1024))
                        newvm.hdds = '%s (%s)' % (config.numVirtualDisks, ' | '.join(capacity))
                    else:
                        newvm.hdds = config.numVirtualDisks
                    if guest is not None:
                        if guest.ipAddress:
                            newvm.ip_address = guest.ipAddress

                    if vm.guest.net:
                        ips = []
                        for nic in vm.guest.net:
                            if nic.ipConfig:
                                addresses = nic.ipConfig.ipAddress
                                for addr in addresses:
                                    ips.append('%s/%s' % (addr.ipAddress, addr.prefixLength))
                        newvm.networking = '\n'.join(ips)

                    if snapshots is not None:
                        newvm.snapshots = snapshots.rootSnapshotList
                        newvm.currentSnapshot = snapshots.currentSnapshot
                        for snapshot in newvm.snapshots:
                            snaps_plain = (self.get_snapshots_plain(snapshot))
                    else:
                        newvm.snapshots = []
                        snaps_plain = []
                    if newvm.state and not vm_db.state:
                        logger.debug('[%s] %s: updating the timestamp of last time seen powered_on' % (vm_db.hypervisor.name, vm_db.id))
                        vm_db.last_poweron = newvm.last_poweron = timezone.now()
                    vm_db.state = newvm.state
                    vm_db.save()
                    return 0, newvm, snaps_plain
        logger.error('VM not found while searching for %s' % vm_db)
        return 404, 'NOT FOUND', 'NA'

    def get_snapshots_plain(self, snapshot):
        snapinfo = []
        snapinfo += [{'id': snapshot.id,
                      'snapshot': snapshot.snapshot,
                      'createTime': snapshot.createTime,
                      'name': snapshot.name,
                      'description': snapshot.description
                      }]
        if snapshot.childSnapshotList is not None:
            for snapshot2 in snapshot.childSnapshotList:
                    snapinfo += self.get_snapshots_plain(snapshot2)
        return snapinfo

    def get_vm_screenshot(self, vmid):
        """Devuelve una request con la captura de pantalla de la VM"""
        req = requests.get('https://%s:%s/screen?id=%s' % (self.hostname, self.port, vmid), auth=(self.user, self.password), verify=False)
        return req
    
    def sync_vms(self):
        """
        This is called every X minutes with a cron job ti syncronize the DB information with the current state of the VMs in the hypervisors.
        TODO: This repeats a lot of task than are done also in the get_vm() method. Unify code.
        """
        try:
            logger.debug("Getting VM list from %s" % self.name)
            code, vm_list = self.get_all_vms()
        except requests.exceptions.ConnectionError as e:
            logger.error('Unable to connect to %s (%s): %s' % (self.name, self.hostname, e))
            return
        if code == 0:
            for vm in vm_list:
                logger.debug("Processing VM: %s" % vm)
                config = vm.summary.config
                runtime = vm.summary.runtime
                guest = vm.summary.guest
                storage = vm.summary.storage
                snapshots = vm.snapshot
                uptime = vm.summary.quickStats.uptimeSeconds
                newvm = VM(hypervisor=self,
                            uuid=config.uuid,
                            iuuid=config.instanceUuid,
                            vmid=vm,
                            name=config.name,
                            path=config.vmPathName,
                            guest=config.guestFullName,
                            cpus=config.numCpu,
                            ram=config.memorySizeMB,
                            annotation=config.annotation or "",
                            uptime=uptime,
                            state=True if runtime.powerState == 'poweredOn' else False,
                            )
                if storage:
                    capacity = []
                    for device in vm.config.hardware.device:
                        if isinstance(device, pyVmomi.vim.vm.device.VirtualDisk):
                            capacity.append('1x%.2f GB' % (device.capacityInKB / 1024 / 1024))
                    newvm.hdds = '%s (%s)' % (config.numVirtualDisks, ' | '.join(capacity))
                else:
                    newvm.hdds = config.numVirtualDisks
                if guest is not None:
                    if guest.ipAddress:
                        newvm.ip_address = guest.ipAddress

                if vm.guest.net:
                    ips = []
                    for nic in vm.guest.net:
                        if nic.ipConfig:
                            addresses = nic.ipConfig.ipAddress
                            for addr in addresses:
                                ips.append('%s/%s' % (addr.ipAddress, addr.prefixLength))
                    newvm.networking = '\n'.join(ips)

                if snapshots is not None:
                    newvm.snapshots = snapshots.rootSnapshotList
                else:
                    newvm.snapshots = ''
                if newvm.uuid is None:
                    logger.debug('[SKIPPED] [%s] %s: %s' % (newvm.hypervisor.name, newvm.vmid, newvm.name))
                    continue
                if newvm.state:
                    newvm.last_poweron = timezone.now()
                if not VM.objects.filter(vmid=newvm.vmid, hypervisor=newvm.hypervisor):
                    logger.debug('[NEW] [%s] %s' % (newvm.hypervisor.name, newvm.name))
                    newvm.save()
                else:
                    oldvms = VM.objects.filter(vmid=newvm.vmid, hypervisor=newvm.hypervisor)
                    # actualizar la INFO de la VM.
                    if oldvms:
                        oldvm = oldvms[0]
                        oldvm_keep = (oldvm.id, oldvm.assignee, oldvm.group, oldvm.public, oldvm.deleted, oldvm.environment, oldvm.pending_poweron, oldvm.notes)
                        oldvm_ip_address = oldvm.ip_address
                        oldvm_networking = oldvm.networking
                        oldvm.__dict__ = newvm.__dict__.copy()
                        oldvm.id, oldvm.assignee, oldvm.group, oldvm.public, oldvm.deleted, oldvm.environment, oldvm.pending_poweron, oldvm.notes = oldvm_keep
                        if not newvm.ip_address:
                            oldvm.ip_address = oldvm_ip_address
                        if not newvm.networking:
                            oldvm.networking = oldvm_networking
                        if oldvm.pending_poweron == True and newvm.state == True:
                            oldvm.pending_poweron = False
                        if not oldvm.state and newvm.state:
                            oldvm.last_poweron = timezone.now()
                        oldvm.save()
                        logger.debug('[UPDATED] [%s] %s: %s' % (newvm.uuid, oldvm.id, newvm.name))
                    else:
                        logger.debug('[SKIPPED] [%s] UUID: %s - IUUID: %s - Name: %s' % (newvm.hypervisor.name, newvm.uuid, newvm.iuuid, newvm.name))
        else:
            logger.error('%s - %s' % (code, vm_list))

class Environment(models.Model):
    name = models.CharField(_('Name'), max_length=200)
    color = models.CharField(_('Color'), max_length=200)

    class Meta:
        verbose_name_plural = _('Environments')
    def __str__(self):
        return self.name


class VM(models.Model):
    hypervisor = models.ForeignKey(ESXi, default='', verbose_name='Hypervisor')
    uuid = models.CharField('UUID', max_length=200, default='', blank=True)
    iuuid = models.CharField('Instance UUID', max_length=200, default='', blank=True)
    vmid = models.CharField('VMid', max_length=200, default='', blank=True)
    public = models.BooleanField(_('Public VM'), default=True, help_text=_("VMs with 'Public VM' field set to false are not visible to users, even in searches."))
    deleted = models.BooleanField(_('Deleted VM'), default=False)
    pending_poweron = models.BooleanField(_('Power on requested'), default=False, blank=True)
    name = models.CharField(_('Name'), max_length=200, default='')
    path = models.CharField(_('Path'), max_length=200, default='')
    guest = models.CharField(_('Operating System'), max_length=200, default='')
    annotation = models.TextField(_('Annotation'), default='', blank=True)
    notes = models.TextField(_('Personal Notes'), default='', blank=True)
    state = models.BooleanField(_('State'), help_text=_('Green: On, Red: Off'), default=False)
    ip_address = models.GenericIPAddressField(_('IP Address'), protocol='IPv4', null=True, blank=True)
    networking = models.TextField(_('Networking'), default='', blank=True)
    cpus = models.IntegerField(_('vCPUs'), default=0)
    ram = models.IntegerField(_('vRAM'), default=0)
    hdds = models.CharField(_('HDDs'), max_length=200, default='')
    assignee = models.ForeignKey(User, verbose_name=_('Assigned to'), blank=True, null=True)
    group = models.ForeignKey(Group, verbose_name=_('Group'), blank=True, null=True)
    last_update = models.DateTimeField(_('Last Check'), auto_now=True)
    favorites = models.ManyToManyField(User, related_name='favorite_vm', blank=True)
    uptime = models.IntegerField(_('Uptime'), null=True, blank=True)
    last_poweron = models.DateTimeField(_('Last time seen ON'), null=True, blank=True)
    environment = models.ForeignKey(Environment, default='', verbose_name=_('Environment'), blank=True, null=True)

    class Meta:
        verbose_name = _('VM')
        verbose_name_plural = _("VMs")

    def ramh(self):
        if self.ram % 1024 == 0 and self.ram >= 1024:
            ramh = str(int(self.ram / 1024)) + ' GB'
        else:
            ramh = str(self.ram) + ' MB'
        return ramh

    def known_state(self):
        unkown_message = _("State unknown. It's been +3 checks since the last time we saw the VM. Is the Server unreachable? Last time seen, the VM was %s.") % (_('powered on') if self.state else _('powered off'))
        return((timezone.now() - self.last_update) < datetime.timedelta(minutes=15), unkown_message)

    def uptimef(self):
        """Devuelve el uptime formateado"""
        if self.uptime:
            return datetime.timedelta(seconds=self.uptime)
        else:
            return None

    def esxi_id(self):
        """Devuelve el ID de ESXi de la VM"""
        return self.vmid.replace("'", '').split(':')[-1]

    def __str__(self):
        return u'<%s> [%s] %s' % (self.id, self.hypervisor.name, self.name)


class OS(models.Model):
    os_family = models.CharField(_('Family'), max_length=200)
    os_version = models.CharField(_('Version'), max_length=200)
    os_arch = models.CharField(_('Architecture'), max_length=200)

    class Meta:
        verbose_name = _('OS')
        verbose_name_plural = _("OS")

    def __str__(self):
        return u'%s %s %s' % (self.os_family, self.os_version, self.os_arch)


class ReservedIPAddress(models.Model):
    ip_address = models.GenericIPAddressField(_('IP Address'))
    network_mask = models.CharField(_('Network mask'), default='24', max_length=15)
    assignee = models.ForeignKey(User, verbose_name=_('Assigned to'), blank=True, null=True)
    observations = models.TextField(_('Observations'), default='')

    class Meta:
        verbose_name = _('Reserved IP')
        verbose_name_plural = _('Reserved IPs')
        unique_together = ('ip_address', 'network_mask',)

    def __str__(self):
        return u'%s/%s' % (self.hostname_address, self.network_mask)
