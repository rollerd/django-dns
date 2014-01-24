from django import forms
from pdns.models import Subnet, Mapping
from django.forms import ModelForm
from django.forms.formsets import formset_factory, BaseFormSet
from django.forms import MultipleChoiceField
from django.forms.extras.widgets import Select
import pylib

# These sets of functions/classes create the base forms for use in views.py and are pretty straightforward 

class IndexForm(forms.Form):
    name = forms.CharField(max_length=255)


def get_domains():
    '''Queries our Subnet model to create the list of domains for display on the index page '''
    domain_list = []
    query = Subnet.objects.all()
    for obj in query:
        if obj.domain not in domain_list:
            domain_list.append(obj.domain)
    return domain_list


class MappingForm(ModelForm):
    '''Creates a modelform from the Mapping model. Specifies which fields to display and has a custom clean method to check for duplicate fields and invalid characters in the entered data '''
    class Meta:
        model = Mapping
        fields = ['ip_or_cname', 'hostname']
    def clean(self):
        invalid_chars = '!@#$%^&*()+=<>,/? :;"\'{}[]|\\`~'
        field1 = self.cleaned_data.get('ip_or_cname')
        field2 = self.cleaned_data.get('hostname')
        if field1 == field2:
            raise forms.ValidationError('IP/CNAME and Hostname cannot be the same!', code='double')
        for character in invalid_chars:
            if field1 and character in field1:
                raise forms.ValidationError('Invalid character: "%s" in IP/CNAME' % character)
            if field2 and character in field2:
                raise forms.ValidationError('Invalid character: "%s" in hostname' % character)
        return self.cleaned_data


def get_choices():
    '''Queries the Subnet model to create a list of subnet names for display on the index page'''
    name_list = []
    objects = Subnet.objects.all()
    for obj in objects:
        name_list.append((obj.subnet_name, obj.proper_name))
    return name_list


class NameForm(forms.Form):
    '''Takes the list of subnet name choices from get_choices() and formats them as a dropdown '''
    def __init__(self, *args, **kwargs):
        super(NameForm, self).__init__(*args, **kwargs)
        self.fields['subnet'] = forms.MultipleChoiceField(choices=get_choices(), widget=Select)


class ModifyAllForm(ModelForm):
    '''Modelform for the modify_all view. Sets fields and some custom data checks for invalid/duplicate data in the form '''
    class Meta:
        model = Mapping
        fields = ['ip_or_cname', 'hostname', 'record_type']
    def clean(self):
        invalid_chars = '!@#$%^&*()+=<>,/? :;"\'{}[]|\\`~'
        field1 = self.cleaned_data.get('ip_or_cname')
        field2 = self.cleaned_data.get('hostname')
        if field1 == field2:
            raise forms.ValidationError('IP/CNAME and Hostname cannot be the same!', code='double')
        for character in invalid_chars:
            if field1 and character in field1:
                raise forms.ValidationError('Invalid character: "%s" in IP/CNAME' % character)
            if field2 and character in field2:
                raise forms.ValidationError('Invalid character: "%s" in hostname' % character)
        return self.cleaned_data


#class SubnetForm(ModelForm):
#    '''Commented this out as it was no longer needed. Was used to create dropdown for domain names '''
#    def __init__(self, *args, **kwargs):
#        super(SubnetForm, self).__init__(*args, **kwargs)
#        test = Subnet.objects.values('domain').distinct()
#        self.fields['domain'] = forms.ModelChoiceField(queryset=Subnet.objects.values('domain').distinct())
#    class Meta:
#        model = Subnet


class RequiredFormSet(BaseFormSet):
    '''No longer required unless we want to override a model requirement that a field have a value entered. There are references to this formset in the view however. '''
    pass
    #def __init__(self, *args, **kwargs):
    #    super(RequiredFormSet, self).__init__(*args, **kwargs)
    #    for form in self.forms:
    #        form['ip_or_cname'].empty_permitted = True


class RecordForm(ModelForm):
    '''Modelform for modifying a single entry. Sets fields and custom check for entered data '''
    class Meta:
        model = Mapping
        fields = ['ip_or_cname', 'hostname', 'record_type']
    def clean(self):
        invalid_chars = '!@#$%^&*()+=<>,/? :;"\'{}[]|\\`~'
        field1 = self.cleaned_data.get('ip_or_cname')
        field2 = self.cleaned_data.get('hostname')
        if field1 == field2:
            raise forms.ValidationError('IP/CNAME and Hostname cannot be the same!', code='double')
        for character in invalid_chars:
            if field1 and character in field1:
                raise forms.ValidationError('Invalid character: "%s" in IP/CNAME' % character)
            if field2 and character in field2:
                raise forms.ValidationError('Invalid character: "%s" in hostname' % character)
        return self.cleaned_data

