from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address


# Create your models here.

def validate_network_letter(network_letter):
    if network_letter not in 'abcdefghijklmnopqrstuvwxyz':
        raise ValidationError(u'%s is not a lower-case letter!' % network_letter)


def validate_record_type(record_type):
    valid_types = ['CNAME', 'A']
    if record_type not in valid_types:
        raise ValidationError(u"Must be either 'CNAME' or 'A' ")


class Subnet(models.Model):
    def __unicode__(self):
        return self.subnet_name
    proper_name = models.CharField(max_length=255, null=True, blank=True, default='TEMP', help_text='This will be auto-filled based on the info you have provided above, but you may change it later')
    subnet_name = models.CharField(max_length=255, db_index=True, unique=True)
    ip_range_start = models.CharField(max_length=255, validators=[validate_ipv4_address])
    ip_range_end = models.CharField(max_length=255, validators=[validate_ipv4_address])
    domain = models.CharField(max_length=255)
    network_letter = models.CharField(max_length=1, null=True, blank=True, validators=[validate_network_letter], help_text='Please use a lower case letter')

class Mapping(models.Model):
    def __unicode__(self):
        return self.ip_or_cname
    subnet = models.ForeignKey(Subnet, to_field='subnet_name')
    ip_or_cname = models.CharField(max_length=255, blank=True)
    hostname = models.CharField(max_length=255)
    record_type = models.CharField(max_length=10, default='A', validators=[validate_record_type])



