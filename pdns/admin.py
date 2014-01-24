from django.contrib import admin
from pdns.models import Subnet, Mapping
from django.forms import ModelForm

# Register your models here.

class AdminForm(ModelForm):
    def clean_proper_name(self):
        print 'cleaned_data', self.cleaned_data
        short_name = self.cleaned_data.get('subnet_name')
        ip_start = self.cleaned_data.get('ip_range_start')
        ip_end = self.cleaned_data.get('ip_range_end')
        net_letter = self.cleaned_data.get('network_letter')
        if net_letter:
            new_name = 'Wharton -%s (%s) Network (%s - %s)' % (net_letter, short_name, ip_start, ip_end)
        else:
            new_name = '%s Network (%s - %s)' % (short_name.capitalize(), ip_start, ip_end)
        return new_name

class MappingInline(admin.TabularInline):
    model = Mapping
    choice = 5

class SubnetAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields' : ['subnet_name']}),
        (None, {'fields' : ['ip_range_start']}),
        (None, {'fields' : ['ip_range_end']}),
        (None, {'fields' : ['domain']}),
        (None, {'fields' : ['network_letter']}),
        (None, {'fields' : ['proper_name']}),
    ]
    form = AdminForm
    #inlines = [MappingInline]

class MappingAdmin(admin.ModelAdmin):
    list_display = ['ip_or_cname', 'hostname', 'record_type', 'subnet']
    search_fields = ['ip_or_cname', 'hostname']
    list_filter = ['subnet__subnet_name', 'record_type']
    actions_on_bottom = True

admin.site.register(Subnet, SubnetAdmin)
admin.site.register(Mapping, MappingAdmin)
