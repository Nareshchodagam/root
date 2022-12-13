from optparse import OptionParser
import logging
import re
import common
from idbhost import Idbhost
import json
import sys

def ParseData(data):
    print(data)

def getInst(h):
    inst,hfuc,g,site = h.split('-')
    return inst,hfuc,g,site    

def getData(filename):
    with open(filename) as data_file:
        data = data_file.read().splitlines()
    return data
    
def getHostData(filename):
    with open(filename) as data_file:
        data = data_file.read().splitlines()
    return data

def genPre(template,site):
    output = []
    for l in template:
        l = l.replace('v_DATACENTER', site)
        output.append(l)
    return output

def genMain(hosts,template):
    output = []
    for h in hosts:
        inst,hfuc,g,site = getInst(h)
        o = template
        lines = []
        for i in o:
            i = i.replace('v_HOSTS', h)
            i = i.replace('v_DATACENTER', site)
            if inst == 'ops0':
                i = i.replace('ops-monitor', 'ops0-monitor')
            lines.append(i)
        output.append(lines)
    return output

def writeTemplate(pre,main_template,site):
    filename = '../output/plan_implementation.txt'
    f = open(filename, 'w')
    begin = "BEGIN_DC: " + site.upper() + "\n"
    f.write("\n")
    f.write(begin)
    for l in pre:
        l = l + "\n"
        f.write(l)
    for l in main_template:
        for h in l:
            h = h + "\n"
            f.write(h)
    end = "END_DC: " + site.upper() + "\n"
    f.write(end)
    f.write("\n")
    f.close()

if __name__ == "__main__":
    usage = """
    proxy patching case implementation plan generation

    This code will generate the implementation plan for patching sites proxy hosts.
    The arguments required to be passed are case, superpod, instance, data center and host.

    %prog -c caseNum -s superpod -i instance -d datacenter -H host
    %prog -c 00081002 -s none -i cs3 -d sjl -H proxy1-1
    %prog -c 00081002 -s sp1 -i na7 -d was -H proxy1-1

    How to call the
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                help="The case number to use")
    parser.add_option("-t", "--template", dest="template", help="The template")
    parser.add_option("-i", "--instance", dest="instance", help="The instance")
    parser.add_option("-d", "--datacenter", dest="datacenter", help="The datacenter")
    parser.add_option("-l", "--host", dest="host", help="The host list in a file")
    parser.add_option("-H", "--hostlist", dest="hostlist", help="The host list comma separated")
    parser.add_option("-f", "--filename", dest="filename", default="implementation_plan.txt", help="The output filename")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    hosts = []
    if options.host:
        hosts = getHostData(options.host)
    if options.hostlist:
        hosts = options.hostlist.split(',')
    #print(hosts)
    if options.datacenter == None:
        print('DC required')
        sys.exit(1)
    if options.template:
        site = options.datacenter
        if site == 'all':
            pre_template = options.template + ".pre"
            pre = getData(pre_template) 
            template = getData(options.template)
            pre_temp = genPre(pre, site)
            main_template = genMain(hosts,template)
            writeTemplate(pre_temp,main_template,site)    
        else:
            dc_hosts = []
            loc = options.datacenter
            for h in hosts:
                inst,hfuc,g,site = getInst(h)
                if site == loc:
                    dc_hosts.append(h)
            
            pre_template = options.template + ".pre"
            pre = getData(pre_template) 
            template = getData(options.template)
            pre_temp = genPre(pre, loc)
            main_template = genMain(dc_hosts,template)
            writeTemplate(pre_temp,main_template,loc)
        