#!/usr/bin/python
 
import os
import re
import sys
import socket
import subprocess
import logging
from optparse import OptionParser
import subprocess
 
def groupType(role):
    groupings = {'search': 'majorset',
                 'mnds,dnds': 'majorset',
                 'insights_iworker,insights_redis': 'majorset' 
                 }
    if role in groupings:
        return groupings[role]
    else:
        return 'majorset'

def groupSize(role):
    groupsizes = {'search': 15,
                  'insights_iworker,insights_redis': 18,
                  'mnds,dnds': 4
                      }
    if role in groupsizes:
        return groupsizes[role]
    else:
        return 1
def getData(filename):
    with open(filename) as data_file:
        data = data_file.readlines()
    return data

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")
    parser.add_option("-r", "--role", dest="role", help="role to be used")
    parser.add_option("-t", "--template", dest="template", help="template to be used")
    parser.add_option("--infra", dest="infra", help="Infra type [Primary|Secondary|Primary and Secondary|Supporting Infrastructure")
    parser.add_option("-g", "--group", dest="group", help="group for subject")
    parser.add_option("-s", "--groupsize", dest="groupsize", help="max groupsize for subject")
    parser.add_option("-p", "--podgroups", dest="podgroups", help="File with pod groupings")
    parser.add_option("-f", "--filter", dest="filter", help="regex host filter")
    parser.add_option("-d", "--dr", dest="dr", default="False", help="dr true or false")
    parser.add_option("-b", "--bundle", dest="bundle", help="Bundle short name eg may oct")
    parser.add_option("--patchset", dest="patchset", help="Patchset name eg 2015.10 or 2016.01")
    parser.add_option("--taggroups", dest="taggroups", help="Size for blocked groups for large running cases like hbase")
    #python = '/usr/local/Cellar/python/2.7.10_2/bin/python2.7'
    python = 'python'
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    grouping = "majorset"
    groupsize = 1
    if options.role:
        grouping = groupType(options.role)
        groupsize = groupSize(options.role)     
    if options.groupsize:
        groupsize = options.groupsize
    if options.podgroups:
        data = getData(options.podgroups)
        for l in data:
            pods,dc = l.split()
            #pods,dc,options.role,options.template,options.dr

            #msg =  { "clusters" : pods ,"datacenter": dc , "roles": options.role, "cl_opstat" : "ACTIVE", "grouping" : "majorset", "maxgroupsize": 4, "templateid" : options.template, "dr": options.dr }
            #print("""python build_plan.py -c 0000001 -C -G '{"clusters" : "%s" ,"datacenter": "%s" , "roles": "%s", "grouping" : "majorset", "maxgroupsize": 4, "templateid" : "%s", "hostfilter": "^.*%s" }' -v""" % (pods,dc,options.role,options.template,options.filter))
            #print("""python build_plan.py -c 0000001 -C -G '{"clusters" : "%s" ,"datacenter": "%s" , "roles": "%s", "grouping" : "majorset", "maxgroupsize": 4, "templateid" : "%s", "dr": "%s", "hostfilter": "^.*%s" }' -v""" % (pods,dc,options.role,options.template,options.dr,options.filter))
            #if options.groupsize:
            #    if re.search(r'LAPP.*CS', pods, re.IGNORECASE):
            #        groupsize = 2
            #    else:
            #        groupsize = groupSize(options.role)
            if options.filter:
                print("""%s build_plan.py -C --bundle %s -G '{"clusters" : "%s" ,"datacenter": "%s" , "roles": "%s", "grouping" : "%s", "maxgroupsize": %s, "templateid" : "%s", "dr": "%s" , "hostfilter": "^.*%s"}' --taggroups %s -v""" % (python,options.patchset,pods,dc,options.role,grouping,groupsize,options.template,options.dr,options.filter,options.taggroups))
            else:
                #print("""python build_plan.py -C --bundle %s -G '{"clusters" : "%s" ,"datacenter": "%s" , "roles": "%s", "grouping" : "majorset","cl_opstat" :  "PROVISIONING,PRE_PRODUCTION", "host_opstat": "ACTIVE,PRE_PRODUCTION,PROVISIONING","maxgroupsize": %s, "templateid" : "%s", "dr": "%s" }' -v""" % (options.patchset,pods,dc,options.role,groupsize,options.template,options.dr))
                print("""%s build_plan.py -C --bundle %s -G '{"clusters" : "%s" ,"datacenter": "%s" , "roles": "%s", "grouping" : "%s","maxgroupsize": %s, "templateid" : "%s", "dr": "%s" }' --taggroups %s -v""" % (python,options.patchset,pods,dc,options.role,grouping,groupsize,options.template,options.dr,options.taggroups))
            #print("""python build_plan.py -C -G '%s' -v""" % msg)
            if options.group:
                print("""%s gus_cases.py -T change  -f ../templates/%s-patch.json  --inst %s --infra "%s" -s "%s Patch Bundle: %s %s %s %s" -k ../templates/6u6-plan.json  -l ../output/summarylist.txt -D %s -i ../output/plan_implementation.txt""" % (python,options.bundle,pods,options.infra,options.bundle.upper(),options.role.upper(),dc.upper(),pods,options.group,dc))
            else:
                print("""%s gus_cases.py -T change  -f ../templates/%s-patch.json  --inst %s --infra "%s" -s "%s Patch Bundle: %s %s %s" -k ../templates/6u6-plan.json  -l ../output/summarylist.txt -D %s -i ../output/plan_implementation.txt""" % (python,options.bundle,pods,options.infra,options.bundle.upper(),options.role.upper(),dc.upper(),pods,dc))
