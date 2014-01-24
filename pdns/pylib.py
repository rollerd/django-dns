from pdns.models import Subnet, Mapping
import re
import time
import netaddr
from django.db.models import Q
import subprocess
import glob
import os
import datetime
from django.core.mail import send_mail, EmailMessage

#This file contains various functions that are called from the views.py file

# These two globals set the path to the zonefiles output directory and the path to the sqlite database directory
OUTPUT_PATH = '/var/www/html/network/mgmt_network/djangodns/privatedns/pdns/output/'
BACKUP_PATH = '/var/www/html/network/mgmt_network/djangodns/privatedns/pdns/'


class Changelog():
    '''
    This class allows creation of the  object that is used to write the changes to a changelog
    and send the changes via email. Stores the changes in memory until they are written, just in case the
    zone files are not correct.

    '''
    def __init__(self):
        '''
        Creates empty list for storing changes temporarily
        '''
        self.pending_changes = []
    def add(self, change, username):
        '''
        Adds change to the pending list
        arguments:
            username: the request.META['REMOTE_USER'] that django gets from apache
            change: the change to append
        '''
        user = username.split('!!')[0].upper() + ', '
        self.pending_changes.append(user + change)
    def save(self, request):
        '''
        Saves the actual changes that are pending to a file
        Once a change is submitted and validated, this formats the changelog and
        email entries and saves/emails the change

        arguments:
            request: the request data for the session
        '''
        username = request.META['REMOTE_USER']  #Gets the username from the django env
        user = username.split('!!')[0]
        self.email_entries = []
        t = datetime.datetime.now()
        entry_info = '%d-%d-%d %d:%d:%d, ' % (t.year, t.month, t.day, t.hour, t.minute, t.second)
        f = open(OUTPUT_PATH + 'changelog.txt', 'a')
        for change in self.pending_changes:
            full_entry = entry_info + change + '\n'
            f.write(full_entry)
            self.email_entries.append(full_entry)
        f.close()
        send_email(self.email_entries, user)
        self.pending_changes = []
        self.email_entries = []


def send_email(changes, user):
    '''
    Emails the changes to the user

    arguments:
        changes: list of changes
        user: username
    '''
    current_time = time.time()
    email_address = user + '@wharton.upenn.edu'
    subject = "Subject: SPOT IP Management Changes: %s" % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)))
    message_body = '\n'.join(changes)
    email = EmailMessage(subject, message_body, email_address, [email_address], headers = {'Reply-To': 'donotreply@wharton.upenn.edu'})
    email.send()


def is_valid_ip(ip_to_check):
    '''
    Checks to see that ip_to_check looks like an ip string and falls within the 0-255 range for each octet
    Returns 1 if ip_to_check looks like a valid IP, 0 if not

    arguments:
        ip_to_check: IP address string
    '''
    is_correct_format = re.match(r'^([\d]{1,3})\.([\d]{1,3})\.([\d]{1,3})\.([\d]{1,3})$', ip_to_check)
    if is_correct_format:
        for octet in range(1,5):
            if int(is_correct_format.group(octet)) < 0 or int(is_correct_format.group(octet)) > 255:
                return 0
        return 1
    else:
        return 0


def remove_dependent_cnames(subnet_name, formset_deleted_forms):
    '''
    When we delete an A record, we would like to delete any CNAMEs that pointed to the hostname associated with A record.
    NOTE: If there are other CNAMEs pointing to the CNAME being removed however, this function will not remove them.
          That will need to be done manually or this function will need to be made more robust
    Returns list of removed entries

    arguments:
        subnet_name: subnet_name string
        formset_deleted_forms: the deleted_forms subset of a formset
    '''
    removed_entries = []
    for obj in formset_deleted_forms:
        obj_ip, obj_hostname, obj_record = obj['ip_or_cname'].value(), obj['hostname'].value(), obj['record_type'].value()
        removed_entries.append('%s, %s, %s' % (obj_record, obj_ip, obj_hostname))
        if obj_record == 'A':
            removed = clean_names(subnet_name, obj_ip, obj_hostname)
            for entry in removed:
                removed_entries.append(entry)
    return removed_entries


def clean_names(name, ip, hostname):
    '''
    Does the actual removal of the related CNAMES for remove_dependent_cnames() function.
    Creates queryset using Q to find data (see docs on django Q)
    Returns a list of the removed mappings

    arguments:
        name: subnet_name
        ip: ip address to search the database for
        hostname: hostname for use in finding CNAME matches
    '''
    cleaned_cnames = []
    query = Q(ip_or_cname = ip) | Q(ip_or_cname = hostname)
    mapping_objs = Mapping.objects.filter(query)
    for obj in mapping_objs:
        if obj.record_type != 'A':      #Will only delete CNAME records
            cleaned_cnames.append('%s, %s, %s' % (obj.record_type, obj.ip_or_cname, obj.hostname))
            obj.delete()
    return cleaned_cnames


def get_available_ip(name):
    '''
    Gets the next available IP in the subnet range.
    NOTE: This could be improved!
          It is slow and creates a list of all the IPs in the range as well as all of the used IPs
    Runs a while loop through the generated IP list until it finds an address that is not used
    Returns next available IP

    arguments:
        name: subnet_name
    '''
    subnet_info_obj = Subnet.objects.get(subnet_name=name)
    mapping_objs = Mapping.objects.filter(subnet=name)
    ip_start = subnet_info_obj.ip_range_start
    ip_end = subnet_info_obj.ip_range_end
    used_ip_list = []
    for obj in mapping_objs:    #Create list of used IPs
        used_ip_list.append(obj.ip_or_cname)
    index = 0
    ip_range = list(netaddr.iter_iprange(ip_start, ip_end)) #Create the actual list of all IPs in the range
    next_ip = str(ip_range[index])
    while next_ip in used_ip_list:
        index += 1
        next_ip = str(ip_range[index])
    return next_ip


def get_domains():
    '''
    Queries Subnet model and returns all distinct domain names
    Returns a list of the distinct domain names
    '''
    subnet_objs = Subnet.objects.all()
    domain_list = []
    for obj in subnet_objs:
        if obj.domain not in domain_list:
            domain_list.append(obj.domain)
    return domain_list


def determine_total_num_ips(ip_range_start, ip_range_end):
    '''
    Determines the total number of usable IPs from the start and end range numbers
    Returns total number of IPs in range
    NOTE: This function may not be calculating correctly.
          Though it is not used by any other functions, it would be nice to have its output
          so that the user can see the size of the range and remaining # of IPs

    arguments:
        ip_range_start: ip address string representing the beginning of the range
        ip_range_end: ip address string representing the end of the range
    '''
    soctet1, soctet2, soctet3, soctet4 = (int(i) for i in ip_range_start.split('.'))
    eoctet1, eoctet2, eoctet3, eoctet4 = (int(i) for i in ip_range_end.split('.'))
    a, b, c, d = 0, 0, 0, 0
    if eoctet1 - soctet1 != 0:
        a = eoctet1 - soctet1
    if eoctet2 - soctet2 != 0:
        b = eoctet2 - soctet2
    if eoctet3 - soctet3 != 0:
        c = eoctet3 - soctet3
    if eoctet4 - soctet4 != 0:
        d = eoctet4 - soctet4
    total_ips = 0
    for o1 in range(0, a + 1):
        for o2 in range(0, b + 1):
            if c + 1 > 1:
                for o3 in range(0, c):
                    total_ips += 255
            else:
                pass
    if d == 255:
        total_ips += 254
    else:
        total_ips += d
    return total_ips


def backup_database():
    '''
    Copies the sqlite database file and names it *.bkup
    '''
    subprocess.call(['cp', '/var/www/html/network/mgmt_network/djangodns/privatedns/db.sqlite3', '/var/www/html/network/mgmt_network/djangodns/privatedns/db.sqlite3.bkup'])


def restore_database():
    '''
    Restores the sqlite database *.bkup file
    '''
    subprocess.call(['cp', '/var/www/html/network/mgmt_network/djangodns/privatedns/db.sqlite3.bkup', '/var/www/html/network/mgmt_network/djangodns/privatedns/db.sqlite3'])


def backup_zone_files():
    '''
    Backs up the output directory in case of failed named check
    Does the actual work of tar-ing the output directory.
    Keeps 3 versions of the output directory just in case.
    '''
    backup_filenames = glob.glob('/var/www/html/network/mgmt_network/djangodns/privatedns/pdns/output*.tar')
    print 'backup filenames', backup_filenames
    if len(backup_filenames) >= 3:
        backup_filenames.sort()
        os.remove('%s' % backup_filenames[0])
    t = time.time()
    subprocess.call(['tar', '-cf', BACKUP_PATH + 'output.%d.tar' % t, '-C', BACKUP_PATH + 'output', '.'])


def restore_backup():
    '''
    Restores the latest output directory in case of a failed named-checkzone
    Does the actual work of un-tar-ing the output directory
    Overwrites the current/bad output directory
    '''
    backup_filenames = glob.glob('/var/www/html/network/mgmt_network/djangodns/privatedns/pdns/output*.tar')
    print 'restore backup filenames', backup_filenames
    backup_filenames.sort()
    subprocess.call(['tar', '-xf', '%s' % backup_filenames[-1], '-C', OUTPUT_PATH])


def write_domain_zone_file(domain_name, subnet_name):
    '''
    Writes the domain zone file
    Backs up the current zone.domain.name file and overwrites the remaining copy
    Calls the valid_zone_file check and restores the backed up file if it fails
    Returns 1 if the file writes and passes checks, 0 if not

    arguments:
        domain_name: name of the domain
        subnet_name: name of the modified subnet
    '''
    backup_zone_files()
    subnet_objs = Subnet.objects.filter(domain=domain_name)
    zonefilename = 'zone.' + domain_name
    zone_file = open(OUTPUT_PATH + '%s' % zonefilename, 'w') #Overwrite the existing file/create it if it doesnt exist
    write_zone_file_header(zone_file, domain_name + '.')
    for subnet in subnet_objs:
        mapping_obj = Mapping.objects.filter(subnet_id=subnet.subnet_name)
        for record in mapping_obj:
            zone_file.write('{0:<30}{1}{2}\n'.format(record.hostname, 'IN\t%s\t' % record.record_type, record))
    zone_file.close()
    if not valid_zone_file(zonefilename, domain_name):
        restore_backup()
        return 0
    write_reverse_zone_files(subnet_name, domain_name)
    return 1


def write_reverse_zone_files(subnet_name, domain_name):
    '''
    Writes reverse zone files for each modified IP range
    Checks to see which subnet ranges have been modifed, and creates/re-writes the
    reverse addresses for those subnets ex '1.100.10.in-addr.apra'

    arguments:
        subnet_name: name of the modified subnet
        domain_name: name of the domain ex 'wharton.private'
    '''
    mapping_objs = Mapping.objects.filter(subnet_id=subnet_name)
    reverse_zone_ip_list = []
    for obj in mapping_objs:
        if obj.record_type == 'CNAME':  #Only need the IP/A record addresses for reverse zone file
            pass
        else:
            zone_ip = reverse_zone_ip(obj.ip_or_cname)
            reversed_ip = reverse_ip(obj.ip_or_cname)
            zonefilename = zone_ip.rstrip('.')
            if zone_ip not in reverse_zone_ip_list:     #If the range doesn't already exist in our list create the file, write the header and add it
                reverse_zone_ip_list.append(zone_ip)
                zone_file = open(OUTPUT_PATH + '%s' % zonefilename, 'w')
                write_zone_file_header(zone_file, '@')
                zone_file.write("{0:<30}{1}".format(reversed_ip + '.in-addr.arpa.', "IN\tPTR\t" + obj.hostname + "." + domain_name + ".\n"))
                zone_file.close()
            else:       #If the range does exist, just add the address to the existing file
                zone_file = open(OUTPUT_PATH + '%s' % zonefilename, 'a')
                zone_file.write("{0:<30}{1}".format(reversed_ip + '.in-addr.arpa.', "IN\tPTR\t" + obj.hostname + "." + domain_name + ".\n"))
                zone_file.close()


def valid_zone_file(zonefilename, domain_name):
    '''
    Runs a named-checkzone check against the domain zone file.
    NOTE:
        named-checkzone command returns 1 if there are errors found and 0 if not.
        HOWEVER - This function returns 1 if there are no errors and 0 if there are errors

    arguments:
        zonefilename: name of the zonefile to check
        domain_name: name of the domain the zone file is for ex 'wharton.private'
    '''
    errors_found = False
    if subprocess.call(['named-checkzone', '-q', domain_name, OUTPUT_PATH + zonefilename]):
        errors_found = True
        #print 'ERRORS IN DOMAIN ZONE FILE FOUND'
    if errors_found:
        return 0
    else:
        #print "NO ERRORS FOUND"
        return 1


def get_reverse_list(ip_list):
    '''
    Reverses a list of ip addresses and returns the reversed list for use in
    reverse zone files/views

    arguments:
        ip_list: list of ip's in string format '['xxx.xxx.xxx.xxx', ...]'
    '''
    reversed_list = []
    for ip in ip_list:
        reverse_address = reverse_ip(ip)
        reversed_list.append(reverse_address)
    return reversed_list


def reverse_ip(ip):
    '''
    Reverses an individual ip address
    Returns the reversed IP

    arguments:
        ip: ip address in string format 'xxx.xxx.xxx.xxx'
    '''
    octet1, octet2, octet3, octet4 = ip.split(".")
    reversed_ip = octet4 + '.' + octet3 + '.' + octet2 + '.' + octet1
    return reversed_ip


def reverse_zone_ip(ip):
    '''
    Reverses an individual IP string and appends .in-addr.arpa for use in reverse
    zone file
    Returns reversed IP with the .in-addr.arpa appended

    arguments:
        ip: ip address in string format 'xxx.xxx.xxx.xxx'
    '''
    octet1, octet2, octet3, octet4 = ip.split(".")
    reversed_ip = octet3 + '.' + octet2 + '.' + octet1 + '.in-addr.arpa.'
    return reversed_ip


def write_zone_file_header(zone_file, domain_name):
    '''
    Writes the zone file header to the given file with the appropriate domain name

    arguments:
        zonefile: an actual open file object for the appropriate zone
        domain_name: name of the domain
    '''
    header = get_header(domain_name)
    zone_file.write(header)


def get_header(origin):
    '''
    Creates the header for the zone file with the appropriate origin and the time
    in seconds since the epoch as the serial number.
    Returns header string pre-formatted

    arguments:
        origin: Either '@' or the domain name in 'domain.name.' format
    '''
    header = "$ttl 38400\n\
%s\tIN\tSOA\tastra.wharton.upenn.edu. core-systems.wharton.upenn.edu. (\n \
\t\t\t%d\n \
\t\t\t10800\n \
\t\t\t3600\n \
\t\t\t604800\n \
\t\t\t86400 )\n" % (origin, time.time()) + \
"{0:<30}{1}\n".format('', 'IN\tNS\tastra.wharton.upenn.edu.') + \
"{0:<30}{1}\n".format('', 'IN\tNS\tpolaris.wharton.upenn.edu.')
    return header
