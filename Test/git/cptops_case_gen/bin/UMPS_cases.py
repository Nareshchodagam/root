
from optparse import OptionParser
from common import Common
from idbhost import Idbhost
import pexpect
import getpass
import time
import logging
import subprocess


common=Common
idb=Idbhost()



def getHostlist(dc, cluster):
    idb.clustinfo(dc,cluster)
    hosts = idb.clusterhost
    logging.debug(hosts)
    return hosts[cluster]

def writeToFile(filename, hostslist):
    with open(filename, 'w') as file:
        for host in hostslist:
            file.write(host + '\n')
        file.close()

def readFile(filename):
    with open(filename, 'r') as rfile:
        fcontent = rfile.readlines()
        content = ",".join([str(x).strip("\n") for x in fcontent])
        rfile.close()
        return content

def writePlan(filename,sp,clusterName,hostfile,dc):
    template_file = '../templates/umps_AFW.template'
    with open(template_file, 'r') as file:
        fread = readFile(hostfile)
        file_Content = file.read()
        file_Content = file_Content.replace('v_DATACENTER',dc)
        file_Content = file_Content.replace('v_SP',sp)
        file_Content = file_Content.replace('v_HOSTS', fread)
        file_Content = file_Content.replace('v_CLUSTER',clusterName)
        file.close()
        with open(filename, 'w') as file1:
            file1.write(file_Content)
            file1.close()


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-d", "--datacenter", dest="dc", help="The datacenter")
    parser.add_option("-c", "--clustername", dest="cluster", help="The cluster")
    parser.add_option("-s", "--superpod", dest="sp", help="The superpod")
    parser.add_option("-g", "--print_commands", dest="commands", help="The commands")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")



    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(format='%(asctime)s : %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)


    if options.dc and options.cluster and options.sp:
        pw = getpass.getpass()
        clusters = options.cluster.split(',')
        for cluster in clusters:

            hostlists = getHostlist(options.dc,cluster)
            writeToFile('/tmp/hosts', hostlists)
            writePlan('impl.txt',options.sp, cluster, '/tmp/hosts',options.dc)
            time.sleep(5)

            #python UMPS_gen_plan.py  -s %s -d %s  -g ../templates/umps.linux.template -r umps  -i %s % (options.sp,options.dc,options.cluster)

            #cmd="python gus_cases.py -T change  -f ../templates/umps_AFW_case.json  -s %s_Chattenow/FileSync_AFW_conversion -k ../templates/umps_AFW_plan.json -l /tmp/hosts -D %s -i impl.txt" % (cluster,options.dc)
            cmd = "python gus_cases.py -T change  -f ../templates/umps-rh6u6-patch.json  -s 'May Patch Bundle : Chatternow %s[%s] PROD' -k ../templates/6u6-plan.json -l /tmp/hosts -D %s -i output/plan_implementation.txt" %  (options.dc,cluster,options.dc)

            child = pexpect.spawn(cmd)
            child.expect(".*password:")
            child.sendline(pw + "\n")
            child.expect(pexpect.EOF)#waiting for child output to finish
            print "Completed cluster %s \n" % cluster




