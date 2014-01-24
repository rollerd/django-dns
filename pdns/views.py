from pdns.models import Mapping, Subnet
from django.shortcuts import *
import anydbm
import os
import pylib
import socket
from forms import IndexForm, NameForm, MappingForm, RequiredFormSet, ModifyAllForm, RecordForm
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.contrib import messages

# This file is responsible for creating all of the data for the templates. It also directly
# renders some views as well.

# Creates changelog object for logging and writing changes
CHANGELOG = pylib.Changelog()
# Path to output zonefiles directory
OUTPUT_PATH = '/var/www/html/network/mgmt_network/djangodns/privatedns/pdns/output/'

# Create your views here.

def index(request):
    '''
    Creates forms for index view and redirects to appropriate pages. (Would be better to do this without redirects)
    The basic non-interactive views are redirected to the appropriate page.
    Returns render with subnet list form, domain list form

    arguments:
        request: request object
    '''
    if request.method == 'POST':
        req_type = request.POST['type']
        if 'domain' in request.POST:
            return HttpResponseRedirect('/privatedns/view/text/domain/%s' % request.POST['domain'])
        if request.POST['subnet']:
            name = request.POST['subnet']
            if req_type == 'forward':
                return HttpResponseRedirect("/privatedns/view/text/%s" % name)
            if req_type == 'reverse':
                return HttpResponseRedirect("/privatedns/view/text/reverse/%s" % name)
            if req_type == 'all':
                return HttpResponseRedirect("/privatedns/view/text/domain/%s" % name)
            if req_type == 'ip':
                return HttpResponseRedirect("/privatedns/view/html/ip/%s" % name)
            if req_type == 'name':
                return HttpResponseRedirect("/privatedns/view/html/name/%s" % name)
            if req_type == 'add':
                number = request.POST['number']
                return HttpResponseRedirect("/privatedns/add/new/%s/%s" % (name, number))
            if req_type == 'mod_single':
                return HttpResponseRedirect("/privatedns/modify/single/%s" % (name))
            if req_type == 'mod_all':
                return HttpResponseRedirect("/privatedns/modify/all_records/%s" % (name))
            else:
                return HttpResponse("ERROR: Unknown 'type' field in request. Must be one of: forward, reverse, all")
        else:
            return HttpResponse('ERROR: NO SUBNET SELECTED')
    else:
        subnet_list_form = NameForm()
        domain_list_form = pylib.get_domains()
    return render(request, 'pdns/index.html', {'subnets' : subnet_list_form, 'domains' : domain_list_form })


def text(request, name):
    '''
    Displays data for forward text view. Index redirects here.
    Generates IP/CNAME lists from models and sorts them
    Returns direct response in plain text format

    arguments:
        request: request object
        name: subnet name
    '''
    response = HttpResponse(content_type='text/plain')
    if not Mapping.objects.filter(subnet_id = name):
        response.write("ERROR: NO SUBNET WITH NAME: %s FOUND text" % name)
    else:
        mapping = Mapping.objects.filter(subnet_id = name)
        unsorted_ip_list = []
        unsorted_cname_list = []
        for obj in mapping:
            if not pylib.is_valid_ip(obj.ip_or_cname):
                unsorted_cname_list.append(obj.ip_or_cname)
            else:
                unsorted_ip_list.append(obj.ip_or_cname)
        sorted_ip_list = sorted(unsorted_ip_list, key = lambda octet : socket.inet_aton(octet))
        sorted_cname_list = sorted(unsorted_cname_list)
        prevent_dupes = []  # Prevents cnames that point to the same hostname from appearing more than once each
        for cname in sorted_cname_list:
            mapping_objs = Mapping.objects.filter(ip_or_cname = cname)
            for obj in mapping_objs:
                if '%s,%s' % (obj.hostname, cname) not in prevent_dupes:
                    response.write("%s\t%s\t\t%s\n" % (obj.record_type, obj.hostname, cname))
                    prevent_dupes.append('%s,%s' % (obj.hostname, cname))
        for ip in sorted_ip_list:
            # obj = Mapping.objects.get(ip_or_cname = ip)
            objs = Mapping.objects.filter(ip_or_cname = ip)
            for obj in objs:
                response.write("%s\t%s\t\t%s\n" % (obj.record_type, ip, obj.hostname))
    return response


def text_reverse(request, name):
    '''
    Displays data for reverse text view. Index redirects here.
    Generates IP list from model, reverses each IP in the list and appends the .in-addr.arpa suffix
    Returns direct response in plaintext format

    arguments:
        request: request object
        name: subnet name
    '''
    response = HttpResponse(content_type='text/plain')
    if not Mapping.objects.filter(subnet_id = name):
        response.write("ERROR: NO SUBNET WITH NAME: %s FOUND textreverse" % name)
    else:
        mapping = Mapping.objects.filter(subnet_id = name)
        unsorted_ip_list = []
        for obj in mapping:
            if pylib.is_valid_ip(obj.ip_or_cname):
                unsorted_ip_list.append(obj.ip_or_cname)
        sorted_ip_list = sorted(unsorted_ip_list, key = lambda octet : socket.inet_aton(octet))
        header = pylib.get_header('@')
        response.write(header)
        for ip in sorted_ip_list:
            reversed_ip = pylib.reverse_ip(ip)
            # obj = Mapping.objects.get(ip_or_cname = ip)
            objs = Mapping.objects.filter(ip_or_cname = ip)
            for obj in objs:
                subnet_model = Subnet.objects.get(subnet_name = str(obj.subnet_id))
                response.write("{0:<30}{1}".format(reversed_ip + ".in-addr.arpa.", "IN\tPTR\t" + obj.hostname + "." + subnet_model.domain + ".\n"))
    return response


def text_all(request, domain_name):
    '''
    Displays data for selected domain in text format. Index redirects here.
    Collects all subnets in the given domain and return direct response with the data

    arguments:
        request: request object
        domain_name: domain name
    '''
    response = HttpResponse(content_type='text/plain')
    subnet_name = Subnet.objects.filter(domain = domain_name)
    if not subnet_name:
        response.write("ERROR: NO DOMAIN WITH NAME: %s FOUND" % domain_name)
    else:
        header = pylib.get_header(domain_name + '.')
        response.write(header)
        for obj in subnet_name:
            mapping = Mapping.objects.filter(subnet_id = obj.subnet_name)
            for record in mapping:
                response.write('{0:<30}{1}{2}\n'.format(record.hostname, 'IN\t%s\t' % record.record_type, record))
    return response


def html_ip(request, name):
    '''
    Displays the sorted by IP data in html format. (NOTE: should combine this into one function with html_ name)
    Collects IPs and CNAMES from the model and sorts them
    Returns render with sorted_ip list, sorted_cname list, sort_by order, subnet name, subnet_info, total_ips,
    total_registered_ips, available_ips, proper name (This info is created in pylib.py and used in the header of the page to render)

    arguments:
        request: request object
        name: subnet name
    '''
    sortby = 'ip'
    subnet_info = Subnet.objects.get(subnet_name = name)
    proper_name = subnet_info.proper_name
    mapping = Mapping.objects.filter(subnet_id = name)
    ip_host_list = []
    cname_host_list = []
    for obj in mapping:
        if pylib.is_valid_ip(obj.ip_or_cname):
            ip_host_list.append((obj.ip_or_cname, obj.hostname))
        else:
            cname_host_list.append((obj.hostname, obj.ip_or_cname))
    total_ips = pylib.determine_total_num_ips(subnet_info.ip_range_start, subnet_info.ip_range_end)
    total_registered_ips = len(ip_host_list)
    available_ips = total_ips - total_registered_ips
    sorted_list = sorted(ip_host_list, key = lambda octet : socket.inet_aton(octet[0]))
    context = {'sorted_list' : sorted_list, 'cname_host_list' : cname_host_list, 'sortby' : sortby, 'subnet_name' : name, 'subnet_info' : subnet_info, 'total_ips' : total_ips, 'total_registered_ips' : total_registered_ips, 'available_ips' : available_ips, 'proper_name' : proper_name}
    return render(request, 'pdns/html.html', context)


def html_name(request, name):
    '''
    Displays the sorted by name data in html format. (NOTE: should combine this into one function with html_ ip)
    See html_ip above - info is the same, sort order is by hostname rather than IP
    '''
    sortby = 'name'
    subnet_info = Subnet.objects.get(subnet_name = name)
    proper_name = subnet_info.proper_name
    mapping = Mapping.objects.filter(subnet_id = name)
    ip_host_list = []
    cname_host_list = []
    for obj in mapping:
        if pylib.is_valid_ip(obj.ip_or_cname):
            ip_host_list.append((obj.ip_or_cname, obj.hostname))
        else:
            cname_host_list.append((obj.hostname, obj.ip_or_cname))
    total_ips = pylib.determine_total_num_ips(subnet_info.ip_range_start, subnet_info.ip_range_end)
    total_registered_ips = len(ip_host_list)
    available_ips = total_ips - total_registered_ips
    sorted_list = sorted(ip_host_list, key = lambda name : name[1])
    context = {'sorted_list' : sorted_list, 'cname_host_list' : cname_host_list, 'sortby' : sortby, 'subnet_name' : name, 'subnet_info' : subnet_info, 'total_ips' : total_ips, 'total_registered_ips' : total_registered_ips, 'available_ips' : available_ips, 'proper_name' : proper_name}
    return render(request, 'pdns/html.html', context)


def add_new(request, name, number):
    '''
    Creates formset and data for new entry page. Will create the selected number of new forms for new entries

    arguments:
        request: request object
        name: subnet_name
        number: number of new entry forms to create
    '''
    pylib.backup_database()
    MappingFormSet = formset_factory(MappingForm, extra=int(number), formset=RequiredFormSet)
    if request.method == 'POST':
        additions = []
        formset = MappingFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                new_entry = form.save(commit = False)
                new_entry.subnet_id = name
                if new_entry.ip_or_cname == '':
                    new_entry.ip_or_cname = pylib.get_available_ip(name)
                if not pylib.is_valid_ip(new_entry.ip_or_cname):
                    new_entry.record_type = 'CNAME'
                additions.append('%s, %s, %s' % (new_entry.record_type, new_entry.ip_or_cname, new_entry.hostname))
                new_entry.save()
            add_messages(request, additions, 'add')
            print 'name=', name
            domain_name = Subnet.objects.filter(subnet_name=name)[0].domain
            save_success = pylib.write_domain_zone_file(domain_name, name)
            if not save_success:
                messages.error(request, 'ERROR: THE ZONE FILE DID NOT PASS NAMED-CHECKZONE. NO CHANGES SAVED')
                pylib.restore_database()
                return HttpResponseRedirect('/privatedns/index/error/')
            CHANGELOG.save(request)
            return HttpResponseRedirect('/privatedns/index/summary/')
        else:
            print formset.errors
    else:
        formset = MappingFormSet()
    proper_name_obj = Subnet.objects.get(subnet_name=name)
    proper_name = proper_name_obj.proper_name
    context = {'formset' : formset, 'subnet_name' : name, 'number' : number, 'proper_name' : proper_name}
    return render(request, 'pdns/add_new.html', context)


def modify_all(request, name):
    '''
    Creates formset and populates data for modify_all page
    Records the changes that are made as appropriate
    '''
    pylib.backup_database()
    MappingModelFormSet = modelformset_factory(Mapping, form=ModifyAllForm, can_delete=True, extra=0)
    if request.method == 'POST':
        deletions = []
        modifications = []
        formset = MappingModelFormSet(request.POST)
        if formset.is_valid():
            for form in formset:    # Adds the subnet name and sets the record_type for each database entry
                modified_data = form.save(commit = False)
                modified_data.subnet_id = name
                if not pylib.is_valid_ip(modified_data.ip_or_cname):
                    modified_data.record_type = 'CNAME'
                if form.changed_data and form not in formset.deleted_forms:
                    modifications.append('%s, %s, %s' % (modified_data.record_type, modified_data.ip_or_cname, modified_data.hostname))
                modified_data.save()
            deletions += pylib.remove_dependent_cnames(name, formset.deleted_forms)
            formset.save()  # Have to call this in 1.6 in order to delete the selected forms
            modifications, deletions = remove_mod_message_for_deleted(modifications, deletions)
            add_messages(request, deletions, 'del')
            add_messages(request, modifications, 'mod')
            domain_name = Subnet.objects.filter(subnet_name=name)[0].domain
            save_success = pylib.write_domain_zone_file(domain_name, name)
            if not save_success:
                messages.error(request, 'ERROR: THE ZONE FILE DID NOT PASS NAMED-CHECKZONE. NO CHANGES SAVED')
                pylib.restore_database()
                return HttpResponseRedirect('/privatedns/index/error/')
            CHANGELOG.save(request)
            return HttpResponseRedirect('/privatedns/index/summary/')
        else:
            print formset.errors
    else:
        formset = MappingModelFormSet(queryset = Mapping.objects.filter(subnet = name))
    proper_name_obj = Subnet.objects.get(subnet_name=name)
    proper_name = proper_name_obj.proper_name
    context = {'formset' : formset, 'subnet_name' : name, 'proper_name' : proper_name}
    return render(request, 'pdns/modify_all.html', context)


def add_messages(request, message_list, msg_type):
    '''
    Takes a list of messages, prepends the appropriate change type and adds them to the changelog object

    arguments:
        message_list: list of message strings
        mdg_type: one of: del, mod, add
    '''
    if msg_type == 'del':
        for message in message_list:
            messages.info(request, 'DELETED: ' + message)
            CHANGELOG.add('DELETED: ' + message, request.META['REMOTE_USER'])
    if msg_type == 'mod':
        for message in message_list:
            messages.info(request, 'MODIFIED: ' + message)
            CHANGELOG.add('MODIFIED: ' + message, request.META['REMOTE_USER'])
    if msg_type == 'add':
        for message in message_list:
            messages.info(request, 'ADDED: ' + message)
            CHANGELOG.add('ADDED: ' + message, request.META['REMOTE_USER'])


def remove_mod_message_for_deleted(modifications, deletions):
    '''
    If an entry is deleted it will appear as both a MODIFY and DELETE. This removes the message from MODIFY and only shows as deleted
    '''
    for record in deletions:
        if record in modifications:
            modifications.remove(record)
    return modifications, deletions


def mod_single_record(request, name, record):
    '''
    Creates the form and populates the data for a single selected entry
    '''
    pylib.backup_database()
    RecordModelFormSet = modelformset_factory(Mapping, form = RecordForm, can_delete=True, extra=0)
    if request.method == 'POST':
        deletions = []
        modifications = []
        formset = RecordModelFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                modified_data = form.save(commit=False)
                modified_data.subnet_id = name
                if not pylib.is_valid_ip(modified_data.ip_or_cname):
                    modified_data.record_type = 'CNAME'
                modifications.append('%s, %s, %s' % (modified_data.record_type, modified_data.ip_or_cname, modified_data.hostname))
                modified_data.save()
            deletions += pylib.remove_dependent_cnames(name, formset.deleted_forms)
            formset.save() # FYI - when testing, use a valid IP format. is_valid() will change the record_type to CNAME if not and you get an error when save() cant delete the obj
            modifications, deletions = remove_mod_message_for_deleted(modifications, deletions)
            add_messages(request, deletions, 'del')
            add_messages(request, modifications, 'mod')
            domain_name = Subnet.objects.filter(subnet_name=name)[0].domain
            save_success = pylib.write_domain_zone_file(domain_name, name)
            if not save_success:
                messages.error(request, 'ERROR: THE ZONE FILE DID NOT PASS NAMED-CHECKZONE. NO CHANGES SAVED')
                pylib.restore_database()
                return HttpResponseRedirect('/privatedns/index/error/')
            CHANGELOG.save(request)
            return HttpResponseRedirect('/privatedns/index/summary/')
        else:
            print formset.errors
    else:
        formset = RecordModelFormSet(queryset = Mapping.objects.filter(hostname=record))
    proper_name_obj = Subnet.objects.get(subnet_name=name)
    proper_name = proper_name_obj.proper_name
    context = {'formset' : formset, 'subnet_name' : name, 'record' : record, 'proper_name' : proper_name}
    return render(request, 'pdns/modify_single_record.html', context)


def mod_single(request, name):
    '''
    Redirects to the mod single record if data is posted. Creates data for jquery autocomplete page
    '''
    mapping_objs = Mapping.objects.filter(subnet=name)
    subnet_obj = Subnet.objects.get(subnet_name=name)
    proper_name = subnet_obj.proper_name
    if request.method == 'POST':
        record = request.POST['record']
        return HttpResponseRedirect('/privatedns/modify/single/%s/%s' % (name, record))
    else:
        name_list = []
        for obj in mapping_objs:
            name_list.append("%s" % obj.hostname)
        context = {'names' : name_list, 'subnet_name' : name, 'proper_name' : proper_name}
    return render(request, 'pdns/modify_single.html', context)


def error_display(request):
    '''
    Directs to error html page
    '''
    return render(request, 'pdns/error.html')


def summary_display(request):
    '''
    Directs to summary/success html page
    '''
    return render(request, 'pdns/summary.html')


def changelog(request):
    '''
    Displays the changelog data in text format
    '''
    f = open(OUTPUT_PATH + 'changelog.txt' , 'r')
    data = f.read()
    f.close()
    content = data
    return HttpResponse(content, content_type='text/plain')



"""                                             TESTING                                                 """

def index2(request):
    if request.method == 'POST':
        name = 'THIS IS FANTASTIC'
        return render(request, 'pdns/index2.html', {'name' : name})
    else:
        form = IndexForm()
    return render(request, 'pdns/index2.html', {'form' : form})


def host(request, name):
    objs = Mapping.objects.all()
    for i in objs:
        if i.hostname == name:
            return HttpResponse(i.hostname)
    return HttpResponse('ERROR: NOTHING FOUND')


def bulkadd(request):
    '''If original privatedns hashed database files are copied to the databases directory, and you navigate to /privatedns/bulkcreate
       on the website, this will attempt to migrate the data from those databases into the sqlite database.
       Some formatting of the data will need to be done form the admin console after import'''
    path = '/var/www/html/network/mgmt_network/djangodns/privatedns/databases/'

    for root, dirs, filenames in os.walk(path):
        file_list = filenames

    for f in file_list:
        name = path + f
        sname = f[:-4]
        success_file = open('/var/www/html/network/mgmt_network/djangodns/privatedns/succes.txt', 'a')
        success_file.write('opening file: %s\n' % name)
        success_file.close()
        db = anydbm.open(name, 'r')

        new_subnet = Subnet(subnet_name=sname, ip_range_start='1.1.1.1', ip_range_end='2.2.2.2', domain='wharton.private', network_letter='a')
        new_subnet.save()

        for key in db:
            if 'CNAME:' in db[key]:
                new_entry = Mapping(subnet_id=sname, ip_or_cname=db[key][6:], hostname=key, record_type='CNAME')
            else:
                new_entry = Mapping(subnet_id=sname, ip_or_cname=key, hostname=db[key])
            new_entry.save()
    return HttpResponse('Success')

def auto_populate(request):
    n = '"one","two","three","four"'
    context = {'name' : n}
    return render(request, 'pdns/modify_single.html', context)
