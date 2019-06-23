from django.conf.urls import url

from vmtory import views

urlpatterns = (
    url(r'^esxi/$', views.esxi, name='esxi'),
    url(r'^myvms/$', views.myvms, name='myvms'),
    url(r'^groupvms/$', views.groupvms, name='groupvms'),
    url(r'^vms/$', views.allvms, name='allvms'),
    url(r'^newvm/$', views.newvm, name='newvm'),
    url(r'^search/$', views.search, name='search'),
    url(r'^advsearch/$', views.advsearch, name='advsearch'),
    url(r'^ipam/$', views.ipam, name='ipam'),
    url(r'^$', views.index, name='index'),
    url(r'^result/$', views.result, name='result'),
    url(r'^ayuda/$', views.ayuda, name='ayuda'),
    url(r'^top10/$', views.top10, name='top10'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^vm/(?P<vm_id>\d+)/snap/restore/(?P<snap_id>\d+)/(?P<snap_name>.+)/$', views.snap_restore, name='snap_restore'),
    url(r'^vm/(?P<vm_id>\d+)/snap/delete/(?P<snap_id>\d+)/(?P<snap_name>.+)/$', views.snap_delete, name='snap_delete'),
    url(r'^vm/(?P<vm_id>\d+)/snap/take/$', views.snap_take, name='snap_take'),
    url(r'^vm/(?P<vm_id>\d+)/delete/$', views.vm_delete, name='vm_delete'),
    url(r'^vm/(?P<vm_id>\d+)/poweron/$', views.vm_poweron, name='vm_poweron'),
    url(r'^vm/(?P<vm_id>\d+)/poweroff/$', views.vm_poweroff, name='vm_poweroff'),
    url(r'^vm/(?P<vm_id>\d+)/reset/$', views.vm_reset, name='vm_reset'),
    url(r'^vm/(?P<vm_id>\d+)/duplicate/$', views.vm_duplicate, name='vm_duplicate'),
    url(r'^vm/(?P<vm_id>\d+)/backup/$', views.vm_backup, name='vm_backup'),
    url(r'^vm/(?P<vm_id>\d+)/modify/$', views.vm_modify, name='vm_modify'),
    url(r'^vm/(?P<vm_id>\d+)/favorites/toggle$', views.favorites_toggle, name='favorites_toggle'),
    url(r'^vm/(?P<vm_id>\d+)/note/update$', views.update_notes, name='update_notes'),
    url(r'^vm/(?P<vm_id>\d+)/screenshot$', views.vm_screenshot, name='vm_screenshot'),
    url(r'^vm/(?P<vm_id>\d+)/$', views.vm_details, name='vm_details'),
    url(r'^api/1.0/vm/(?P<vm_id>\d+)/$', views.api_get_vm, name='api_get_vm'),
)
