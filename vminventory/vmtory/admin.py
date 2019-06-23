from django.contrib import admin

# Register your models here.
from .models import ESXi, VM, OS, ReservedIPAddress, Environment, Location

admin.site.register(ESXi)
admin.site.register(VM)
admin.site.register(OS)
admin.site.register(ReservedIPAddress)
admin.site.register(Environment)
admin.site.register(Location)
