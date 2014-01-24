# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Mapping', fields ['ip_or_cname']
        db.delete_unique(u'pdns_mapping', ['ip_or_cname'])

        # Adding unique constraint on 'Mapping', fields ['hostname']
        db.create_unique(u'pdns_mapping', ['hostname'])


    def backwards(self, orm):
        # Removing unique constraint on 'Mapping', fields ['hostname']
        db.delete_unique(u'pdns_mapping', ['hostname'])

        # Adding unique constraint on 'Mapping', fields ['ip_or_cname']
        db.create_unique(u'pdns_mapping', ['ip_or_cname'])


    models = {
        u'pdns.mapping': {
            'Meta': {'object_name': 'Mapping'},
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_or_cname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '10'}),
            'subnet': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pdns.Subnet']", 'to_field': "'subnet_name'"})
        },
        u'pdns.subnet': {
            'Meta': {'object_name': 'Subnet'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_range_end': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ip_range_start': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'network_letter': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'proper_name': ('django.db.models.fields.CharField', [], {'default': "'TEMP'", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'subnet_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
        }
    }

    complete_apps = ['pdns']