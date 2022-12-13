from optparse import OptionParser
import logging
import re
import shutil
import os
import subprocess
import socket
from common import Common
from idbhost import Idbhost


common = Common
idb = Idbhost()


# Intiliazie the lists
HOSTS_CPS = []
HOSTS_DSTORE = []
HOSTS_MSG = []
HOSTS = []


# Function to write in file
def write_to_file(filename, mode, data):
    fp = open(filename, mode)
    fp.write(data)
    fp.flush()
    fp.close()


# Clear the list to add  servers of group2
def clearList():
    del HOSTS_CPS[:]
    del HOSTS_DSTORE[:]
    del HOSTS_MSG[:]
    del HOSTS[:]


# Assign hostnames based on hostfunc to the appropriate lists
def build_Hostlist(hostname):
    global v_HOSTNAME_CPS
    global v_HOSTNAME_DSTORE
    global v_HOSTNAME_MSG
    global v_HOSTS
    if re.search(r'prsn|chan|sshare', hostname):
        HOSTS_CPS.append(hostname)
    elif re.search(r'dstore', hostname):
        HOSTS_DSTORE.append(hostname)
    elif re.search(r'msg', hostname):
        HOSTS_MSG.append(hostname)
    HOSTS = HOSTS_CPS + HOSTS_DSTORE + HOSTS_MSG

    v_HOSTNAME_CPS = ",".join(HOSTS_CPS)
    v_HOSTNAME_DSTORE = ",".join(HOSTS_DSTORE)
    v_HOSTNAME_MSG = ",".join(HOSTS_MSG)
    v_HOSTS = ",".join(HOSTS)


# Remove existing output directory and create new one
def recreate_dir(dirname):
    if os.path.isdir(dirname):
        shutil.rmtree(dirname)
        os.mkdir(dirname)
    else:
        os.mkdir(dirname)


# Appned the DC and CLUSTER name to the plan
def add_dc_cluster(cluster,filename,state):
    out_file="output/" + filename
    if state is 'BEGIN':
        data = "\t" + 'BEGIN_GROUP: %s\n\n' % cluster
        write_to_file(out_file,"a+",data)
    elif state is 'END':
        data = "\t" + 'END_GROUP: %s\n' % cluster
        write_to_file(out_file,"a+",data)
    else:
        raise Exception('XXXX')


def gen_hostlist(hosts_list):
    return ",".join(hosts_list)



# Do not add unavailable hosts in the  impl plan
def remove_down_hosts(hlist, downlist):
    for host in downlist:
        if host in hlist['g1']:
            hlist['g1'].remove(host)
        if host in hlist['g2']:
            hlist['g2'].remove(host)
    return hlist


# Generate the impl plan
def gen_plan(sp, cluster, dc, role, bundle):
    template_file = options.gensetup
    #template_file ="../templates/" + role + ".linux.template"
    s = open(template_file).read()
    s = s.replace('v_HOSTNAME_CPS', v_HOSTNAME_CPS)
    s = s.replace('v_HOSTNAME_DSTORE', v_HOSTNAME_DSTORE)
    s = s.replace('v_HOSTNAME_MSG', v_HOSTNAME_MSG)
    s = s.replace('v_HOSTS', v_HOSTS)
    s = s.replace('v_CLUSTER', cluster)
    s = s.replace('v_DATACENTER', dc)
    s = s.replace('v_SUPERPOD', sp)
    s = s.replace('v_BUNDLE', bundle)
    return s


# Logic to extract the servers from  hostlist on groups basis
def get_hosts(cluster, hostsdict):
    hlist = {}
    hlist['g1'] = []
    hlist['g2'] = []
    for hosts in hostsdict.values():
        for host in hosts:
            if host.split(".")[0].split("-")[-1] == "phx" or host.split(".")[0].split("-")[-1] == "dfw" or \
                            host.split(".")[0].split("-")[-1] == "frf":
                if host.split("-")[1].strip("1234") == "sshare":
                    if host.split("-")[2] == "1" or host.split("-")[2] == "2":
                        hlist['g1'].append(host.rstrip())
                    elif host.split("-")[2] == "3" or host.split("-")[2] == "4":
                        hlist['g2'].append(host.rstrip())
                else:
                    if host.split("-")[2] == "1":
                        hlist['g1'].append(host.rstrip())
                    elif host.split("-")[2] == "2":
                        hlist['g2'].append(host.rstrip())

            elif host.split(".")[0].split("-")[-1] == "lon":
                if host.split("-")[1].strip("1234") == "msg" or  host.split("-")[1].strip("1234") == "dstore":
                    if host.split("-")[2] == "1":
                        hlist['g1'].append(host.rstrip())
                    elif host.split("-")[2] == "2":
                        hlist['g2'].append(host.rstrip())

                else:
                    if host.split("-")[2] ==  "1" or host.split("-")[2] ==  "2":
                        hlist['g1'].append(host.rstrip())
                    elif host.split("-")[2] ==  "3" or host.split("-")[2] ==  "4":
                        hlist['g2'].append(host.rstrip())
            else:
                if host.split("-")[1][-1] == "1":
                    hlist['g1'].append(host.rstrip())
                elif host.split("-")[1][-1] == '2':
                    hlist['g2'].append(host.rstrip())
        return hlist


# Function to retrive the hostlist from idb
def init_Host(dc, cluster):
    idb.clustinfo(dc, cluster)
    hosts = idb.clusterhost
    logging.debug(hosts)
    return hosts


# Function to get the clusters name from idb in a given dc
def get_clusters(dc, sp, op_status):
    idb.sp_info(dc, sp, op_status, 'CHATTER')
    clus_json = idb.spcl_grp
    for key, vals in clus_json.iteritems():
        clusters = vals['Primary'].split(',')
    if 'CHATTERGUS1' in clusters:
        clusters.remove('CHATTERGUS1')
    return clusters


   
#main 
if __name__ == "__main__":
    usage = """
    UMPS patching case implementation plan generation
    
    This code will generate the implementation plan for patching  UMPS servers.
    The arguments required to be passed are superpod, instance, data center and role .
    
    %prog  -s superpod -i instance -d datacenter -r role -g  'umps template file path'
    %prog -s <suporpod> -d <datacenter> -r <role> -g <../templates/umps.linux.template> -d <DC> -b <candidate|current>
    %prog  -s SP1 -i CHATTER5 -d chi -r umps -g templates/umps.template  -d chi -b candidate
    
    """
    parser = OptionParser(usage)
    parser.add_option("-s", "--superpod", dest="superpod", help="The superpod")
    parser.add_option("-b", "--patch_bundle", dest="bundle", help="The patch bundle name")
    parser.add_option("-i", "--cluster", dest="cluster", help="The instance")
    parser.add_option("-o", "--op_status", dest="op_status", help="Operational Status")
    parser.add_option("-d", "--datacenter", dest="datacenter", help="The datacenter")
    parser.add_option("-g", "--gensetup", dest="gensetup", help="test")
    parser.add_option("-r", "--role", dest="role", help="The role")
    parser.add_option("-H", "--host", dest="host", help="The host")
    parser.add_option("-f", "--filename", dest="filename", default="plan_implementation.txt", help="The output filename")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.superpod and options.datacenter and options.role:
        if options.cluster:
            clusters = options.cluster.split(",")
        else:
            clusters = get_clusters(options.datacenter, options.superpod, options.op_status)

        recreate_dir('output')
        out_file = "output/" + options.filename
        data = 'BEGIN_DC: %s\n' % options.datacenter.upper()
        write_to_file(out_file, "a+", data)

        for cluster in clusters:
            hosts = init_Host(options.datacenter, cluster)
            host_list = ",".join(hosts[cluster])
            dstore_list = filter(lambda x: 'dstore' in x, hosts[cluster])
            add_dc_cluster(cluster, options.filename, 'BEGIN')
            with open('../templates/umps.linux.template.pre', 'r') as f_read:
                lines = f_read.read().replace('v_DATACENTER', options.datacenter)
            write_to_file(out_file, "a+", lines + '\n')

            if not filter(lambda x: 'gumps' in x, hosts[cluster]):
                cmd = '\nExec: /opt/rh/python27/root/usr/bin/python2.7 ~/nagios_monitor.py -H %s -c disable -d 4 \n' % (
                    host_list)
                write_to_file('output/' + options.filename, "a+", cmd)
                cmd = '\nExec: /opt/rh/python27/root/usr/bin/python2.7 ~/validate_host-state_nagios.py  -H %s -S ' \
                      'Chatternow-Dstore-STATE -P 8087\n\n' % (",".join(dstore_list))
                write_to_file('output/' + options.filename, "a+", cmd)

                hlist = get_hosts(cluster, hosts)
                for group in sorted(hlist.keys()):
                    for host in hlist[group]:
                        write_to_file('output/summarylist.txt', 'a+', host + '\n')
                        build_Hostlist(host)
                    plan = gen_plan(options.superpod, cluster, options.datacenter, options.role, options.bundle)
                    logging.debug(plan)
                    write_to_file('output/' + options.filename, 'a+', plan)
                    clearList()
                cmd = '\nExec: /opt/rh/python27/root/usr/bin/python2.7 ~/nagios_monitor.py -H %s -c enable\n' % (host_list)
                write_to_file('output/' + options.filename, "a+", cmd)
                add_dc_cluster(cluster, options.filename, 'END')
            else:
                for host in hosts[options.cluster]:
                    write_to_file('output/summarylist.txt', 'a+', host + '\n')
                    build_Hostlist(host)

                plan = gen_plan(options.superpod, cluster, options.datacenter, options.role, options.bundle)
                write_to_file('output/' + options.filename, 'a+', plan)
                add_dc_cluster(cluster, options.filename, 'END')
                #data = 'END_DC: %s\n' % options.datacenter.upper()
                #write_to_file(out_file, "a+", data)
        data = 'END_DC: %s\n' % options.datacenter.upper()
        write_to_file(out_file, "a+", data)
        print "Generating: output/%s" % options.filename

    else:
        usage
