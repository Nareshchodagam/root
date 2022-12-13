#!/usr/bin/python

###############################################################################
#
# Purpose: Check state of shared nfs boxes and ensure the target host is
#          configured to restore state after a reboot.
#
# Usage: %prog -H host1,host2,host3,host4
#
# Requirements: texttable.py
###############################################################################

import os
import socket
import sys
import random
import datetime
import time
from optparse import OptionParser
from os.path import expanduser
import logging
import re
import common
from texttable import Texttable



###############################################################################
#                Constants
###############################################################################

commands = dict(
    # Fill this dict with commands to be executed on the remote hosts.
    # remember to escape variables.
    DFH = "df -h | grep search | grep -v .patchSafeMode | awk '{print \$6}'",
    SHARE = "/usr/sbin/share | awk '{print \$2}'",
    SHOWMOUNT = "/usr/sbin/showmount -e | awk '{print \$1}' | grep -v export",
    ZPOOL_STATUS = "/sbin/zpool status | awk '{print \$1\" \"\$2}'",
    DFSTAB = "grep -v ^# /etc/dfs/dfstab | grep 'ro ' | awk '{print \$6}'",
    VFSTAB = "grep -v ^# /etc/vfstab | grep search | awk '{print \$3}'",
    NFSSVCADM = "/usr/bin/svcs -a | grep 'nfs/server' | awk '{print \$1}'",
    NETSTAT_NFS = "netstat -a | grep nfsd | grep ESTABLISHED | sort -nk1 |\
     awk '{print \$2}' | cut -d'.' -f1 ",
    VFSTAB_AMOUNT = "grep -v ^# /etc/vfstab | grep search | awk '{print \$3,\$6}'",
)


username=os.getlogin()
useremail=username + '@salesforce.com'
home=expanduser("~")
outdir=home + "/output"
ts = time.time()
runtime = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d_%H%M%S')

###############################################################################
#                Functions
###############################################################################

def PrintTable(header,hosts,values):

    # Use the texttable module to print out the data in a tabular format.
    # See texttable.py for further formatting options.

    tf = open(outdir + '/outtable.'+runtime+'.txt','a')
    tablewidth=20
    table = Texttable()
    x=[]
    for i in hosts:
        x.append(tablewidth)
    table.set_cols_width(x)
    table.add_rows([hosts, values],header=False)
    print table.draw() + "\n"
    table.set_chars([' ', ' ', ' ', ' '])
    tf.write('\n'+header+'\n')
    tf.write(table.draw()) # python will convert \n to os.linesep
    tf.close()

def ProposeRemount(connlist):
    totalcount=0
    remove_hosts=[]
    randlist=[]
    hostcount=len(connlist)
    for host in connlist:
        totalcount += len(connlist[host])
    avgcount=totalcount / hostcount

    for host in connlist:
        if len(connlist[host]) > avgcount:
            print host + " is overweight with " + \
            str(len(connlist[host])) + " connections"

            owcount=len(connlist[host])
            newlen=owcount - avgcount

            print "Proposing removing " + str(newlen) + "  records from " +\
            host + "\n"

            for i in range(newlen):
                a=connlist[host]
                remove_hosts.append(a.pop(i))

    print "\n\nAsk netops to delete persistence on the following ips:\n"
    for i in remove_hosts:
        addr = socket.gethostbyname(i)
        print addr


    print "\n\nAfter persistence has been deleted, remount the following hosts:\n"
    for i in remove_hosts:
        print i

def get_site():
    hostname = socket.gethostname()
    logging.debug(hostname)
    inst,hfuc,g,site = hostname.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

def get_inst(hostname):
    logging.debug(hostname)
    inst,hfuc,g,site = hostname.split('-')
    return inst

def get_prod_hosts(hostlist,site):
    prod_hosts= []
    for h in hostlist:
        inst = get_inst(h)
        loc = check_prod(inst,site)
        if loc == 'PROD':
            prod_hosts.append(h)
    return prod_hosts

def check_prod(inst, site):
    host = inst+'-monitor.ops.sfdc.net'
    primary = socket.getfqdn(host)
    logging.debug("site : %s" % site)
    logging.debug("host : %s" % host)
    logging.debug("primary host : %s" % primary)
    pri_site = re.search(r'-(\w{3}).ops.sfdc.net', primary)
    logging.debug("pri_site : %s" % pri_site.group(1))
    if pri_site.group(1) != site:
        return "DR"
    else:
        return "PROD"

def CheckNFSDisabled(host,status_to_check):
    s=status_to_check.strip()
    print "Checking that NFS is " + status_to_check + " on " + host
    NFSSVCADM=commands['NFSSVCADM']
    result=os.popen("ssh  -o StrictHostKeyChecking=no -o \
    ConnectTimeout=5 -n " + host + " \"" + NFSSVCADM + "\" \
    2>/dev/null").read()
    r=result.strip()

    print host + " is reporting NFS status as: " + r
    if r == s:
        sys.exit(0)
    else:
        sys.exit(1)

def CheckVFSvsDFH(host):
    print "Checking that automount is enabled for all currently mounted points on " + host
    VFSTAB_AMOUNT=commands['VFSTAB_AMOUNT']

    # Pull back automount info
    result=os.popen("ssh  -o StrictHostKeyChecking=no -o \
    ConnectTimeout=5 -n " + host + " \"" + VFSTAB_AMOUNT + "\" \
    2>/dev/null").read()
    VFSTAB_AMOUNT=result

    if "no" in VFSTAB_AMOUNT:
        sys.exit(1)
    else:
        sys.exit(0)


###############################################################################
#                Main
###############################################################################

if __name__ == "__main__":

    usage="""

    *** texttable.py must exist in ~/ or ~/includes ***

    Available commands

        DFH = "df -h | grep search | grep -v .patchSafeMode | awk '{print \$6}'",

        SHARE = "/usr/sbin/share | awk '{print \$2}'",

        SHOWMOUNT = "/usr/sbin/showmount -e | awk '{print \$1}' | grep -v export",

        ZPOOL_STATUS = "/sbin/zpool status | awk '{print \$1\" \"\$2}'",

        DFSTAB = "grep -v ^# /etc/dfs/dfstab | grep 'ro ' | awk '{print \$6}'",

        VFSTAB = "grep -v ^# /etc/vfstab | grep search | awk '{print \$3}'",

        VFSTAB_AMOUNT = "grep -v ^# /etc/vfstab | grep search | awk '{print \$3, \$6}'",

        NFSSVCADM = "/usr/bin/svcs -a | grep 'nfs/server' | awk '{print \$1}'",

        NETSTAT_NFS = "netstat -a | grep nfsd | grep ESTABLISHED | sort -nk1 |\

         awk '{print \$2}' | cut -d'.' -f1 ",


    %prog -H host1,host2,host3,host4 -c com1,com2,com3

    All output:
    %prog -H shared-nfs1-1-asg,shared-nfs1-2-asg,shared-nfs2-1-asg,shared-nfs2-2-asg

    For connected ips:
    %prog -H shared-nfs1-1-asg -c NETSTAT_NFS -i

    For proposal
    %prog -H shared-nfs1-1-asg,shared-nfs1-2-asg,shared-nfs2-1-asg,shared-nfs2-2-asg -c NETSTAT_NFS -r

    Exit with return code to check NFS status :
    %prog -H shared-nfs1-1-asg -s online (ret 0 if enabled 1 if disabled)
    %prog -H shared-nfs1-1-asg -s disabled (ret 1 if enabled 0 if disabled)

    Verify automount status
    %prog -H shared-nfs1-1-asg -a (ret 1 if mismatch 0 if match)
    """
    parser = OptionParser(usage)
    parser.add_option("-H", dest="hostlist", default='', help="csv host list")
    parser.add_option("-c", dest="cmdfilter", default=[], help="filter commands")
    parser.add_option("-e", dest="emailresult", action='store_true', default=False,\
                       help="email result (only from -i)")
    parser.add_option("-r", dest="remount", action='store_true', default=False, \
                      help="propose remount")
    parser.add_option("-a", dest="automount", action='store_true', default=False, \
                      help="verify automount status")
    parser.add_option("-s", dest="status_to_check", help="Return status of NFS", \
                      default=False)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                        help="verbose")
    parser.add_option("-i", dest="ips", action='store_true', default=False,\
                       help="convert to ips")


    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.status_to_check:
        CheckNFSDisabled(options.hostlist,options.status_to_check)

    if options.automount:
        CheckVFSvsDFH(options.hostlist)

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    #Filter the commands list to only commands passed as an argument.
    if options.cmdfilter:
        cmdfilter=options.cmdfilter.upper().split(',')
        if cmdfilter != "":
            filteredcmds=dict()
            for newkey in cmdfilter:
                if newkey in commands:
                    filteredcmds[newkey]=commands[newkey]
                else:
                    print "WARNING: '" + newkey + "' is not a recognized command."
            commands=filteredcmds

    # Prepare a data structure for the results.
    results=dict()
    connlist=dict()
    for command in commands:
        results[command]=dict()

    for host in sorted(options.hostlist.split(',')):
        # Execute each command in the commands dict and save it's result
        # into a new dict with the with the key of the command as it's name.
        for key, value in commands.iteritems():
            try:
                connlist[host]=[]
                result=os.popen("ssh  -o StrictHostKeyChecking=no -o \
                ConnectTimeout=5 -n " + host + " \"" + value + "\" \
                2>/dev/null").read()
                results[key][host]=result
                if command== 'NETSTAT_NFS':
                    cl=result.split('\n')
                    cl=[x for x in cl if x]
                    connlist[host]=cl
            except:
                print "Something went wrong with the ssh command."

    for command in commands:
        # Loop through the commands again, assigning the host + cmd output
        # to their own lists.
        currentcommand=results[command]
        if command == 'NETSTAT_NFS' and not options.ips:
            print command + "\n"
        hosts=[]
        values=[]
        site = get_site()
        for host,cmdvalue in sorted(currentcommand.iteritems()):
            hosts.append(host)
            if command == 'NETSTAT_NFS' and options.ips:
                # If the -i flag is set, spit out a list of ips as opposed to a
                # table of hostnames.
                ipvalues=[]
                cmdvalue=cmdvalue.split()
                prod_hosts = get_prod_hosts(cmdvalue,site)
                f=open(outdir +'/del_persistence.txt','w')
                f2=open(outdir +'/neteng_details.txt', 'w')
                #f.truncate()
                #f2.truncate()
                f2.write('\n ---- Hostname -> IP ---- \n\n')
                for i in prod_hosts:
                    addr = socket.gethostbyname(i)
                    f.write(addr + '\n')
                    f2.write(i + ' -> ' + addr + '\n')
                    print addr
                f2.write('\n ---- Show persistence ---- \n\n')
                for i in prod_hosts:
                    addr = socket.gethostbyname(i)
                    f2.write('show ltm persistence persist-records client-addr '\
                              + addr + ' all-properties\n')
                f2.write('\n ---- Delete persistence ---- \n\n')
                for i in prod_hosts:
                    addr = socket.gethostbyname(i)
                    f2.write('delete ltm persistence persist-records client-addr '\
                             + addr + '\n')
                f.close()
                f2.close()

                # If -e is set, email the results to the current user
                if options.emailresult:
                    os.system('mailx ' + useremail + '< ' + outdir + \
                          '/del_persistence.txt')
                    os.system('mailx ' + useremail + '< ' + outdir + \
                          '/neteng_details.txt')
            else:
                values.append(cmdvalue)
        if options.ips == False:
            PrintTable(command,hosts,values)

    if options.remount:
        ProposeRemount(connlist)