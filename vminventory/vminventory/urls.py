from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
import vmtory

urlpatterns = (
    # Examples:
    # url(r'^$', 'vminventory.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^vmtory/', include('vmtory.urls')),
    url(r'^accounts/login/$', auth_views.login, name='login'),
    url(r'^accounts/profile/$', vmtory.views.index),
    url(r'^accounts/logout/$', auth_views.logout,{'next_page': 'index'}, name='logout'),
    # url(r'^$', include('vmtory.urls')),
    url(r'^$', lambda r: HttpResponseRedirect('vmtory/')),
    # url(r'^esxi/', include('vmtory.urls')),
    # url(r'^load_vms/', include('vmtory.urls')),
)
