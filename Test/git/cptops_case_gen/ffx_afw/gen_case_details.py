
"""Code to take a ffx batch file and output required details for case generation"""
import re
import subprocess
import logging
from optparse import OptionParser
import common_methods
import os
import shlex
import sys



def parseData(batch_data):
    dcs = {}
    hosts = []
    batch = ''
    for i in batch_data:
        i = i.rstrip()
        logging.debug(i)
        #batch_num, hostname, serial, dc_sp, inst_dc, rack = i.split(",")
        batch_num,hostname,dc_sp,inst_dc = i.split(",")
        batch = batch_num
        hosts.append(hostname)
        inst,dc = inst_dc.split('-')
        if dc not in dcs:
            dcs[dc] = 1
        if dcs[dc] == 1:
            dcs[dc] = inst
        elif not inst in dcs[dc]:
            dcs[dc] = dcs[dc] + "," + inst
           
    return dcs,hosts,batch

def instAltLoc(pods_lists,inst,dc):
    altdc = ''
    for l in pods_lists:
        l = l.rstrip()
        if re.match(inst, l, re.IGNORECASE):
            if re.search(dc, l, re.IGNORECASE):
                next
            else:
                _,altdc = l.split()
            
    return altdc

def buildPre(dcs_insts,filename,pods_lists):
    build_pre = []
    build_pre.append("\n")
    build_pre.append("Before doing anything setup your sudo password\n")
    build_pre.append("This should be done in another shell outside katzmeow\n")
    build_pre.append("read -s -p 'Password: ' SUDO_PASS\n")
    build_pre.append("export SUDO_PASS\n")
    build_pre.append("\n")
    build_pre.append("BEGIN_GROUP: FILES\n")
    for dc in dcs_insts:
        build_pre.append("Exec: svn co svn://vc-%s/subversion/tools/automation/scripts/cpt/ffx/batchfiles/%s/%s ~/%s\n" %(dc.lower(),dc.lower(),filename,filename))
    build_pre.append("END_GROUP: FILES\n")
    
    build_pre.append("\n")
    
    build_pre.append("BEGIN_GROUP: PRE\n")
    for dc in dcs_insts:
        for inst in dcs_insts[dc].split(","):
            altdc = instAltLoc(pods_lists, inst, dc)
            if not altdc == '':
                build_pre.append("Exec: ~/ffx/ffx/safety-check-cluster.sh %s %s\n" % (altdc,inst))
    
    build_pre.append("\n")
    
    for dc in dcs_insts:
        for inst in dcs_insts[dc].split(","):
            build_pre.append("Exec: ~/ffx/ffx/safety-check-cluster.sh %s %s\n" % (dc.lower(),inst))
    build_pre.append("END_GROUP: PRE\n")
    build_pre.append("\n")
    return build_pre
    
def buildPost(hosts):
    build_post = []
    build_post.append("BEGIN_GROUP: POST\n")
    build_post.append("\n")
    for h in hosts:
        build_post.append("""Exec: ~/ffx/ffx/ffx-waitforstartup.sh %s\n""" % h)
    build_post.append("\n")
    for h in hosts:
        build_post.append("""Exec: ~/ffx/ffx/ffx-corruptfilefinder.sh %s\n""" % h)
    build_post.append("END_GROUP: POST\n")
    build_post.append("\n")
    return build_post
    
def buildMain(dcs_insts,filename,batch): 
    build_main = []
    insts = ''
    altdcs = []
    for dc in dcs_insts:
        insts = dcs_insts[dc].split(",")
    build_main.append("\n")       
    build_main.append("BEGIN_GROUP: 1\n")
    for dc in dcs_insts:
        for inst in dcs_insts[dc].split(","):
            altdc = instAltLoc(pods_lists, inst, dc)
            if altdc not in altdcs and altdc != '':
                altdcs.append(altdc)
        for altdc in altdcs:
            build_main.append("Manual: Presteps run for %s?\n" % altdc.upper())
        build_main.append("Manual: Presteps run for %s?\n" % dc.upper())
        
    build_main.append("\n")
    build_main.append("Manual : Confirm no one is executing on the same insts : %s ?\n" % ",".join(insts))
    build_main.append("\n")
    build_main.append("Exec: ~/ffx/ffx/rr-ffx-prechecks.sh %s %s\n" % (filename,batch))
    build_main.append("\n")
    build_main.append("Exec: ~/ffx/ffx/gig-rt-rps-convert.sh %s %s\n" % (filename,batch))
    build_main.append("\n")
    build_main.append("Exec: ~/ffx/ffx/rr-ffx-postchecks.sh %s %s\n" % (filename,batch))
    build_main.append("\n")
    build_main.append("Exec: ~/ffx/ffx/rr-start-ffx.sh %s %s\n" % (filename,batch))
    build_main.append("\n")
    build_main.append("END_GROUP: 1\n")
    build_main.append("\n")
    return build_main
    
def printOutput(dcs_insts,batch,output_file_hostlist,create_case,case_sub):
    #def printOutput(dcs_insts, batch, output_file_plan, output_file_hostlist, create_case):
    for dc in dcs_insts:
        insts = dcs_insts[dc]
        if case_sub == True:
            str = """python ../gus_cases_vault.py -T change  -f ../templates/ffx-conv-nonaproved.json  --infra "Primary and Secondary" -s "FFX AFW Conversions %s batch %s" -k ../templates/ffx-afw-plan.json -D %s -l %s -A""" % (
            dc, batch, dc, output_file_hostlist)
        else:
            #str = """python gus_cases_vault.py -T change  -f ../templates/ffx-afw-case_details.json  --inst %s --infra "Primary and Secondary" -s "FFX AFW Conversions %s batch %s" -k ../templates/ffx-afw-plan.json -D %s -i %s -l %s""" % (insts,dc,batch,dc,output_file_plan,output_file_hostlist)
            str = """python ../gus_cases_vault.py -T change  -f ../templates/ffx-conv-nonaproved.json  --infra "Primary and Secondary" -s "FFX AFW Conversions %s batch %s" -k ../templates/ffx-afw-plan.json -D %s -l %s""" % (dc,batch,dc,output_file_hostlist)

    logging.debug(str)
    cmd_list = shlex.split(str)
    logging.debug(cmd_list)
    if create_case == True:
        cmd_output = common_methods.run_cmd(cmd_list)
        print(cmd_output)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--filename", dest="batch_file", help="Filename with batch details")
    parser.add_option("-c", action="store_true", dest="create_case", default=False, help="Case creation option")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")
    parser.add_option("-A", action="store_true", dest="case_sub", default=False, help="Submit case for approval")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    #output_file_plan = '../output/plan_implementation.txt'
    output_file_hostlist = 'output/hostlist_file'
    pods_lists = common_methods.getData('pods_lists')
    if options.batch_file:
        _,fname = os.path.split(options.batch_file)
        batch_data = common_methods.getData(options.batch_file)
        dcs_insts,hosts,batch = parseData(batch_data)
        #build_pre = buildPre(dcs_insts,fname,pods_lists)
        #build_main = buildMain(dcs_insts,fname,batch)
        #build_post = buildPost(hosts)
        #plans = build_pre + build_main + build_post
        #output_plan = common_methods.writeOutPlan(plans,output_file_plan)
        common_methods.writeOut(hosts,output_file_hostlist)
        #printOutput(dcs_insts,batch,output_file_plan,output_file_hostlist,options.create_case)
        printOutput(dcs_insts, batch, output_file_hostlist, options.create_case, options.case_sub)