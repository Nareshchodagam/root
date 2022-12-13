#!/usr/bin/env python
"""
This program is used to generate podlist file in a single shot. This script can be execute in multiple way like
pytnon update_podlist.py -u  [ It will update all the podlist files ]
python update_podlist.py -u -p <preset_name>
python update_podlist.py -u -d chi,was -p <preset_name>
"""
# imports
import json
import logging
import os
import pprint
import re
import subprocess
import sys

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from idbhost import Idbhost
from os import environ
from socket import gethostname
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Functions definition

def dcs(rolename, podtype):
    prod_dc = validate_dc()
    if re.search(r'crz', rolename, re.IGNORECASE):
        prod_dc = 'crz'
    elif re.search(r'rps|release|puppet|airdev', rolename, re.IGNORECASE):
        prod_dc.extend(['sfz', 'crd', 'crz', 'prd', 'sfm'])
    elif re.search(r'^argus_xrd_prod', rolename, re.IGNORECASE):
        prod_dc = 'xrd'
    elif re.search(r'^warden|argus|strata|netlog|cmgtapi', rolename, re.IGNORECASE):
        prod_dc = 'prd'
    elif re.search(r'hbase', rolename, re.IGNORECASE):
        prod_dc.extend(['sfm', 'prd', 'crd'])
    elif re.search(r'icesplunk', rolename, re.IGNORECASE):
        prod_dc = (['sfm', 'prd', 'crd'])
    elif re.search(r'splunk', rolename, re.IGNORECASE):
        prod_dc.extend(['crz', 'sfz', 'prd'])
    elif re.search(r'^bks_', rolename, re.IGNORECASE):
        prod_dc = ['crd', 'crz', 'wax']
    elif re.search(r'ajna|sms|public', podtype, re.IGNORECASE):
        prod_dc.extend(['sfz', 'prd'])
    elif re.search(r'secrets|secrets_ci|netmonitor|mom|secds|gingham|samsecurity|secmgt', podtype, re.IGNORECASE):
        prod_dc.extend(['xrd', 'crd', 'sfz', 'prd', 'crz'])
    elif re.search(r'^rackbot|^tools|monitor', rolename, re.IGNORECASE):
        prod_dc.extend(['prd', 'crd', 'sfm', 'xrd'])
    elif re.search(r'ops-stack', podtype, re.IGNORECASE):
        prod_dc.extend(['crd', 'sfz', 'prd', 'crz'])
    elif re.search(r'lhub', rolename, re.IGNORECASE):
        prod_dc = 'sfz'
    elif re.search(r'^deploydata', rolename, re.IGNORECASE):
        prod_dc.extend(['crd', 'crz', 'sfz'])
    elif re.search(r'^cmgt', rolename, re.IGNORECASE):
        prod_dc = 'phx'
    elif re.search(r'gateway|^praapp|^praccn|^pravmh|^polcore|^pkicontroller|^grok|sam|dvasyslog|nwexp|dvamon|dvaexp|searchidx|searchmgr|'
                   r'dva_onboarding|^deepsea|syntheticsagent|syntheticsmaster|^snd', rolename, re.IGNORECASE):
        prod_dc.extend(['prd'])
    elif re.search(r'^vnscanam|^inst|^edns|^ns|^netmgt|^smart|cfgapp|funnel|netbot|rdb|hmrlog|^artifactrepo', rolename, re.IGNORECASE):
        prod_dc.extend(['prd', 'crd', 'crz', 'sfm', 'sfz'])
    elif re.search(r'^syslog|appauth|vc|delphi', rolename, re.IGNORECASE):
        prod_dc.extend(['crd', 'crz', 'sfm', 'sfz'])    # TODO This code block can be refactored.
    elif re.search(r'irc', rolename, re.IGNORECASE):
        prod_dc = (['sfm', 'crd'])
    elif re.search(r'^hwmon', rolename, re.IGNORECASE):
        prod_dc.extend(['prd', 'crd'])
    elif re.search(r'nodeapp|^csm', rolename, re.IGNORECASE):
        prod_dc.extend(['crd'])
    elif re.search(r'pra_prod|^pravmh|mta|sdproxy|^gdsdclient|^servicedirectory', rolename, re.IGNORECASE):
        prod_dc.extend(['prd'])
    elif re.search(r'mq_ice|acs_ice|app_ice|ffx_ice', rolename, re.IGNORECASE):
        prod_dc = 'prd'
    elif re.search(r'netevents', rolename, re.IGNORECASE):
        prod_dc = (['prd', 'xrd'])
    elif re.search(r'ddisite', rolename, re.IGNORECASE):
        prod_dc = (['crd', 'crz', 'cdu', 'syd', 'yhu', 'yul'])
    elif re.search(r'ddicore', rolename, re.IGNORECASE):
        prod_dc = (['crd', 'crz', 'rz1'])
    elif re.search(r'ddilab', rolename, re.IGNORECASE):
        prod_dc = (['crd'])
    elif re.search(r'ddireport', rolename, re.IGNORECASE):
        prod_dc = (['rz1'])  
    return prod_dc
    #else:
        #return non_prod_dc


# Where am I
def where_am_i():
    """
    This function will extract the DC/site name form where you are executing your code.

    :param: This function doesn't require any parameter to pass.
    :return: This function will return the side/DC name e.g sfm/chi/was/tyo etc....
    """
    logger.info("Check the site_name, before connecting to iDB")
    hostname = gethostname()
    logger.debug(hostname)
    if not re.search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst, hfuc, g, site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
        short_site = short_site.replace(".eng.sfdc.net", "")
        short_site = short_site.replace(".data.sfdc.net", "")
    logger.info("Setup the site name to '{0}'" .format(short_site))
    return short_site


# idb class instantiate
def idb_connect(site):
    """
    Initiate connection to idb based on the site/DC name.

    :param site: The site name
    :type site: string
    :return: This function will return a class instance.
    :rtype:  Instance

    """
    logger.info("Connecting to iDB")
    try:
        if site == "sfm":
            idb = Idbhost()
        else:
            idb = Idbhost(site)
        logger.info("Successfully connect to iDB")
        return idb
    except Exception as e:
        logger.error("Unable to connect to idb, '{0}'".format(e))
        sys.exit(1)


def read_file(loc, filename, json_fmt=True):
    """
    The function is used to read file(Json OR Non-Json) and return the content of the file
    for next operations.
    :param loc: The location of the file '$USER/git/cptops_jenkins/scripts'
    :type loc: string
    :param filename: Name of the file   'case_presets.json'
    :type filename: string
    :param json_fmt: If True, it will read file as json object else plain file
    :type json_fmt: bool (True/False)
    :return: A dict which contains the content of given file 'filename'
    :rtype: dict
    """
    try:
        logger.info("Opening file {0}{1}".format(loc, filename))
        with open(loc + filename, 'r') as f_content:
            if json_fmt:
                try:
                    logger.info("Loading json file")
                    f_data = json.load(f_content)
                    logger.debug(pprint.pformat(f_data))
                except ValueError as e:
                    logger.error("Expected a json file, but doesn't looks like a json '{0}' " .format(e))
                    sys.exit(1)
                else:
                    logger.info("Successfully load the data from the {0} file" .format(filename))
                    retval = f_data
            else:
                logger.info("Reading file content")
                f_data = f_content.readlines()
                retval = f_data
    except IOError as e:
        logger.error("Can't open the file {0}{1} '{2}'".format(loc, filename, e))
        sys.exit(1)
    else:
        logger.debug("Successfully load the data from the file")
        return retval


def parse_json_data(data):
    """
    This function takes the input (case_preset.json file content) and choose the roles which are belongs to prod and doesn't
    have canary and type hostlist.
    This function will return a dict for all the presets in following format :-  {'preset_name' : ['podlist_file', 'cluster_type']}
    :param data: The output of case_preset.json file
    :type data: json
    :returns : returns a dict containing the preset_name, podlist file and POD/Cluster to query
    :rtype: dict
    :Example:
        {u'pbsmatch_prod': [u'pbsmatchcl', u'PBSMATCH']}
    """
    role_details = {}
    try:
        logger.info("Parsing json data for prod POD/Clusters")
        for roletype, roledata in data.items():

            if 'prod' in roletype and 'canary' not in roletype and 'standby' not in roletype:
                for role_file in roledata.values():
                    try:
                        role_details[roletype] = [role_file['PODGROUP'], role_file['CLUSTER_TYPE'], role_file['ROLE']]
                    except Exception as e:
                        logger.warn("update_podlist.py: Auto podlist not supported for preset '{0}' - '{1}' is missing"
                                      .format(roletype, e))
    except Exception as e:
        logger.error("Something went wrong with data parsing, '{0}'". format(e))
    else:
        logger.info("Successfully parsed the data")
        return role_details

def captain_clusters(role, dc):
    """
    This function us for fetching the cluster onboarded on to Captain
    :param role: querying atlas api for role
    :param dc: querying atlas api for dc
    :return: a list of clusters onboarded to captain.
    """
    clusters = []

    # get cluster data from Atlas for the specified role and dc
    url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/role-clusters?role={0}&dc={1}".format(role, dc)
    response = requests.get(url, verify=False)
    atlas_data = response.json()
    logger.debug("captain_clusters; role:{0} dc:{1} atlas_data:{2}".format(role, dc, atlas_data))

    # parse a list of cluster names out of the returned data, if any
    # NOTE: 'pod' key here is a misnomer; it's the cluster name
    if atlas_data:
        for cluster in atlas_data:
            if cluster['captain'] == True and cluster['pod'] not in clusters:
                clusters.append(cluster['pod'])

    # if not empty, print info msg with cluster list
    if clusters:
        logger.info("{0},{1} captain clusters: {2} ".format(role, dc, ",".join(clusters)))
    return clusters

def validate_dc():
    """
    This function query DC name from ATLAS
    :return: valid DC name
    """
    valid_dc = []
    url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/datacenters/list"
    response = requests.get(url,verify=False)
    try:
        response_data = response.json()
        non_prod_dc = ['sfz', 'crd', 'sfm', 'prd', 'crz']
        for data in response_data:
            if data['name'].encode("ascii","replace") in non_prod_dc:
                pass
            else:
                valid_dc.append(data['name'].encode("ascii","replace"))
    except:
        valid_dcs = ['was', 'chi', 'dfw', 'par', 'lon', 'frf', 'tyo', 'chx',
                     'wax', 'sfm', 'phx', 'ukb', 'crd', 'crz', 'ord', 'iad',
                     'yul', 'yhu', 'hnd', 'cdu', 'syd', 'xrd', 'fra', 'cdg',
                     'ia2', 'ph2', 'lo2', 'lo3', 'rd1', 'rz1', 'ttd', 'hio']
    return valid_dc


def query_to_idb(dc, rolename, idb_object, cl_status):
    """
    This function is used to query iDB with DC name and roles
    :param dc: DC's to query
    :param rolename: Rolename to query
    :param idb_object:
    :return: A dictionary contains superpod and pod information.
    :rtype: dict
    """
    logger.info("Extracting data from iDB")
    idb.sp_data(dc, cl_status.upper(), rolename)
    logger.info("Successfully extracted data from iDB")
    if not idb.spcl_grp:
        logger.error("Data not returned from iDB for - '{0}' from dc '{1}'".format(rolename, dc))
    else:
        return idb.spcl_grp

def check_ambari(dc):
    """
    This function is used to query ambari cluster with dc name
    :param dc: DC to query
    :return: ambari cluster
    """
    pjson = {}
    cluster = []
    pod_data = idb.clusterdata_complete('HBASE',dc)
    pjson[dc] = pod_data[0]['data']
    for value in pjson.values():
        for i in value:
            for j in i.get('clusterConfigs'):
                if j.get('key') == "is_ambari_managed" :
                    cluster.append(i.get('name'))
    return cluster

def file_handles(file_name):
    """
    This function takes podlist file as an argument and build primary and secondary files to write pod information.
    :param file_name:
    :return: None
    """
    if re.search(r'acs|dbaascl|trust|afw|hammer|hbase.pri|pod|public-trust|hmrlog|sfs', file_name, re.IGNORECASE):
        file_handle_pri = open('hostlists/' + file_name, 'w')
        file_handle_sec = open('hostlists/' + file_name.split('.')[0] + '.sec', 'w')
        logger.info("Opened file handles on podlist file - '{0}, {1}.sec'".format(file_name, file_name.split('.')[0]))
        return file_handle_pri, file_handle_sec

    elif 'hbase.clusters' in file_name:
        file_handle_pri = open('hostlists/' + file_name, 'w')
        logger.info("Opened file handles on podlist file - '{0}'".format(file_name))
        return file_handle_pri, None

    elif 'la_clusters' in file_name:
        file_handle_pri = open('hostlists/' + file_name, 'w')
        file_handle_sec = open('hostlists/' + 'la_cs_clusters', 'w')
        logger.info("Opened file handles on podlist file - '{0}'".format(file_name))
        return file_handle_pri, file_handle_sec

    elif 'la_cs_clusters' in file_name:
        file_handle_pri = open('hostlists/' + file_name, 'w')
        file_handle_sec = open('hostlists/' + 'la_clusters', 'w')
        logger.info("Opened file handles on podlist file - '{0}'".format(file_name))
        return file_handle_pri, file_handle_sec

    else:
        file_handle_pri = open('hostlists/' + file_name, 'w')
        file_handle_sec = 'None'
        logger.info("Opened file handles on podlist file - '{0}'".format(file_name))
        return file_handle_pri, file_handle_sec


def run_cmd(cmdlist):
    """
    Uses subprocess to run a command and return the output
    :param cmdlist: A list containing a command and args to execute
    :return: the output of the command execution
    """
    logger.debug(cmdlist)
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = run_cmd.communicate()
    return out


def get_inst_site(host):
    """
    Splits a host into a list splitting at - in the hostname
    The list contains inst,host function, group and 3 letter site code
    :param host: hostname
    :return: list containing inst,host function and 3 letter site code ignoring group.
    :rtype: list
    """
    inst, hfunc, g, site = host.split('-')
    short_site = site.replace(".ops.sfdc.net.", "")
    return inst, hfunc, short_site


def isInstancePri(inst, dc):
    """
    Confirms if an instance is primary or secondary based on site code
    DNS is used to confirm as the source of truth
        :param: an instance and a 3 letter site code
        :return: either PROD or DR
        :rtype: str
    """
    inst = inst.replace('-HBASE', '')
    monhost = inst + '-monitor.ops.sfdc.net'
    cmdlist = ['dig', monhost, '+short']
    try:
        output = run_cmd(cmdlist)
    except IOError as e:
        logger.error("update_python.py: Please check if you have dig command installed")
    logger.debug(output)
    for o in output.split('\n'):
        logger.debug(o)
        if re.search(r'monitor', o):
	        splitted = o.split("-")
	        if len(splitted) > 3:
                	inst, hfunc, short_site = get_inst_site(o)
            		logger.debug("%s : %s " % (short_site, dc))
            		if short_site != dc:
                		return "DR"
            		else:
                		return "PROD"


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]


def listbuilder(pod_list, dc):  # This was added as part of - 'T-1810443'
    """
    This function is to generate hostlist files for monitor hosts.
    :param pod_list: podlist from pod.sec and pod.pri
    :type pod_list: str
    :param dc: datacenter name
    :return: A tuple containing two lists with primary and secondary monitor host.

    """
    # searching for just monitor as below commented line shows, errs with NoneType on run
    # hostnum = re.compile(r"(^monitor)([1-6])")

    hostnum = re.compile(r"(^monitor|^netmonitor)(\d+)")
    hostcomp = re.compile(r'(\w*-\w*)(?<!\d)')
    hostlist_pri = []
    hostlist_sec = []
    if isinstance(pod_list, list):
        pods = pod_list
    else:
        pods = pod_list.split(',')
    for val in pods:
        if val != "None":
            output = os.popen("dig %s-monitor-%s.ops.sfdc.net +short | tail -2 | head -1" % (val.lower(), dc))
            prim_serv = output.read().strip("\n")
            host = prim_serv.split('.')
            logger.debug(host[0])
	    #skipping hosts with net in them (such as net-monitor and netmonitor)
            if 'net' in host[0]:
                logger.debug('Skipping net host ' + str(host[0]) + ', they break our nagios monitor execution')
                continue
            mon_num = host[0].split('-')
            if prim_serv:
                hostval2 = hostcomp.search(prim_serv)
                if "%s-monitor" % (val.lower()) == hostval2.group():
                    if val.lower() == mon_num[0]:
                        if host[0] not in hostlist_pri:
                            hostlist_pri.append(host[0])
                    match = hostnum.search(mon_num[1])
                    num = int(match.group(2))
                    if (num % 2) == 0:
                        stby_host = val.lower() + "-" + match.group(1) + str(num - 1) + "-" + mon_num[2] + "-" + dc
                    else:
                        stby_host = val.lower() + "-" + match.group(1) + str(num + 1) + "-" + mon_num[2] + "-" + dc
                    if stby_host not in hostlist_sec:
                        hostlist_sec.append(stby_host)
                else:
                    val = prim_serv.split('-')[0]
                    if host[0] not in hostlist_pri:
                        hostlist_pri.append(host[0])
                    match = hostnum.search(mon_num[1])
                    num = int(match.group(2))
		    if (num % 2) == 0:
                        if num == 30:
                                stby_host = val.lower() + "-" + match.group(1) + str(num + 1) + "-" + mon_num[2] + "-" + dc
                        else:
                                stby_host = val.lower() + "-" + match.group(1) + str(num - 1) + "-" + mon_num[2] + "-" + dc
                    else:
                        if num == 31:
                                stby_host = val.lower() + "-" + match.group(1) + str(num - 1) + "-" + mon_num[2] + "-" + dc
                        else:
                                stby_host = val.lower() + "-" + match.group(1) + str(num + 1) + "-" + mon_num[2] + "-" + dc
                    if stby_host not in hostlist_sec:
                        hostlist_sec.append(stby_host)

    return hostlist_pri, hostlist_sec


def parse_cluster_pod_data(file_name, preset_name, idb_data, groupsize, role):
    """
    This function decides formatting of data to be writtenin  podlist file and it is responsible to restructure incoming data.
    This function regorub the data for the follwing roles
        1.afw
        2.hammer
        3.acs
        4.LiveAgent
        5.hbase
        6.Any other cluster type

    :param file_name: podlist file to write
    :type: str
    :param preset_name: Name of the preset to match in re.search
    :param idb_data: iDB connection
    :param groupsize: No. of pods to write in a single line
    :return: None
    """
    pod_data = []
    c_pods = []
    f_read = False
    monitor_canary_count = 0
    for dc in idb_data.keys():
        #c_pods = captain_clusters(role, dc)
        if re.search(r'afw', file_name, re.IGNORECASE):
            groupsize = 1
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                p = []
                s = []
                for index in range(0, ttl_len):
                    if 'Primary' in pods[index] and pods[index]['Primary'] != "None" and pods[index]['Primary'] not in c_pods:
                        p.append([pods[index]['Primary'], pods[index]['Operational Status']])
                    if 'Secondary' in pods[index] and pods[index]['Secondary'] != "None" and pods[index]['Secondary'] not in c_pods:
                        s.append([pods[index]['Secondary'], pods[index]['Operational Status']])

                chunked = chunks(p, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        pri.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        pri.write(w_active)

                chunked = chunks(s, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        sec.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        sec.write(w_active)
            logger.info("Successfully written data to podlist files - '{0}, {1}.sec' for dc '{2}'".format(file_name, file_name.split('.')[0], dc))

        elif re.search(r'hammer|hmrlog', file_name, re.IGNORECASE):
            groupsize = 5
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                p = []
                s = []
                for index in range(0, ttl_len):
                    if 'Primary' in pods[index] and pods[index]['Primary'] != "None" and pods[index]['Primary'] not in c_pods:
                        p.append([pods[index]['Primary'], pods[index]['Operational Status']])
                    if 'Secondary' in pods[index] and pods[index]['Secondary'] != "None" and pods[index]['Secondary'] not in c_pods:
                        s.append([pods[index]['Secondary'], pods[index]['Operational Status']])

                chunked = chunks(p, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        pri.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        pri.write(w_active)

                chunked = chunks(s, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        sec.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        sec.write(w_active)
            logger.info("Successfully written data to podlist files - '{0}, {1}.sec' for dc '{2}'".format(file_name, file_name.split('.')[0], dc))

        elif 'pod' in file_name or 'acs' in file_name:
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            if 'acs' in file_name:
                groupsize = 1
            else:
                groupsize = 3
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                p = []
                s = []
                for index in range(0, ttl_len):
                    if 'Primary' in pods[index] and pods[index]['Primary'] != "None" and pods[index]['Primary'] not in c_pods:
                        p.append([pods[index]['Primary'], pods[index]['Operational Status']])
                    if 'Secondary' in pods[index] and pods[index]['Secondary'] != "None" and pods[index]['Secondary'] not in c_pods:
                        s.append([pods[index]['Secondary'], pods[index]['Operational Status']])

                chunked = chunks(p, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        pri.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        pri.write(w_active)

                chunked = chunks(s, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        sec.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        sec.write(w_active)
            logger.info("Successfully written data to -  '{0}, {1}.sec' for dc {2}".format(file_name, file_name.split('.')[0], dc))

        elif re.match(r'hbase_sp_prod', preset_name, re.IGNORECASE):
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            cluster = check_ambari(dc)

            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                for index in range(0, ttl_len):
                    # TODO Why this regex was added.
                    if pods[index]['Primary'] != "None" and \
                            re.match(r"HBASE\d|HBASEX|HDAAS|STG\dHDAAS|ARG1HBSVC|DCHBASE", pods[index]['Primary'], re.IGNORECASE) \
                            and pods[index]['Primary'] not in c_pods and pods[index]['Primary'] not in cluster:
                        w = pods[index]['Primary'] + " " + dc + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        pri.write(w)


            logger.info("Successfully written data to - '{0}' for dc '{1}'".format(file_name, dc))

        elif re.match(r'hbase_ambari_prod', preset_name, re.IGNORECASE):
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            cluster = check_ambari(dc)
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                for index in range(0, ttl_len):
                    # TODO Why this regex was added.
                    if pods[index]['Primary'] != "None" and \
                            re.match(r"HBASE\d|HBASEX|HDAAS|STG\dHDAAS|ARG1HBSVC|DCHBASE|ISTHBASE02", pods[index]['Primary'], re.IGNORECASE) \
                            and pods[index]['Primary'] not in c_pods and pods[index]['Primary'] in cluster:
                        w = pods[index]['Primary'] + " " + dc + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        pri.write(w)

            logger.info("Successfully written data to - '{0}' for dc '{1}'".format(file_name, dc))

        #Added to accomodate HBASE internal clusters  - W-5105681
        elif re.match(r'hbase_internal_prod', preset_name, re.IGNORECASE):
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            print(idb_data[dc].items)
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                cluster_list = ['dev1hdaas', 'dev2hdaas', 'dev3hdaas', 'dev6hdaas', 'prodinternal1', 'prodinternal2', 'int1hdaas', 'int2hdaas', 'sbox2hdaas', 'blitzhbase01', 'blitzhbase02', 'hbsr1','phoenix', 'isthbase01', 'hbsrcrd2', 'proddebug', 'perfengma2', 'relvalidation', 'blitz1', 'blitz2', 'blitz3', 'blitz4', 'icebd10hbase2a', 'icebd11hbase2a', 'icebd12hbase2a', 'icebd13hbase2a', 'stmda1hbase2a', 'stmfa1hbase2a', 'stmfb1hbase2a', 'stmfc1hbase2a', 'stmfd1hbase2a', 'stmra1hbase2a', 'stmsa1hbase2a', 'stmua1hbase2a', 'stmub1hbase2a']
                for index in range(0, ttl_len):
                    # TODO Why this regex was added.
                    if pods[index]['Primary'] != "None" and( pods[index]['Primary'].lower() in cluster_list) :
                        w = pods[index]['Primary'] + " " + dc + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        pri.write(w)
            logger.info("Successfully written data to - '{0}' for dc '{1}'".format(file_name, dc))

        elif re.match(r'hbase_internal_dch_prod', preset_name, re.IGNORECASE):
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            print(idb_data[dc].items)
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                cluster_list = ['dev4hdaas', 'dev5hdaas', 'dev7hdaas', 'dev8hdaas', 'iot1dchbase0a', 'perf1hdaas', 'testhbase']
                for index in range(0, ttl_len):
                    # TODO Why this regex was added.
                    if pods[index]['Primary'] != "None" and( pods[index]['Primary'].lower() in cluster_list) :
                        w = pods[index]['Primary'] + " " + dc + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        pri.write(w)
            logger.info("Successfully written data to - '{0}' for dc '{1}'".format(file_name, dc))

	#END

	#Added to accomodate SAYONARA ZOOKEPER HBASE POD's - W-5483209
        elif re.match(r'hbase_sayonara_prod', preset_name, re.IGNORECASE):
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                for index in range(0, ttl_len):
                    if pods[index]['Primary'] != "None" and \
                            re.match(r".*SAYONARA.*", pods[index]['Primary'], re.IGNORECASE) and pods[index]['Primary'] not in c_pods:
                        w = pods[index]['Primary'] + " " + dc + " " + sp.upper() + " " + pods[index][
                            'Operational Status'] + "\n"
                        pri.write(w)
            logger.info("Successfully written data to - '{0}' for dc '{1}'".format(file_name, dc))
        #END


        elif re.search(r'(hbase_prod)', preset_name, re.IGNORECASE):
            """
            This code splits up hbase clusters into primary, secondary lists
            writing the output to files
            """
            logger.info("Writing data on podlist file -  '{0}', '{1}.sec' ".format(file_name, file_name.split('.')[0]))
            for sp, pods in idb_data[dc].items():
                p = []
                s = []
                ttl_len = len(pods)
                for index in range(0, ttl_len):
                    if pods[index]['Primary'] != "None" and 'HBASE' in pods[index]['Primary'] and pods[index]['Primary'] not in c_pods:
                        loc = isInstancePri(pods[index]['Primary'], dc)
                        if loc == 'PROD':
                            p.append([pods[index]['Primary'], pods[index]['Operational Status']])
                        elif loc == 'DR':
                            s.append([pods[index]['Primary'], pods[index]['Operational Status']])

                chunked = chunks(p, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        pri.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        pri.write(w_active)

                chunked = chunks(s, groupsize)
                for sub_lst in chunked:
                    if 'DECOM' in [i[1] for i in sub_lst]:
                        w_decom = ','.join([i[0] for i in sub_lst if 'DECOM' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "DECOM" + "\n"
                        sec.write(w_decom)
                    if 'ACTIVE' in [i[1] for i in sub_lst]:
                        w_active = ','.join([i[0] for i in sub_lst if 'ACTIVE' in i[1]]) + " " + dc.upper() + " " + sp.upper() + " " + "ACTIVE" + "\n"
                        sec.write(w_active)
            logger.info("Successfully written data to -  '{0}, {1}.sec' for dc '{2}'".format(file_name, file_name.split('.')[0], dc))

        elif re.search(r'lapp', preset_name, re.IGNORECASE):
            """
            This code generate podlist files for lapp hosts [CS and PROD].
            """
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                for index in range(0, ttl_len):
                    if pods[index]['Primary'] != "None" and pods[index]['Primary'] not in c_pods:
                        #if 'cs' in file_name:
                        #    if 'CS' in pods[index]['Primary'] and 'GLA' not in pods[index]['Primary']:
                        #        w = pods[index]['Primary'] + " " + dc.upper() + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        #        pri.write(w)
                        #    elif 'CS' not in pods[index]['Primary'] and 'GLA' not in pods[index]['Primary']:
                        #        w = pods[index]['Primary'] + " " + dc.upper() +  " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        #        sec.write(w)
                        #else:
                        #if 'CS' not in pods[index]['Primary'] and 'GLA' not in pods[index]['Primary']:
                        w = pods[index]['Primary'] + " " + dc.upper() + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        pri.write(w)
                        #elif 'GLA' not in pods[index]['Primary']:
                        #w = pods[index]['Primary'] + " " + dc.upper() + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        #sec.write(w)

        elif re.match(r'(monitor)', preset_name, re.IGNORECASE):
            """
            This code reads updates the monitor podlist from Atlas.
            
            """



            cluster = []
            pod_dict = {}
            pod_temp = {}
            url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?role=monitor&dc={}".format(dc)
            response = requests.get(url, verify=False)
            if response.json() is None:
                logging.error("No Data Present")
                sys.exit(1)
            data = response.json()
            for host in data:
                pod = host['superpodName']
                cluster = host['clusterName']
                cluster_status = host['clusterStatus']
                if pod not in pod_dict:
                    pod_dict[pod] = []
                    pod_temp[pod] = []
                if cluster not in pod_temp[pod]:
                    pod_temp[pod].append(cluster)
                    pod_dict[pod].append({"cluster_name" : cluster, "cluster_status" : cluster_status})

            for sp, pods in pod_dict.items():
                ttl_len = len(pods)

                for index in range(0, ttl_len):
                    if pods[index]['cluster_name'] not in c_pods and pods[index]['cluster_status'].upper() in ['ACTIVE','DECOM','PROVISIONING']:
                        w = pods[index]['cluster_name'] + " " + dc + " " + sp.upper() + " " + pods[index]['cluster_status'] + "\n"
                        pri.write(w)
                        if dc in ['prd', 'sfm']:
                            if monitor_canary_count == 0 :
                                canary_file = open('hostlists/monitor.canary', 'w')
                            canary_file.write(w)
                            monitor_canary_count+=1

            logger.info("Successfully written data to podlist files - '{0}' for dc '{1}'".format(file_name, dc))



        else:
            logger.info("Writing data on podlist file - '{0}'".format(file_name))
            for sp, pods in idb_data[dc].items():
                ttl_len = len(pods)
                for index in range(0, ttl_len):
                    if 'Primary' in pods[index] and pods[index]['Primary'] not in c_pods:
                        if 'irc' in file_name and 'MTA' in pods[index]['Primary']:
                            continue
                        elif 'piperepo' in file_name and pods[index]['Primary'] not in ['PIPEREPO','OPS_PIPELINE']:
                            continue
                        w = pods[index]['Primary'] + " " + dc.upper() + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                        pri.write(w)

                    if 'Secondary' in pods[index] and pods[index]['Secondary'] not in c_pods:
                        if 'HUB' not in pods[index]['Secondary'] and 'MFM' not in pods[index]['Secondary']:
                            w = pods[index]['Secondary'] + " " + dc.upper() + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                            sec.write(w)
                        else:
                            w = pods[index]['Secondary'] + " " + dc.upper() + " " + sp.upper() + " " + pods[index]['Operational Status'] + "\n"
                            pri.write(w)
            logger.info("Successfully written data to podlist file -  '{0}' for dc '{1}'".format(file_name, dc))


def custom_logger():
    """
    This function is used to set custom logger.
    :return:
    """
    # Setting up custom logging
    logger = logging.getLogger('update_podlist.py')
    logger.setLevel(logging.DEBUG if args.verbose is True else logging.INFO)

    # create a Stream handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if args.verbose is True else logging.INFO)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(ch)
    logger.propagate = False
    return logger


if __name__ == "__main__":
    parser = ArgumentParser(description="""This code to update existing podlist files""",
                            usage=''
                                '%(prog)s -u -r <role>\n'
                                  '%(prog)s -u \n'
                                  '%(prog)s -u -p <role|roles> -d <dc|dcs> \n'
                                    '%(prog)s -u -s pre_production <default="active">', formatter_class=RawTextHelpFormatter)
    parser.add_argument("-u", dest='update', action='store_true', required=True, help="To update all files in a single run")
    parser.add_argument("-p", dest='preset_name', help='To query the specfic role')
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("-g", "--groupsize", dest="groupsize", default=3, help="Groupsize of pods or clusters for build file")
    parser.add_argument("-s", "--cluster_status", dest="cluster_status", default='active,decom,provisioning', help="Cluster Status to Query")
    parser.add_argument("-d", dest='datacenter', help="Datacenters to query")
    args = parser.parse_args()

    logger = custom_logger()
    groupsize = args.groupsize  # NOTE This is specific to group the PODS
    groupsize = int(groupsize)
    if args.update:
        site = where_am_i()
        idb = idb_connect(site)
        file_content = read_file('/{0}/git/cptops_jenkins/scripts/'.format(environ['HOME']), 'case_presets.json')
        preset_data = parse_json_data(file_content)
        logger.debug(pprint.pformat(preset_data))


        if args.preset_name:  # This loop will be called when user is trying to extract information for a specific role
            cstm_preset_data = {}
            if 'monitor' in args.preset_name and args.preset_name != 'monitor_prod' :
                args.preset_name = 'ffx_prod,' + args.preset_name
            for preset in args.preset_name.split(','):
                try:
                    cstm_preset_data[preset] = preset_data[preset]
                except KeyError as e:
                    logger.error("Could not recognise preset name - {0}" .format(e))
                    sys.exit(1)
            preset_data = cstm_preset_data
        role_details = []
        total_idb_data = {}
        for k, v in preset_data.items():
            clustype = v[1].split(',')
            pri, sec = file_handles(v[0])
            for clustname in clustype:
                logger.info("\n************************* Starting on role '{0}'*************************".format(k))
                if clustname not in role_details or re.search(r'afw|hbase|lhub|log_hub|splunk-|pod|hammer', v[0], re.IGNORECASE):
                    role_details.append(clustname)
                    total_idb_data['monitor'] = {dc:'' for dc in dcs(k, v[1])}
                    if v[1] not in total_idb_data.keys():
                        if args.datacenter:
                            datacenters = args.datacenter.split(',')
                            idb_ret = query_to_idb(datacenters, clustname,  idb, args.cluster_status)
                        else:
                            idb_ret = query_to_idb(dcs(k, clustname), clustname, idb, args.cluster_status)
                        total_idb_data[clustname] = idb_ret
                        if not idb_ret:
                            continue
                    else:
                        logger.info("Skipping iDB query, using data from cache")

                    parse_cluster_pod_data(v[0], k, total_idb_data[clustname], groupsize, v[2])
                    logger.info("\n************************* Done with Role '{0}' *************************\n".format(k))
                else:
                    logger.info("skipping... The podlist file {0} for role {1}  has been processed" .format(v[0], k))
                    logger.info("\n************************* Done with Role '{0}' *************************\n".format(k))
            else:
                continue


