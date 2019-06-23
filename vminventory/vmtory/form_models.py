# *-* encoding: utf-8 *-*
from django import forms
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _
from vmtory.models import OS, VM, ESXi, Environment, Location
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Field


class NewVMForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(NewVMForm, self).__init__(*args, **kwargs)
        self.fields.get("vmgroup").queryset = Group.objects.filter(user=user)

    vmname = forms.CharField(label=_('VM name'), max_length=100)
    vmos = forms.ModelChoiceField(label=_('Operating System'), queryset=OS.objects.all().order_by('os_family', 'os_version'), empty_label=_('Please select one'))
    vmgroup = forms.ModelChoiceField(label=_('Assign to group'), queryset=Group.objects.all(), empty_label=_('None'), required=False)
    cpus = forms.ChoiceField(label=_('CPUs'), choices=(enumerate(range(1, 9), 1)))
    mem = forms.ChoiceField(label=_('RAM'), choices=(enumerate([str(x) + ' GB' for x in range(1, 128)], 1)))
    hdd = forms.IntegerField(label=_('Storage in GB'), initial=20)
    ipaddress = forms.GenericIPAddressField(label=_('IP address'), required=False)
    vmuser = forms.CharField(label=_('OS user'), initial='administrator')
    vmpswd = forms.CharField(label=_('Password for OS user'), initial='changeme')
    observations = forms.CharField(label=_('Observations'), widget=forms.Textarea(), required=False)
    location = forms.ModelChoiceField(label=_('Prefered location'), required=False, queryset=Location.objects.all(), empty_label=_('Please select one'))
    environment = forms.ModelChoiceField(label=_('Environment'), required=False, queryset=Environment.objects.all(), empty_label=_('Please select one'))
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.attrs = {'class': 'ui form'}
    helper.layout = Layout(
        HTML('<h4 class="ui dividing header">' + str(_('VM characteristics')) + '</h4>'),
        Div(Field('vmname'), css_class='field'),
        Div(
            Div(Field('vmos', css_class="ui selection fluid dropdown"), css_class='field'),
            Div(Field('cpus', css_class="ui selection fluid dropdown"), css_class='field'),
            Div(Field('mem', css_class="ui selection fluid dropdown"), css_class='field'),
            Div(Field('hdd', css_class="ui selection number"), css_class='field'),
            css_class='ui inline equal width fields',
        ),
        HTML('<h4 class="ui dividing header">' + str(_('Additional Configuration')) + '</h4>'),
        Div(
            Div(Field('vmgroup', css_class="ui selection fluid dropdown"), css_class='field'),
            Div(Field('ipaddress', css_class="ui selection fluid dropdown"), css_class='field'),
            Div(Field('vmuser', css_class="ui selection fluid dropdown"), css_class='field'),
            Div(Field('vmpswd', css_class="ui selection fluid dropdown"), css_class='field'),
            css_class='ui inline equal width fields',
        ),
        HTML('<h4 class="ui dividing header">' + str(_('Speacial options')) + '</h4>'),
        Div(
            Div(Field('environment', css_class='ui selection fluid dropdown'), css_class='field'),
            Div(Field('location', css_class='ui selection fluid dropdown'), css_class='field'),
            css_class='ui inline equal width fields',
        ),
        Div(Field('observations'), css_class='field'),
        Submit('save_changes', _('Send VM creation request'), css_class="ui positive button")
    )


class DuplicateVMForm(forms.Form):
    vmoriginal_id = forms.CharField(label=_('Original VM ID'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    vmoriginal_name = forms.CharField(label=_('Original VM name'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    esxi = forms.CharField(label=_('Original VM Hypervisor'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    vmname = forms.CharField(label=_('Name for the new VM'))
    vmgroup = forms.ModelChoiceField(label=_('Assigne to the Group'), queryset=Group.objects.all(), empty_label=_('None'), required=False)
    ipaddress = forms.GenericIPAddressField(label=_('IP for the new VM'), required=False)
    observations = forms.CharField(label=_('Observations'), widget=forms.Textarea(attrs={'placeholder': _('Please, put here additional information that may be relevant, for exmaple if you need to change the VM characteristics')}), required=False)
    location = forms.ModelChoiceField(label=_('Prefered location'), required=False, queryset=Location.objects.all())
    environment = forms.ModelChoiceField(label=_('Environment'), required=False, queryset=Environment.objects.all(), empty_label=_('Please select one'))
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.attrs = {'class': 'ui container form'}
    helper.layout = Layout(
        HTML('<h4 class="ui dividing header">' + str(_('Origin VM')) + '</h4>'),
        Div(
            Div(Field('vmoriginal_id'), css_class='disabled field'), 
            Div(Field('vmoriginal_name'), css_class='disabled field'),
            Div(Field('esxi'),css_class=' disabled field'),
            css_class='inline equal width fields'
        ),
        HTML('<h4 class="ui dividing header">' + str(_("Destination VM")) + '</h4>'),
        Div(
            Div(Field('vmname'), css_class='field'),
            Div(Field('vmgroup', css_class='ui fluid selection dropdown'), css_class='field'),
            Div(Field('ipaddress'), css_class='field'),
            css_class='inline equal width fields'
            ),
        Div(
            Div(Field('environment', css_class='ui fluid selection dropdown'), css_class='field'),
            Div(Field('location', css_class='ui fluid selection dropdown'), css_class='field'),
            css_class='inline equal width fields',
            ),
        Div(Field('observations'), css_class='field'),
        Submit('save_changes', _('Request VM cloning'), css_class="ui primary center aligned button"),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        vm_id = kwargs.pop("vm_id", None)
        vm_name = kwargs.pop("vm_name", None)
        esxi = kwargs.pop("esxi", None)
        environment = kwargs.pop("environment", None) 
        super(DuplicateVMForm, self).__init__(*args, **kwargs)
        self.fields.get("vmgroup").queryset = Group.objects.filter(user=user)
        self.fields.get("vmoriginal_id").initial = vm_id
        self.fields.get("vmoriginal_name").initial = vm_name
        self.fields.get("vmname").initial = vm_name + '-CLON'
        self.fields.get("esxi").initial = esxi
        self.fields.get("environment").initial = environment


class BackupVMForm(forms.Form):
    vmoriginal_id = forms.CharField(label=_('Original VM id'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    vmoriginal_name = forms.CharField(label=_('Original VM name'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    esxi = forms.CharField(label=_('Original VM Hypervisor'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    backupname = forms.CharField(label=_('Suggested name for the backup'))
    md5sum = forms.BooleanField(label=_('Calculate MD5 hash?'), required=False)
    observations = forms.CharField(label=_('Observations'), widget=forms.Textarea(attrs={'placeholder': _('Please, put here additional information that may be relevant, for exmaple if you need the backup to run the VM in your PC or if it should be uploaded somewhere in particular')}), required=False)
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.attrs = {'class': 'ui form'}
    helper.layout = Layout(
        HTML('<h5 class="ui dividing header">' + str(_('Original VM data:')) + '</h4>'),
        Div(
            Div(Field('vmoriginal_id'), css_class='disabled field'),
            Div(Field('vmoriginal_name'), css_class='disabled field'),
            Div(Field('esxi'), css_class='disabled field'),
            css_class="inline equal width fields",
            ),
        HTML('<h5 class="ui dividing header">' + str(_('Information for the export')) + '</h4>'),
        Div(
            Div(Field('backupname'), css_class='field'),
            css_class="inline equal width fields",
            ),
        Div(
            Div(Field('md5sum'), css_class='ui toggle checkbox field'),
            css_class="inline equal width fields",
            ),
        Div(Field('observations'), css_class='field'),
        Submit('save_changes', _('Request VM export'), css_class="ui primary button"),
    )

    def __init__(self, *args, **kwargs):
        vm_id = kwargs.pop("vm_id", None)
        vm_name = kwargs.pop("vm_name", None)
        esxi = kwargs.pop("esxi", None)
        environment = kwargs.pop("environment", None)
        super(BackupVMForm, self).__init__(*args, **kwargs)
        self.fields.get("vmoriginal_id").initial = vm_id
        self.fields.get("vmoriginal_name").initial = vm_name
        self.fields.get("backupname").initial = vm_name + '_vX.Y.ova'
        self.fields.get("esxi").initial = esxi


class ModifyVMForm(forms.Form):
    vmoriginal_id = forms.CharField(label=_('VM id'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    vmoriginal_name = forms.CharField(label=_('VM Name'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    esxi = forms.CharField(label=_('Hypervisor'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    new_cpu = forms.CharField(label=_('CPUs'), max_length=100)
    new_ram = forms.CharField(label=_('RAM'))
    new_hdd = forms.CharField(label=_('Disco'))
    observations = forms.CharField(label=_('Changes'), widget=forms.Textarea(attrs={'placeholder': _('Add here additional information that is relevant to the modification being requested')}), required=False)
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.attrs = {'class': 'ui equal width form'}
    helper.layout = Layout(
        HTML('<h4 class="ui dividing header">' + str(_('VM data')) + '</h4>'),
        Div(
            Div(Field('vmoriginal_id'), css_class='disabled field'),
            Div(Field('vmoriginal_name'), css_class='disabled field'),
            Div(Field('esxi'), css_class='disabled field'),
            css_class="fields",
        ),
        HTML('<h4 class="ui dividing header">' + str(_('Requested change')) + '</h4>'),
        Div(
            Div(Field('new_cpu'), css_class='field'),
            Div(Field('new_ram'), css_class='field'),
            Div(Field('new_hdd'), css_class='field'),
            css_class='fields',
            ),
        Div(Field('observations'), css_class='field'),
        Submit('save_changes', _('Request VM modification'), css_class="ui primary button"),
    )

    def __init__(self, *args, **kwargs):
        vm = kwargs.pop("vm", None)
        esxi = kwargs.pop("esxi", None)
        super(ModifyVMForm, self).__init__(*args, **kwargs)
        self.fields.get("vmoriginal_id").initial = vm.id
        self.fields.get("vmoriginal_name").initial = vm.name
        self.fields.get("new_cpu").initial = vm.cpus
        self.fields.get("new_ram").initial = str(int(vm.ram) / 1024) + 'GB' if int(vm.ram) >= 1024 else str(vm.ram) + 'MB'
        self.fields.get("new_hdd").initial = vm.hdds
        self.fields.get("esxi").initial = esxi


class NewSnapshotForm(forms.Form):
    snap_name = forms.CharField(label=_('Snapshot name'), )
    snap_desc = forms.CharField(label=_('Snapshot description'), widget=forms.Textarea(), )
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.attrs = {'class': 'ui small form'}
    helper.layout = Layout(
        Div(
            Div(Field('snap_name'), css_class='field'),
            Div(Field('snap_desc'), css_class='field'),
            Div(Submit('save_changes', _('Request snapshot creation'), css_class="ui center aligned primary button"), css_class='field'),
            Div(HTML(_('<p>NOTE: the VM could be powered off to perform the operation</p>'))),
        ),
    )


class AdvancedSearchForm(forms.Form):
    assignee = forms.ModelMultipleChoiceField(label=_('Users'),
                                              queryset=User.objects.filter(id__in=VM.objects.all().values('assignee').distinct()).order_by('username'),
                                              required=False
                                             )
    group = forms.ModelMultipleChoiceField(label=_('Group'),
                                           queryset=Group.objects.order_by('name'),
                                           required=False
                                          )
    hypervisor = forms.ModelMultipleChoiceField(label=_('Hypervisor'),
                                                queryset=ESXi.objects.all().order_by('name'),
                                                required=False
                                               )
    ip_address = forms.CharField(label=_('IP address'),
                                 required=False
                                )
    name = forms.CharField(label=_('VM name'),
                           required=False
                          )
    annotation = forms.CharField(label=_('Annotations'),
                                 required=False
                                )
    enviroment = forms.ModelMultipleChoiceField(label=_('Environment'),
                                           queryset=Environment.objects.all().order_by('name'),
                                           required=False
                                          )
    include_deleted = forms.BooleanField(label=_('Include deleted VMs'),
                                            required=False
                                           )
    helper = FormHelper()
    helper.form_method = 'GET'
    helper.attrs = {'class': 'ui equal width mini form'}
    helper.layout = Layout(
        Div(
            Div(Field('name'), css_class='field'),
            Div(Field('ip_address'), css_class='field'),
            Div(Field('assignee', css_class="ui selection dropdown"), css_class='field'),
            Div(Field('group', css_class='ui selection dropdown'), css_class='field'),
            Div(Field('hypervisor', css_class='ui selection dropdown'), css_class='field'),
            Div(Field('enviroment', css_class='ui selection dropdown'), css_class='field'),
            Div(Field('include_deleted'), css_class='ui fluid checkbox field'),
            Submit('do_search', str(_('Search')), css_class="ui positive button"),
            css_class='inline fields'
        ),
    )


class ConfirmDeleteForm(forms.Form):
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.attrs = {'class': 'ui right aligned form'}
    helper.layout = Layout(
        Div(HTML('<a class="ui button" onclick="window.history.back()">' + str(_("Cancel")) + '</a>'),
            Submit('do_delete', _('Yes, delete.'), css_class="ui negative button"),
           ),
    )
