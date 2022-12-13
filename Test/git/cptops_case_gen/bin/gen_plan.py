 from optparse import OptionParser
import logging
import re
import os
import json

# DSheehan 03/20 added following changes:
# implicit loading of <template>.pre and <template.post> to enable presteps and poststeps applicable to all hosts
# related to above concept of all hosts to enable commmands applicable to all hosts
# custom parameters -C option to allow you to pass in a dict : '{"v_PARAMNAME": "paramvalue"}
# related to above modified gen_plan and get_gen_setup
def gen_plan(options,case,sp,cluster,dc,hostname,role,allhostlist=''):
    if re.search(r'public', hostname) and role == 'proxy':
        role = 'publicproxy'
    elif role == 'proxy':
        role = 'sitesproxy'
    template_file="templates/" + role + ".template"
    s=open(template_file).read()
    if len(allhostlist)>0:
        s = s.replace('v_LISTOFHOSTS', allhostlist)
    if options.customparam:
        data=json.loads( options.customparam )
    for key in data.keys():
        s = s.replace(key, data[key] )
    s = s.replace('v_HOSTS', hostname)
    s = s.replace('v_CLUSTER', cluster)
    s = s.replace('v_DATACENTER', dc)
    s = s.replace('v_SUPERPOD', sp)
    s = s.replace('v_CASENUM', case)
    #if SP has a digit suffix and is not sp1
    dcsp = dc+sp[-1:] if sp[-1:].isdigit() and sp[-1:] != '1' else dc + ''
    s = s.replace('v_DCSP', dcsp)
    return s

def get_gen_setup(options,case,sp,cluster,dc,filename,allhostlist=''):
    s=open(filename).read()
    if len(allhostlist)>0:
        s = s.replace('v_LISTOFHOSTS', allhostlist)
    if options.customparam:
        data=json.loads( options.customparam )
    for key in data.keys():
        s = s.replace(key, data[key] )
    s = s.replace('v_CLUSTER', cluster)
    s = s.replace('v_DATACENTER', dc)
    s = s.replace('v_SUPERPOD', sp)
    s = s.replace('v_CASENUM', case)
    return s

def write_plan(plan,filename):
    out_file="output/" + filename
    print "Generating: " + out_file
    f = open(out_file,'w')
    f.write(plan)
    f.close()

def get_hosts(hostlist):
    hlist = []
    with open(hostlist) as f:
        for line in f:
            hlist.append(line.rstrip())
    return hlist


if __name__ == "__main__":
    usage = """
    proxy patching case implementation plan generation

    This code will generate the implementation plan for patching sites proxy hosts.
    The arguments required to be passed are case, superpod, instance, data center and host.

    %prog -c caseNum -s superpod -i instance -d datacenter -H host
    %prog -c 00081002 -s none -i cs3 -d sjl -H proxy1-1
    %prog -c 00081002 -s sp1 -i na7 -d was -H proxy1-1
    %prog gen_plan.py -c 00084099 -s none -i none -d sjl -l ~/sjlhostlist -r shared-nfs -g /home/dsheehan/case_gen/templates/shared-nfs.template -C '{"v_REGEX": "^cs3-|^cs4-"}'
    How to call the
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                help="The case number to use")
    parser.add_option("-s", "--superpod", dest="superpod", help="The superpod")
    parser.add_option("-i", "--cluster", dest="cluster", help="The instance")
    parser.add_option("-l", "--hostlist", dest="hostlist", help="The hostlist")
    parser.add_option("-g", "--gensetup", dest="gensetup", help="The general setup information")
    parser.add_option("-d", "--datacenter", dest="datacenter", help="The datacenter")
    parser.add_option("-p", "--publicproxy", dest="publicproxy", help="public proxy")
    parser.add_option("-r", "--role", dest="role", help="Host role")
    parser.add_option("-H", "--host", dest="host", help="The host")
    parser.add_option("-f", "--filename", dest="filename", default="plan_implementation.txt", help="The output filename")
    parser.add_option("-C", "--customparam", dest="customparam", default='{}', help="list of custom parameters v_PARAM='value'")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.caseNum and options.superpod and options.cluster and options.datacenter and options.host and options.role:
        plan = gen_plan(options,options.caseNum,options.superpod,options.cluster,options.datacenter,options.host,options.role)
        write_plan(plan,options.filename)
    elif options.caseNum and options.superpod and options.cluster and options.datacenter and options.hostlist and options.role and options.gensetup:
        hlist = get_hosts(options.hostlist)
        gen_setup = get_gen_setup(options,options.caseNum,options.superpod,options.cluster,options.datacenter,options.gensetup)
        plans = []
        t = ''
        for i in gen_setup:
            t += i
        t += '\n'
        optionallistofhosts = ','.join([line for line in hlist])
        if os.path.isfile(options.gensetup + '.pre'):
            t = get_gen_setup(options,options.caseNum,options.superpod,options.cluster,options.datacenter,options.gensetup + '.pre',optionallistofhosts )
        for host in hlist:
            plan = gen_plan(options,options.caseNum,options.superpod,options.cluster,options.datacenter,host,options.role,optionallistofhosts)
            logging.debug(plan)
            plans.append(plans)
            t += plan
            t += '\n'
        if os.path.isfile(options.gensetup + '.post'):
            t += get_gen_setup(options,options.caseNum,options.superpod,options.cluster,options.datacenter,options.gensetup + '.post',optionallistofhosts )
        write_plan(t,options.filename)
    else:
        print(usage)
