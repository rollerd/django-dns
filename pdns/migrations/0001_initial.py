# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Subnet'
        db.create_table(u'pdns_subnet', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subnet_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('ip_range_start', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ip_range_end', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('network_letter', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
        ))
        db.send_create_signal(u'pdns', ['Subnet'])

        # Adding model 'Mapping'
        db.create_table(u'pdns_mapping', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subnet', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pdns.Subnet'], to_field='subnet_name')),
            ('ip_or_cname', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('record_type', self.gf('django.db.models.fields.CharField')(default='A', max_length=10)),
        ))
        db.send_create_signal(u'pdns', ['Mapping'])


    def backwards(self, orm):
        # Deleting model 'Subnet'
        db.delete_table(u'pdns_subnet')

        # Deleting model 'Mapping'
        db.delete_table(u'pdns_mapping')


    models = {
        u'pdns.mapping': {
            'Meta': {'object_name': 'Mapping'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_or_cname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
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
            'subnet_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
        }
    }

    complete_apps = ['pdns']