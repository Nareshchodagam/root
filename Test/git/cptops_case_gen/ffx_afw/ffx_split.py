import argparse
from idbhost import Idbhost
parser = argparse.ArgumentParser()

def buddy_find(host):
    """
    This function is used to check the status of app on buddy host.
    :param host: hostname to check the buddy
    :return: Buddy Host
    """
    hs = host.split('-')
    site, cluster,hostprefix, hostnum = hs[-1], hs[0], hs[1][-1], hs[2]

    if hostprefix == '1':
        buddyprefix = '2'
    elif hostprefix == '2':
        buddyprefix = '1'
    elif hostprefix == '5':
        buddyprefix = '6'
    elif hostprefix == '6':
        buddyprefix = '5'

    buddyhost = '%s-ffx%s-%s-%s' % (cluster, buddyprefix, hostnum, site)
    return buddyhost

def idb_values(dc_name,clust_name):

    idb.clustinfo(dc_name,clust_name)
    idb.deviceRoles('ffx')
    data = idb.roles_all
    for batch,hostlist in data.items():
        for role,hosts in hostlist.items():
            print "%s \n%s \n%s" %(batch,role,hosts)
            return hosts,batch,role

parser.add_argument("-H", dest="hosts")
parser.add_argument("-F", dest="file")
parser.add_argument("-C", dest="clust_name")
parser.add_argument("-D", dest="dc_name")
parser.add_argument("-S", dest="sp")

args = parser.parse_args()
idb = Idbhost()

clust_name = args.clust_name
dc_name = args.dc_name
sp = args.sp

#open('primary.txt', 'w').close()
#open('secondary.txt', 'w').close()
primary = []
secondary = []
if args.hosts:
    hosts = args.hosts
    hosts = hosts.split(',')
    for host in hosts:
        buddy = buddy_find(host)
        if host not in primary and host not in secondary:
            primary.append(host)
            with open('primary.txt', 'a') as pri:
                pri.write(host +"\n")
            secondary.append(buddy)
            with open('secondary.txt', 'a') as sec:
                sec.write(buddy+"\n")
elif args.file:
    file = args.file
    with open(file, 'r') as raw:
        hosts = raw.readlines()
    for host in hosts:
        buddy = buddy_find(host)
        if host not in primary and host not in secondary:
            primary.append(host)
            with open('primary.txt', 'a') as pri:
                pri.write(host)
            secondary.append(buddy)
            with open('secondary.txt', 'a') as sec:
                sec.write(buddy)
else:
    hosts, batch, role = idb_values(dc_name, clust_name)
    #open('batch' + batch + '-1.txt', 'w').close()
    #open('batch' + batch + '-2.txt', 'w').close()
    for host in hosts:
        buddy = buddy_find(host)
        #idb.gethost(host)
        #sp = idb.mlist[host]['superpod']
        if host not in primary and host not in secondary:
            primary.append(host)
            with open("batchfiles/"'batch' + batch + '-1.txt', 'a') as pri:
                pri.write(batch + "-1," + host + "," + dc_name + "-" + sp + "," + clust_name + "-" + dc_name + "\n")
            secondary.append(buddy)
            with open("batchfiles/"'batch' + batch + '-2.txt', 'a') as sec:
                sec.write(batch + "-2," + buddy + "," + dc_name + "-" + sp + "," + clust_name + "-" + dc_name + "\n")