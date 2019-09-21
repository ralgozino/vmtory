# *-* encoding: utf-8 *-*

from django_tables2 import tables, Column
from vmtory.models import VM
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

OPC_TEMPLATE = '{% load i18n %}<div class="ui tiny icon center aligned buttons">'
OPC_TEMPLATE += '{% url \'vm_details\' record.id as the_url%} <a href="{{the_url}}" class="ui icon button" data-tooltip="{% blocktrans %}VM details and adavanced options{% endblocktrans %}"><i class="blue info icon"></i></a>'
OPC_TEMPLATE += '{% if record.pending_poweron %}\
<span class="ui icon button" data-tooltip="{% blocktrans %}There\'s a poweron request pending{% endblocktrans %}"><i class="refresh disabled icon loading"></i></span>\
{% else %}\
    {% if record.state %}\
    {% url \'vm_poweroff\' record.id as the_url%} <a href="{{the_url}}" class="ui icon button {% if record.deleted %}disabled{% endif %}" data-tooltip="{% blocktrans %}Request power off{% endblocktrans %}"><i class="red stop circle icon"></i></a>\
    {% else %}\
    {% url \'vm_poweron\' record.id as the_url%} <a href="{{the_url}}" class="ui icon {% if record.deleted %}disabled{% endif %} button" data-tooltip="{% blocktrans %}Request power on{% endblocktrans %}"><i class="green play circle icon"></i></a>\
    {% endif %}\
{% endif %}'
OPC_TEMPLATE += '{% url \'favorites_toggle\' record.id as the_url%}<a href="#" onclick="toggleFavorite(\'{{the_url}}\', \'.fav{{record.id}}\', \'.anchor{{record.id}}\')" class="ui icon button anchor{{record.id}}"  data-toggle=tooltip data-tooltip="{%if table.request.user in record.favorites.all%}{% blocktrans %}Remove from{% endblocktrans %}{%else%}{% blocktrans %}Add to{% endblocktrans %}{%endif%} {%blocktrans%}favourites{%endblocktrans%}"><i class="star {%if table.request.user in record.favorites.all%}yellow {%else%} black{%endif%} icon fav{{record.id}}"></i></a>'
OPC_TEMPLATE += '{% url \'vm_delete\' record.id as the_url%} <a href="{{the_url}}" class="ui icon button {% if record.deleted %}disabled{% endif %}" data-toggle=tooltip data-tooltip="{% blocktrans %}Request deletion{% endblocktrans %}"><i class="orange trash icon"></i></a>'
OPC_TEMPLATE += '</div>'

class Top10Table(tables.Table):
    assignee__username = Column(_('User'))
    total = Column(_('Quantity'))

class GenericTable(tables.Table):
    acceso_rapido = tables.columns.TemplateColumn(OPC_TEMPLATE, orderable=False, verbose_name=_('Quick Access'), attrs={'th': {'class': 'collapsing'}})
    annotation_p = tables.columns.TemplateColumn('{% if record.annotation %}{{record.annotation|linebreaksbr}}{%else%}&mdash;{%endif%}', orderable=False, verbose_name=_('Annotations'))

    class Meta:
        model = VM
        template = 'semantic_table.html'
        exclude = ['uuid', 'public', 'path', 'vmid', 'annotation', 'iuuid', 'deleted', 'pending_poweron', 'uptime', 'notes', 'last_poweron', 'networking']
        attrs = {"class": "ui table"}
        sequence = (
                    'id',
                    'state',
                    'hypervisor',
                    'environment',
                    'name',
                    'cpus',
                    'ram',
                    'hdds',
                    'guest',
                    'ip_address',
                    'assignee',
                    'group',
                    'annotation_p',
                    'last_update',
                    'acceso_rapido',
                    )

    def render_environment(self, value, record):
        if record.environment:
            display = ' <span class="ui horizontal mini %s basic label">%s</span>' % (record.environment.color, record.environment.name)
        else:
            display = ''
        return mark_safe(display)

    def render_ram(self, value, record):
        return record.ramh()

    def render_hypervisor(self, value):
        hv = value
        if hv.tooltip:
            return mark_safe('<span data-tooltip="' + hv.tooltip + '">' + hv.name + '</span>')
        else:
            return mark_safe('<span>' + hv.name + '</span>')

    def render_state(self, value, record):
        template = '<div data-tooltip="%s" class="ui center aligned icon"><i class="%s %s icon"></i></div>'
        if record.deleted:
            return mark_safe(template % (_('Eliminada'), 'trash', 'brown'))
        known_state, unkown_message = record.known_state()
        if known_state:
            if value:
                ut = record.uptimef()
                if ut:
                    encendida = _('Powered on since %s') % record.uptimef()
                else:
                    encendida = _('Powered on')
                return mark_safe(template % (encendida, 'play circle', 'green'))
            else:
                return mark_safe(template % (_('Powered off'), 'stop circle', 'red'))
        else:
            return mark_safe(template % (unkown_message, 'question circle', 'grey'))

    def order_assignee(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'assignee__username')
        return (queryset, True)

    def order_group(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'group__name')
        return (queryset, True)


class VMTable(GenericTable):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(VMTable, self).__init__(*args, **kwargs)

    class Meta:
        attrs = {"class": "ui striped table"}
        exclude = ['assignee', 'guest', 'last_update']


class GroupVMTable(GenericTable):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupVMTable, self).__init__(*args, **kwargs)

    class Meta:
        exclude = ['guest', 'last_update']

    def order_assignee(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'assignee__username')
        return (queryset, True)

    def order_group(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'group__name')
        return (queryset, True)


class DeletedVMTable(GenericTable):

    class Meta:
        exclude = ['state', 'acceso_rapido', 'guest']
        sequence = (
                    'id',
                    'hypervisor',
                    'environment',
                    'name',
                    'cpus',
                    'ram',
                    'hdds',
                    'ip_address',
                    'assignee',
                    'group',
                    'last_update',
                    )


class AllVMTable(GenericTable):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(AllVMTable, self).__init__(*args, **kwargs)
        
    id_with_link = tables.columns.TemplateColumn('{% url \'vm_details\' record.id as the_url%} <a href="{{the_url}}">{{record.id}}</a>', verbose_name='ID', order_by='id')

    class Meta:
        exclude = ['id', 'guest']
        sequence = (
                    'id_with_link',
                    'state',
                    'hypervisor',
                    'environment',
                    'name',
                    'cpus',
                    'ram',
                    'hdds',
                    'ip_address',
                    'assignee',
                    'group',
                    'annotation_p',
                    'last_update',
                    )


class AdvancedSearchVMTable(tables.Table):
    opciones_template = '<a class="ui mini compact button" data-tooltip="{% load i18n %}{% blocktrans %}Opens an email with the VM data and the owner as receipent.{% endblocktrans %}" href="mailto:{{record.assignee}}@ayourdomain?Subject={% blocktrans %}Query%20about%20VM{% endblocktrans %}%20%22{{record.name}}%22&Body={% blocktrans %}Query%20about%20VM%20id:%20{% endblocktrans %}{{record.id}}%20%0D%0A%20VM%20Name:%20{{record.name}}%20%0D%0A%20IP:%20{{record.ip_address}}"><i class="envelope icon"></i> {% blocktrans %}Query{% endblocktrans %}</a>'
    opciones = tables.columns.TemplateColumn(opciones_template, verbose_name=_("Options"), orderable=False)
    id_with_link = tables.columns.TemplateColumn('{% url \'vm_details\' record.id as the_url%} <a href="{{the_url}}">{{record.id}}</a>', verbose_name='ID', order_by='id')

    class Meta:
        model = VM
        exclude = ['id', 'uuid', 'public', 'path', 'vmid', 'networking', 'annotation', 'iuuid', 'deleted', 'pending_poweron', 'guest', 'uptime', 'last_update', 'notes', 'last_poweron']
        sequence = (
                    'id_with_link',
                    'state',
                    'hypervisor',
                    'environment',
                    'name',
                    'cpus',
                    'ram',
                    'hdds',
                    'ip_address',
                    'assignee',
                    'group',
                    'opciones',
                    )

    def render_ram(self, value, record):
            return record.ramh()

    def render_hypervisor(self, value):
        hv = value

        return mark_safe('<span data-tooltip="%s">%s</span>' % (hv.tooltip, hv.name))

    def render_state(self, value, record):
        template = '<div data-tooltip="%s" class="ui center aligned icon" data-variation="small"><i class="%s %s icon"></i></div>'
        if record.deleted:
            return mark_safe(template % (_('Deleted'), 'trash', 'brown'))
        known_state, unkown_message = record.known_state()
        if known_state:
            if value:
                ut = record.uptimef()
                if ut:
                    encendida = _('Powered on since %s') % record.uptimef()
                else:
                    encendida = _('Powered on')
                return mark_safe(template % (encendida, 'play circle', 'green'))
            else:
                return mark_safe(template % (_('Powered off'), 'stop circle', 'red'))
        else:
            return mark_safe(template % (unkown_message, 'question circle', 'grey'))

    def render_environment(self, value, record):
        if record.environment:
            display = ' <span class="ui horizontal mini %s basic label">%s</span>' % (record.environment.color, record.environment.name)
        else:
            display = ''
        return mark_safe(display)
