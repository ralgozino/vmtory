# *-* encoding: utf-8 *-*

"""
VMtory Views definition
"""

from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.db.models import Q, Sum, Count
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings

from django_tables2 import RequestConfig


from vmtory.models import ESXi, VM, ReservedIPAddress, Environment
from vmtory.form_models import NewVMForm, DuplicateVMForm, NewSnapshotForm, AdvancedSearchForm, ConfirmDeleteForm, BackupVMForm, ModifyVMForm
from vmtory.tables import VMTable, GroupVMTable, AllVMTable, DeletedVMTable, AdvancedSearchVMTable, Top10Table
from vmtory.itop_api import create_ticket


import re
import json
from collections import OrderedDict
import ipaddress
from requests.exceptions import ConnectionError
import logging

logger = logging.getLogger(__name__)

if settings.DEBUG:
    logger.setLevel(logging.DEBUG)


def index(request):
    """
    Welcome page
    """

    vms_count = VM.objects.filter(deleted=False).count() or 0
    vms_count_online = VM.objects.filter(deleted=False, state=True).count() or 0
    hypervisors_count = ESXi.objects.filter(enable=True).count() or 0
    ram_count = round(VM.objects.filter(deleted=False).aggregate(Sum('ram'))['ram__sum'] or 0 /1024)
    cpus_count = VM.objects.filter(deleted=False).aggregate(Sum('cpus'))['cpus__sum'] or 0

    return render(request, "index.html", {'page_title': 'Inicio', 'vms_count': vms_count, 'vms_count_online': vms_count_online, 'ram_count': ram_count, 'cpus_count': cpus_count,'hypervisors_count': hypervisors_count})


@login_required
def allvms(request):
    """
    This view shows all the vms loaded in the database. Should
    available only to users marked as staff members.
    """
    if request.user.is_staff:
        q = VM.objects.filter(deleted=False)
        q_deleted = VM.objects.filter(deleted=True)
        table = AllVMTable(q)
        table.prefix = 'active_vms'
        table_deleted = AllVMTable(q_deleted)
        table_deleted.prefix = 'deleted_vms'
        RequestConfig(request).configure(table)
        RequestConfig(request).configure(table_deleted)
        return render(request, "all_vms.html",
                      {"vms": table,
                       'viewfilter': 'all',
                       'deleted_vms': table_deleted,
                       'page_title': _('All VMs')
                      }
                     )
    else:
        return render(request,
                      "no_permission.html",
                      {'viewfilter': 'all',
                       'page_title': _('Permissions Error'),
                       'error_description': _('Only STAFF members can see all the VMs.'),
                      }
                     )


@login_required
def myvms(request):
    table = table_deleted = favs_table = None
    q = VM.objects.filter(assignee=request.user.id, deleted=False).order_by('name')
    q2 = VM.objects.filter(assignee=request.user.id, deleted=True).order_by('name')
    favs_vms = VM.objects.filter(favorites=request.user)

    if favs_vms:
        favs_table = VMTable(favs_vms, request=request)
        favs_table.prefix = 'favs_vms'
        RequestConfig(request).configure(favs_table)
    if q:
        table = VMTable(q, request=request)
        table.prefix = 'active_vms'
        RequestConfig(request).configure(table)
    if q2:
        table_deleted = DeletedVMTable(q2)
        table_deleted.prefix = 'deleted_vms'
        RequestConfig(request).configure(table_deleted)
    return render(request, 'myvms.html', {'favs': favs_table, 'vms': table, 'deleted_vms': table_deleted, 'viewfilter': 'myvms', 'page_title': _('My VMs')})


@login_required
def groupvms(request):
    grupos = request.user.groups.all()
    if grupos:
        grupos_vms = {}
        for group in request.user.groups.all():
            table = None
            q = VM.objects.filter(group=group, deleted=False).order_by('name')
            if q:
                table = GroupVMTable(q, request=request)
                table.prefix = group
                RequestConfig(request).configure(table)
            grupos_vms[group] = table

        return render(request, 'groupvms.html', {'grupos_vms': grupos_vms, 'page_title': _("My Groups' VMs")})
    else:
        return render(request, 'groupvms.html', {'page_title': _("My Groups' VMs")})


@login_required
def newvm(request):
    if request.method == 'POST':
        form = NewVMForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = {'username': request.user.username, 'description': ''}
            ticket['title'] = "[" + str(form.cleaned_data['location']) + str(_("][VM][CREATE] ")) + form.cleaned_data['vmname']
            for field in form:
                 ticket['description'] += "<p>" + str(field.label) + ": " + str(form.cleaned_data[field.name]) + '</p>\n'
            result = notify(ticket)
            return render(request, "result_ok.html", {"mensaje": _("Request succesfully sent! You'll receive an email with the request confirmation."), "result": result, "datosvm": form, 'page_title': _('New VM request')})
        else:
            return render(request, "newvm.html", {"form": form, 'page_title': _('New VM request')})
    else:
        return render(request, "newvm.html", {"form": NewVMForm(user=request.user), 'page_title': _('New VM request')})


@login_required
def esxi(request):
    if request.user.is_staff:
        return render(request, "esxi.html", {"esxi": ESXi.objects.all(), 'page_title': _('Hypervisors')})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'esxi', 'page_title': _('Permissions error')})


@login_required
def vm_screenshot(request, vm_id):
    vm_db = VM.objects.get(id=vm_id)

    if request.user.groups.filter(name=vm_db.group or '') or request.user.is_staff or vm_db.assignee == request.user:
        screenshot = vm_db.hypervisor.get_vm_screenshot(vm_db.esxi_id())
        if screenshot.ok:
            return HttpResponse(screenshot.content, content_type='image/png')
        else:
            return HttpResponseForbidden()
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("You don't have permissions to see this VM's details.")})


@login_required
def vm_details(request, vm_id):
    vm_db = VM.objects.get(id=vm_id)

    if request.user.groups.filter(name=vm_db.group or '') or request.user.is_staff or vm_db.assignee == request.user:

        if request.method == 'POST':
            form = NewSnapshotForm(request.POST)
            if form.is_valid():
                ticket = {
                    'username': request.user.username,
                    'title': '[' + str(vm_db.hypervisor.location) + str(_('][SNAPSHOT][CREATE] ')) + vm_db.name + ' - "' + form.cleaned_data['snap_name'] + '"',
                    'description': _('<p><strong>CREATE SNAPSHOT:</strong></p> \
                                    <p>Hypervisor: %s</p> \
                                    <p>VM Name: %s</p>\
                                    <p>VMtory ID: %s</p>\
                                    <p>ID VM ESXi:%s</p> \
                                    <p>Snapshot name: %s</p>\
                                    <p>Description:</p><pre>%s</pre>' \
                                    % (vm_db.hypervisor.name,
                                       vm_db.name,
                                       vm_db.id,
                                       vm_db.esxi_id(),
                                       form.cleaned_data['snap_name'],
                                       form.cleaned_data['snap_desc']
                                       )
                                    ),
                    'subcategory': '%s' % settings.ITOP_CATEGORIES.get('SNAPSHOT_CREATE'),
                }
                result = notify(ticket)
                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
        else:
            form = NewSnapshotForm

        try:
            hv = ESXi.objects.filter(enable=True, id=vm_db.hypervisor.id)[0]
            code, newvm, snapshots_dict = hv.get_vm(vm_db)
        except ConnectionError:
            code = -10
            snapshots_dict = {}
        if code == 0:
            try:
                return render(request, 'vmdetails.html', {'vm_db': vm_db, 'vm': newvm, 'snapshots': snapshots_dict, 'form': form, 'page_title': 'Detalles de %s' % newvm.name})
            except UnboundLocalError:
                return render(request, 'vmdetails.html', {'vm_db': vm_db, 'vm': vm_db, 'snapshots': '', 'page_title': 'Detalles de %s' % vm_db.name})
        else:
            return render(request, 'vmdetails.html', {'vm_db': vm_db, 'vm': vm_db, 'snapshots': '', 'page_title': 'Detalles de %s' % vm_db.name, 'esxi_error': True})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': 'Error de permisos', 'error_description': 'No tiene permisos para ver los detalles de esta VM.'})


@login_required
def advsearch(request):
    form = AdvancedSearchForm(request.GET)
    if form.is_valid():
        name = Q(name__icontains=form.cleaned_data['name']) if form.cleaned_data['name'] else Q()
        users = Q(assignee__in=form.cleaned_data['assignee']) if form.cleaned_data['assignee'] else Q()
        groups = Q(group__in=form.cleaned_data['group']) if form.cleaned_data['group'] else Q()
        hypervisores = Q(hypervisor__in=form.cleaned_data['hypervisor']) if form.cleaned_data['hypervisor'] else Q()
        ip = Q(ip_address__icontains=form.cleaned_data['ip_address']) | Q(networking__icontains=form.cleaned_data['ip_address']) if form.cleaned_data['ip_address'] else Q()
        annotation = Q(annotation__icontains=form.cleaned_data['annotation']) if form.cleaned_data['annotation'] else Q()
        enviroment = Q(environment__in=form.cleaned_data['enviroment']) if form.cleaned_data['enviroment'] else Q()
        include_deleted = Q(deleted=False) if not form.cleaned_data['include_deleted'] else Q()
        table = ''
        if form.has_changed():
            found_entries = VM.objects.filter(Q(public=True) & name & include_deleted & hypervisores & users & groups & annotation & ip & enviroment)
            table = AdvancedSearchVMTable(found_entries)
            RequestConfig(request).configure(table)
        return render(request, "advancedsearch.html", {"form": form, "vms": table, 'viewfilter': 'advsearch', 'page_title': _('Advanced search')})
    else:
        return render(request, "advancedsearch.html", {"form": form, 'page_title': _('Advanced search')})


@login_required
def search(request):
    query_string = ''
    ip_address = ''
    found_entries = None
    if ('q' in request.GET) and request.GET['q'].strip():
        query_string = request.GET['q']

        entry_query = get_query(query_string, [
                                               'id',
                                               'name',
                                               'ip_address',
                                               'annotation',
                                               'networking'
                                               ])

        found_entries = VM.objects.filter(entry_query).order_by('name')
        if not request.user.is_staff:
            found_entries = found_entries.filter(Q(public=True) & Q(assignee=request.user.id) | Q(group__in=request.user.groups.all()) & Q(deleted=False))
    elif ('ip' in request.GET) and request.GET['ip'].strip():
        ip_address = request.GET['ip']

        found_entries = VM.objects.filter(ip_address=ip_address)
        if not request.user.is_staff:
            found_entries = found_entries.filter(Q(public=True) & Q(assignee=request.user.id) | Q(group__in=request.user.groups.all()) & Q(deleted=False))
    else:
        return render(request, "all_vms.html", {'viewfilter': 'advsearch', 'page_title': _('Search "%s"') % ((query_string or ip_address) or '')})

    table = AllVMTable(found_entries, request=request)
    RequestConfig(request).configure(table)
    return render(request, "all_vms.html", {"vms": table, 'viewfilter': 'advsearch', 'page_title': _('Search "%s"') % ((query_string or ip_address) or '')})


def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:

        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]


def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.

    '''
    query = None  # Query to search for every search term
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None  # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query


@login_required
def snap_restore(request, vm_id, snap_id, snap_name):
    vm = VM.objects.get(id=vm_id)

    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        ticket = {
            'username': request.user.username,
            'title': '[' + str(form.cleaned_data['location']) + str(_('][SNAPSHOT][RESTORE] ')) + vm.name + ' - "' + snap_name + '"',
            'description': _('<p><strong>RESTORE SNAPSHOT</strong></p><p>Snapshot name: %s</p><p>Hypervisor: %s</p><p>VM name: %s</p><p>VMtory ID: %s</p><p>ESXi VM ID: %s</p><p>ESXi Snapshot ID: %s</p><p>Command:</p><pre>%s</pre>') % (snap_name, vm.hypervisor, vm.name, vm.id, vm.esxi_id(), snap_id, ' vim-cmd vmsvc/snapshot.revert ' + vm.esxi_id() + ' ' + snap_id + ' suppressPowerOff && vim-cmd vmsvc/power.on ' +  vm.esxi_id()),
            'subcategory': settings.ITOP_CATEGORIES.get('SNAPSHOT_RESTORE'),
        }
        result = notify(ticket)

        if result['code'] == 0:
            messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
        else:
            messages.error(request, str(result['code']) + ': ' + result['message'])
        return HttpResponseRedirect(reverse('result'))
    else:
        return render(request, "no_permission.html", {'viewfilter': 'vmdetails', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to restore snapshots on this VM.")})



@login_required
def snap_delete(request, vm_id, snap_id, snap_name):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        if request.method == 'POST':
            form = ConfirmDeleteForm(request.POST)
            if form.is_valid():
                ticket = {
                    'username': request.user.username,
                    'title': '[' + str(form.cleaned_data['location']) + str(_('][SNAPSHOT][DELETE] ')) + vm.name + ' - "' + snap_name + '"',
                    'description': _('<p><strong>DELETE SNAPSHOT</strong></p><p>Snapshot name: %s</p><p>Hypervisor: %s</p><p>VM name: %s</p><p>VMtory ID: %s</p><p>ESXi VM ID: %s</p><p>ESXi Snapshot ID: %s</p>') % (snap_name, vm.hypervisor, vm.name, vm.id, vm.esxi_id(), snap_id),
                    'subcategory': settings.ITOP_CATEGORIES.get('SNAPSHOT_DELETE'),
                }
                result = notify(ticket)

                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
        else:
            return render(request, "confirmation.html", {"form": ConfirmDeleteForm, 'page_title': _('Delete request confirmation'), 'name': 'Snaphost', 'message': -('Are yopu sure you want to delete the snapshot %s?') % snap_name})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'vmdetails', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to delete snapshots on this VM.")})


@login_required
def snap_take(request):
    if request.method == 'POST':
        form = NewSnapshotForm(request.POST)
        if form.is_valid():
            vm = VM.objects.get(id=form.cleaned_data['vm_id'])
            if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
                ticket = {
                    'username': request.user.username,
                    'title': '[' + str(form.cleaned_data['location']) + str(_('][SNAPSHOT][CREATE] ')) + vm.name,
                    'description': _('<p><strong>CREATE SNAPSHOT:</strong></p><p>Snapshot name: %s</p><p>Description:<br />%s</p><p>Link VM: %s</p>') % (form.cleaned_data['snap_name'], form.cleaned_data['snap_desc'], request.build_absolute_uri(reverse('vm_details', kwargs={'vm_id': vm.id}))),
                    'subcategory': settings.ITOP_CATEGORIES.get('SNAPSHOT_CREATE'),
                }
                result = notify(ticket)

                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
            else:
                return render(request, "no_permission.html", {'viewfilter': 'vmdetails', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to create snapshots on this VM.")})
        else:
            return render(request, "vmdetails.html", {"form": form, })
    else:
        return render(request, "newvm.html", {"form": NewVMForm, })


@login_required
def vm_delete(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if vm.assignee == request.user:
        if request.method == 'POST':
            form = ConfirmDeleteForm(request.POST)
            if form.is_valid():
                ticket = {
                    'title': '[' + str(vm.hypervisor.location) + str(_('][VM][DELETE] ')) + vm.name,
                    'username': request.user.username,
                    'description': _('<p><strong>DELETE VM</strong></p><p>Hypervisor: %s</p><p>VM Name: %s</p><p>VMtory ID: %s</p><p>ESXi VM ID: %s</p>') % (vm.hypervisor.name, vm.name, vm.id, vm.esxi_id()),
                    'subcategory': settings.ITOP_CATEGORIES.get('VM_DELETE_SUBCATEGORY'),
                }
                result = notify(ticket)
                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
        else:
            return render(request, "confirmation.html", {"form": ConfirmDeleteForm, 'page_title': _('Delete confirmation'), 'name': 'VM', 'message': _('Are you sure you want to delete the VM "%s"?') % vm.name})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Only the owner can delete a VM")})


@login_required
def vm_poweron(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        same_ip = VM.objects.filter(ip_address=vm.ip_address, environment=vm.environment, state=True, deleted=False).exclude(id=vm.id).exclude(ip_address=None)
        
        if same_ip.count() > 0:
            result = {"code": 403, "message": _("Can't send power on request due to another(s) VM(s) is(are) powered on and using the same IP right now:\n %s") % same_ip}
            messages.error(request, str(result['code']) + ': ' + result['message'])
            return HttpResponseRedirect(reverse('result'))
        
        if vm.state is False:
            if not vm.pending_poweron:
                ticket = {
                    'title': '[' + str(vm.hypervisor.location) + str(_('][VM][POWER ON] ')) + vm.name,
                    'username': request.user.username,
                    'description': _('<p><strong>POWER ON VM</strong></p><p>Hypervisor: %s</p><p>VM Name: %s</p><p>ID VMtory: %s</p><p>ESXi VM ID: %s</p><p>Command:</p><pre>vim-cmd vmsvc/power.on %s</pre>') % (vm.hypervisor.name, vm.name, vm.id, vm.esxi_id(), vm.esxi_id()),
                    'subcategory': settings.ITOP_CATEGORIES.get('VM_POWER_ON'),
                }
                result = notify(ticket)
                if result['code'] == 0:
                    vm.pending_poweron = True
                    vm.save()
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
            else:
                result = {"code": 403, "message": _("Can't send power on request due to another request has been made.")}
                messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
        else:
            result = {"code": 403, "message": _("The VM is already powered on.")}
            messages.error(request, str(result['code']) + ': ' + str(result['message']))
            return HttpResponseRedirect(reverse('result'))
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to power on this VM")})


@login_required
def vm_poweroff(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        if vm.state is True:
            if not vm.pending_poweron:
                ticket = {
                    'title': '[' + str(vm.hypervisor.location) + str(_('][VM][POWER OFF] ')) + vm.name,
                    'username': request.user.username,
                    'description': _('<p><strong>POWER OFF VM</strong></p><p>Hypervisor: %s</p><p>VM Name: %s</p><p>ID VMtory: %s</p><p>ESXi VM ID: %s</p>') % (vm.hypervisor.name, vm.name, vm.id, vm.esxi_id()),
                    'subcategory': settings.ITOP_CATEGORIES.get('VM_POWER_OFF'),
                }
                result = notify(ticket)
                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
            else:
                result = {"code": 403, "message": _("Can't send a poweroff due to a pending power on request.")}
                messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
        else:
            result = {"code": 403, "message": _("The VM is already powered off.")}
            messages.error(request, str(result['code']) + ': ' + result['message'])
            return HttpResponseRedirect(reverse('result'))
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to power off this VM")})


@login_required
def vm_reset(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        if vm.state is True:
            ticket = {
                'title': '[' + str(vm.hypervisor.location) + str(_('][VM][RESET] ')) + vm.name,
                'username': request.user.username,
                'description': _('<p><strong>RESET VM</strong></p><p>Hypervisor: %s</p><p>VM Name: %s</p><p>ID VMtory: %s</p><p>ESXi VM ID: %s</p>') % (vm.hypervisor.name, vm.name, vm.id, vm.esxi_id()),
                'subcategory': settings.ITOP_CATEGORIES.get('VM_POWER_RESET'),
            }
            result = notify(ticket)
            if result['code'] == 0:
                messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
            else:
                messages.error(request, str(result['code']) + ': ' + result['message'])
            return HttpResponseRedirect(reverse('result'))
        else:
            result = {"code": 403, "message": _("Can't send the reset request. The VM is powered off.")}
            messages.error(request, str(result['code']) + ': ' + result['message'])
            return HttpResponseRedirect(reverse('result'))
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to reset this VM")})


@login_required
def vm_duplicate(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        esxi = vm.hypervisor.name
        if request.method == 'POST':
            form = DuplicateVMForm(request.POST, user=request.user, vm_id=vm_id, vm_name=vm.name, esxi=esxi)
            if form.is_valid():
                ticket = {'username': request.user.username, 'description': '', 'subcategory': settings.ITOP_CATEGORIES.get('VM_CLONE')}
                ticket['title'] = "[" + str(form.cleaned_data['location']) + str(_("][VM][CLONE] ")) + str(form.cleaned_data['vmoriginal_name'])
                for field in form:
                    ticket['description'] += "<p>" + str(field.label) + ": " + str(form.cleaned_data[field.name]) + '</p>\n'
                result = notify(ticket)
                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + str(result['message']))
                return HttpResponseRedirect(reverse('result'))
            else:
                return render(request, "newvm.html", {"form": form, 'page_title': 'Clonar VM'})
        else:
            return render(request, "newvm.html", {"form": DuplicateVMForm(user=request.user, vm_id=vm_id, vm_name=vm.name, esxi=esxi), 'page_title': _('Clone VM')})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to clone this VM")})


@login_required
def vm_backup(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        esxi = vm.hypervisor.name
        if request.method == 'POST':
            form = BackupVMForm(request.POST, vm_id=vm_id, vm_name=vm.name, esxi=esxi)
            if form.is_valid():
                ticket = {'username': request.user.username, 'description': '', 'subcategory': settings.ITOP_CATEGORIES.get('VM_BACKUP')}
                ticket['title'] = "[" + str(vm.hypervisor.location) + str(_("][VM][EXPORT] ")) + form.cleaned_data['vmoriginal_name']
                for field in form:
                    ticket['description'] += "<p>" + str(field.label) + ": " + str(form.cleaned_data[field.name]) + '</p>\n'
                result = notify(ticket)
                if result['code'] == 0:
                    messages.success(request, _("Request succesfully sent! You'll receive an email with the request confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
            else:
                return render(request, "newvm.html", {"form": form, 'page_title': _('Export VM')})
        else:
            return render(request, "newvm.html", {"form": BackupVMForm(vm_id=vm_id, vm_name=vm.name, esxi=esxi), 'page_title': _('Export VM')})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to backup this VM")})


@login_required
def vm_modify(request, vm_id):
    vm = VM.objects.get(id=vm_id)
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        esxi = vm.hypervisor.name
        if request.method == 'POST':
            form = ModifyVMForm(request.POST, vm=vm, esxi=esxi)
            if form.is_valid():
                ticket={'description': '', 'username': request.user.username}
                ticket['title'] = "[" + str(vm.hypervisor.location) + str(_("][VM][MODIFY] ")) + form.cleaned_data['vmoriginal_name']
                for field in form:
                     ticket['description'] += "<p>" + str(field.label) + ": " + str(form.cleaned_data[field.name]) + '</p>\n'
                ticket['description'] += _('<p> The following parameters have been modified: </p>\n') + '<p>' +'<br />'.join(form.changed_data) + '</p>\n'
                result = notify(ticket)
                if result['code'] == 0:
                    messages.success(request, _("Request sent successfully. You will get an email with the confirmation."))
                else:
                    messages.error(request, str(result['code']) + ': ' + result['message'])
                return HttpResponseRedirect(reverse('result'))
            else:
                return render(request, "newvm.html", {"form": form, 'page_title': _('Modify VM')})
        else:
            return render(request, "newvm.html", {"form": ModifyVMForm(vm=vm, esxi=esxi), 'page_title': _('Modify VM')})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Your user doesn't have permissions to modify this VM")})

@login_required
def top10(request):
    if request.user.is_staff:
        table = Top10Table( VM.objects.filter(deleted=False).values('assignee__username').annotate(total=Count('assignee')), request )
        RequestConfig(request).configure(table)
        return render(request, "top10.html", {"top10": table, 'page_title': 'Top 10'})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'esxi', 'page_title': _('Permissions error'), 'error_description': _('Only staff can see the TOP 10 ;)')})



@login_required
def result(request):
    return render(request, "message.html", {'page_title': _('Operation result')})


@login_required
def favorites_toggle(request, vm_id):
    if request.is_ajax():
        vm = VM.objects.get(id=vm_id)
        if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
            if request.user in vm.favorites.all() or []:
                vm.favorites.remove(request.user)
            else:
                vm.favorites.add(request.user)
            vm.save()
            json_response = {'vm_id': str(vm_id), 'vm': str(vm)}
            return HttpResponse(json.dumps(json_response), content_type='application/json')
        else:
            return render(request, "no_permission.html", {'viewfilter': 'esxi', 'page_title': _('Permissions error'), 'error_description': _("You can't add this VM to your favourites")})


@login_required
def update_notes(request, vm_id):
    if request.is_ajax():
        vm = VM.objects.get(id=vm_id)
        if request.user.groups.filter(name=vm.group or '') or \
           request.user.is_staff or \
           vm.assignee == request.user:
            vm.notes = request.body
            vm.save()
            result = 'ok'
        else:
            result = _("Error: you don't have permissions to modify notes.")
        json_response = {'result': result}
        return HttpResponse(json.dumps(json_response), content_type='application/json')


@login_required
def ipam(request):
    """
    TODO: Refactor all the IPAM. It works on the assumption that all networks are /24 and doens't take into account the environments.
    TODO: Separate IPs per environment.
    """
    if request.user.is_staff:
        nhosts = range(1, 255)
        ips = VM.objects.filter(deleted=False).values('ip_address')
        reserved_ips = ReservedIPAddress.objects.all()
        networks = onetworks = {}
        environments: Environment.objects.all()

        for ip_address in ips:
            ip = ip_address.get('ip_address')
            if ip and ':' not in ip:
                host = ip.split('.')[-1]
                network = '.'.join(ip.split('.')[:-1])
                if networks.get(network):
                    if networks[network].get(host):
                        networks[network][host] = {'in_use': True, 'reserved': False, 'duplicated': True, 'msg': networks[network][host]['msg']}
                    else:
                        networks[network][host] = {'in_use': True, 'reserved': False, 'duplicated': False, 'msg': ''}
                else:
                    networks[network] = {host: {'in_use': True, 'reserved': False, 'duplicated': False, 'msg': ''}}

        for r_ip_address in reserved_ips:
            r_ip = r_ip_address.ip_address
            msg = r_ip_address.observations
            if ip and ':' not in ip:
                host_r = r_ip.split('.')[-1]
                network_r = '.'.join(r_ip.split('.')[:-1])
                if networks.get(network_r):
                    if networks[network_r].get(host_r):
                        networks[network_r][host_r] = {'in_use': True, 'reserved': True, 'duplicated': True, 'msg': networks[network_r][host_r]['msg'] + ' \n ' + msg}
                    else:
                        networks[network_r][host_r] = {'in_use': True, 'reserved': True, 'duplicated': False, 'msg': msg}
                else:
                    networks[network_r] = {host_r: {'in_use': True, 'reserved': True, 'duplicated': False, 'msg': msg}}

        for network_f in networks:
            used = 0
            unused = 0
            for host_f in nhosts:
                host_f = str(host_f)
                if not networks[network_f].get(host_f):
                    networks[network_f][host_f] = {host_f: {'in_use': False, 'reserved': False, 'duplicated': False, 'msg': ''}}
                    unused += 1
                else:
                    used += 1
            networks[network_f]['used'] = used
            networks[network_f]['unused'] = unused

            # Magia para que las IPs aparezcan ordenadas.
            onetworks = OrderedDict(sorted(networks.items(), key=lambda t: ipaddress.IPv4Network(t[0] + '.0/24') if t[0] != '' else ipaddress.IPv4Network('0.0.0.0')))
            for n in onetworks:
                onetworks[n] = OrderedDict(sorted(onetworks[n].items(), key=lambda t: int(t[0]) if not t[0].endswith('used') and ':' not in t[0] else 0))

        return render(request, "ipam.html", {"page_title": "IPAM", "snetworks": onetworks, "networks": onetworks})
    else:
        return render(request, "no_permission.html", {'viewfilter': 'myvms', 'page_title': _('Permissions error'), 'error_description': _("Only staff can access the IPAM moduke")})


@login_required
def api_get_vm(request, vm_id):
    vms = VM.objects.filter(id=vm_id)
    if not vms:
        raise Http404
    
    vm = vms[0]
    if request.user.groups.filter(name=vm.group or '') or request.user.is_staff or vm.assignee == request.user:
        jresponse = {
            'id': vm.id,
            'esxi_vm_id': vm.esxi_id(),
            'name': vm.name,
            'ip': vm.ip_address,
            'networking': vm.networking if vm.networking else '-',
            'hypervisor': vm.hypervisor.name if vm.hypervisor else '-',
            'state': 'ON' if vm.state else 'OFF',
            'deleted': vm.deleted,
            'assignee': vm.assignee.username if vm.assignee else '-',
            'group': vm.group.name if vm.group else '-',
            'annotation': vm.annotation,
            'environment': vm.environment.name if vm.environment else '-',
            'cpu': vm.cpus,
            'ram': vm.ramh(),
            'hdd': vm.hdds,
        }
    else:
        return HttpResponseForbidden()
    return HttpResponse(json.dumps(jresponse), content_type='application/json')

@login_required
def profile(request):
    return render(request, "profile.html", {'page_title': _('User profile'), 'user': request.user})

def ayuda(request):
    return render(request, "ayuda.html", {'viewfilter': 'ayuda', 'page_title': _('Help')})

def notify(ticket):
    if 'itop' in settings.VMTORY_NOTIFICATION_BACKEND:
        result = create_ticket(ticket)
        logger.debug("Creating ticket resulted in: %s" % result)
    if 'email' in settings.VMTORY_NOTIFICATION_BACKEND:
        result = {}
        result['code'] = send_mail(
            ticket['title'],
            '<p>New request from: ' + ticket['username'] + '</p>\n' + str(ticket['description']),
            settings.DEFAULT_FROM_EMAIL,
            [settings.VMTORY_SUPPORT_EMAIL],
            fail_silently=False,
        )
        if result['code'] == 1:
            result['message'] = "1 email sent"
            result['code'] = 0
        else:
            result['code'] = 500
            result['message'] = "Message not sent."
        logger.debug("Sending email resulted in: %s" % result)
    return result
