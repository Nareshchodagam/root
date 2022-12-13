#!/usr/bin/python

"""A wrapper to generate umps implementation plan and to create cases"""

import argparse
import logging
import getpass
import shlex
import json
from subprocess import check_call
from common import Common
from idbhost import Idbhost

idb = Idbhost()

template_file = 'umps.linux.template'

data = {
    "chatter1": "cs1,cs12,cs30",
    "chatter3": "na1",
    "chatter2": "na0,cs2",
    "chatter4": "cs13",
    "chatter5": "na10,cs7",
    "chatter7": "cs8",
    "chattergus1": "gs0",
    "chatter1c3": "",
    "chatter1c4": "na9,cs14",
    "chatter6": "cs9",
    "chatter8": "cs10",
    "chatter1w3": "na11,cs11",
    "chatter1w4": "n12,na14",
    "chatter2c1": "cs15",
    "chatter2c2": "na2",
    "chatter2c3": "na13,cs19",
    "chatter2c4": "cs16",
    "chatter2w1": "na4,cs17",
    "chatter2w2": "cs20",
    "chatter2w3": "eu0",
    "chatter2w4": "na15,na16,cs18",
    "chatter3c1": "cs23,cs24,cs25,cs27,cs28",
    "chatter3c2": "",
    "chatter3c3": "na5,na19,na20,",
    "chatter3c4": "",
    "chatter3w1": "na17,na18,na22,na23,na41,cs21,cs22,cs26",
    "chatter3w2": "",
    "chatter3w3": "",
    "chatter3w4": "",
    "chatter4c1": "na6,cs42",
    "chatter4c2": "na27,na29,cs40,cs45,cs46",
    "chatter4c3": "na25,na28",
    "chatter4c4": "",
    "chatter4w1": "na24,na26,cs41",
    "chatter4w2": "na31,cs43",
    "chatter4w3": "cs44",
    "chatter4w4": "",
    "chatter9": "ap3,cs5,cs31",
    "chatter10": "cs6",
    "chatter1t3": "ap0,ap2",
    "chatter1t4": "ap1",
    "chatter1p1": "",
    "chatter1p2": "na33,cs3",
    "chatter1p3": "cs52",
    "chatter1p4": "",
    "chatter2p1": "",
    "chatter2p2": "",
    "chatter2p3": "",
    "chatter2p4": "",
    "chatter1f1": "",
    "chatter1f2": "cs82,cs83,eu6",
    "chatter1f3": "",
    "chatter1f4": "",
    "chatter1d1": "na8,na34,cs51",
    "chatter1d2": "na3,na32",
    "chatter1d3": "na7,cs50",
    "chatter1d4": "",
    "chatter2d1": "",
    "chatter2d2": "",
    "chatter2d3": "",
    "chatter2d4": "",
    "chatter1l1": "eu5,cs80,cs81",
    "chatter1l2": "eu1,eu3,eu4,cs86,cs87",
    "chatter1l3": "eu2,",
    "chatter1l4": "",

}


def run_command(cmd):
    cmd = shlex.split(cmd)
    check_call(cmd)

# Function to get the clusters name from idb in a given dc
def get_clusters(dc, sp, op_status):
    idb.sp_info(dc, sp, op_status, 'CHATTER')
    clus_json = idb.spcl_grp
    for key, vals in clus_json.iteritems():
        clusters = vals['Primary'].split(',')
    if 'CHATTERGUS1' in clusters:
        clusters.remove('CHATTERGUS1')
    return clusters


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-D", "--datacenter", help="Please enter the DC", required=True)
    parser.add_argument("-C", "--clusters", help="UMPS clusters name")
    parser.add_argument("-S", "--superpod", help="superpod name")
    parser.add_argument("-O", "--op_status", help="operational_status")
    parser.add_argument("-P", "--preprod", help="preprod", action="store_true")
    parser.add_argument("-V", "--verbose", help="To get debug info")
    args = parser.parse_args()
    dc = args.datacenter
    sp = args.superpod
    op_status = args.op_status

    if args.clusters:
        clusters = args.clusters
    else:
        clusters = get_clusters(dc, sp, op_status)

    if args.verbose:
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

    if dc and sp:
        if isinstance(clusters, list):
            clusters = [cluster.lower() for cluster in clusters]
            insts = ",".join([data[cluster] for cluster in clusters if data[cluster]])
        else:
            insts = ",".join([data[cluster] for cluster in clusters.split(',') if data[cluster]])

        if args.clusters:
            if 'gus' in clusters:
                template_file = template_file.replace('umps.linux.template', 'umps.linux.gus.template')
            elif args.preprod:
                template_file = template_file.replace('umps.linux.template', 'umps.linux.preprod.template')
            plan_cmd = "python UMPS_gen_plan.py -s  %s -i %s -g ../templates/%s -d %s  -r " \
                "umps -b 2016.01 -o %s" % (sp, clusters.upper(), template_file, dc, op_status)
        else:
            if args.preprod:
                template_file = template_file.replace('umps.linux.template', 'umps.linux.preprod.template')
            plan_cmd = "python UMPS_gen_plan.py -s  %s  -g ../templates/%s -d %s  -r " \
                "umps -b 2016.01 -o %s" % (sp, template_file, dc, op_status)

        case_cmd = 'python gus_cases.py -T change  -f ../templates/jan-patch.json  -s "Jan Patch ' \
            'Bundle: UMPS %s-%s  %s %s NotLive" -k ../templates/6u6-plan.json  -l output/summarylist.txt -D %s -i ' \
            'output/plan_implementation.txt' % (dc.upper(), sp.upper(), insts, ",".join(clusters), dc)
        logging.info("Running plan generation command \n %s" % plan_cmd)
        logging.info("Running case generation command \n %s" % case_cmd)
        run_command(plan_cmd)
        run_command(case_cmd)

