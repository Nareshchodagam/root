#!/usr/bin/python
###############################################################################
#
# Purpose: Take information from idb build imp plans.
#
# Usage: See ../docs/build_plan_README.md
#
###############################################################################

from optparse import OptionParser
import re
import glob
import os.path
import logging
from modules.buildplan_helper import *
from idbhost import Idbhost
import requests
import json
import sys

reload(sys)

sys.setdefaultencoding('utf8')
###############################################################################
#                Constants
###############################################################################
templatefile = ''
out_file = ''
pre_file = ''
post_file = ''
hosts = []
hostlist = []
not_patched_hosts = []
not_os_hosts = []

new_supportedfields = {'superpod': 'host.cluster.superpod.name',
                       'role': 'host.deviceRole',
                       'cluster': 'host.cluster.name',
                       'hostname': 'host.name',
                       'failoverstatus': 'host.failOverStatus',
                       'dr': 'host.cluster.dr',
                       'host_operationalstatus': 'host.operationalStatus',
                       'cluster_operationalstatus': 'host.cluster.operationalStatus',
                       'clustertype': 'host.cluster.clusterType',
                       'index_key': 'key',
                       'index_value': 'value',
                       'cluter_configs': 'host.cluster.clusterConfigs',
                       'host_configs': 'host',
                       'cluster_env': 'host.cluster.environment'}

# Old supportedfields.
supportedfields = {
    'superpod': 'cluster.superpod.name',
    'role': 'deviceRole',
    'cluster': 'cluster.name',
    'hostname': 'name',
    'failoverstatus': 'failOverStatus',
    'dr': 'cluster.dr',
    'host_operationalstatus': 'operationalStatus',
    'cluster_operationalstatus': 'cluster.operationalStatus',
    'clustertype': 'cluster.clusterType'}


###############################################################################
#                Functions
###############################################################################

def get_hosts_from_file(filename):
    try:
        with open(filename) as f:
            hostlist = f.read().splitlines()
    except:
        print
        "Unable to open host list file"
        exit()
    return hostlist


def write_list_to_file(filename, list, newline=True):
    if newline:
        s = '\n'.join(list)
    else:
        s = ''.join(list)
    f = open(filename, 'w')
    f.write(s)
    f.close()


def get_json(input_file):
    with open(common.etcdir + '/' + input_file) as data_file:
        try:
            data = json.load(data_file)
        except Exception as e:
            print('Problem loading json from file %s : %s' % (input_file, e))
    return data


def build_dynamic_groups(hosts):
    # Cut up the hostlist by the values stored in ../etc/host_regex.json
    # to generate more complex plans.
    outmap = {}
    with open(common.etcdir + '/host_regex.json') as data_file:
        hostmap = json.load(data_file)

    for r, v in hostmap.items():
        regexp = re.compile(r)
        for host in hosts:
            if regexp.search(host) is not None:
                if v in outmap and not (outmap[v] is None):
                    outmap[v].append(host)
                else:
                    outmap[v] = []
                    outmap[v].append(host)
    return outmap


# Functions For UMPS W-3773536 | T-1747266

# Intiliazie the lists
HOSTS_CPS = []
HOSTS_DSTORE = []
HOSTS_MSG = []
HOSTS = []


def clearUmpsList():
    del HOSTS_CPS[:]
    del HOSTS_DSTORE[:]
    del HOSTS_MSG[:]
    del HOSTS[:]


def build_Umps_Hostlist(hostname):
    global v_CPS1
    global v_DSTORE1
    global v_MSG1
    global v_HOSTS
    if re.search(r'prsn|chan', hostname):
        HOSTS_CPS.append(hostname)
    elif re.search(r'dstore', hostname):
        HOSTS_DSTORE.append(hostname)
    elif re.search(r'msg', hostname):
        HOSTS_MSG.append(hostname)
    HOSTS = HOSTS_CPS + HOSTS_DSTORE + HOSTS_MSG

    v_CPS1 = ",".join(HOSTS_CPS)
    v_DSTORE1 = ",".join(HOSTS_DSTORE)
    v_MSG1 = ",".join(HOSTS_MSG)
    v_HOSTS = ",".join(HOSTS)


def get_umps_hosts(cluster, hosts):
    hlist = {}
    hlist['g1'] = []
    hlist['g2'] = []
    # for hosts in hostsdict.values():
    for host in hosts:
        if host.split(".")[0].split("-")[-1] == "phx" or host.split(".")[0].split("-")[-1] == "dfw" or \
                host.split(".")[0].split("-")[-1] == "frf" or host.split(".")[0].split("-")[-1] == "par" or \
                host.split(".")[0].split("-")[-1] == "ukb" or \
                host.split(".")[0].split("-")[-1] == "iad" or host.split(".")[0].split("-")[-1] == "ord" or \
                host.split(".")[0].split("-")[-1] == "hnd":
            # if host.split("-")[1].strip("1234") == "sshare":
            #    if host.split("-")[2] == "1" or host.split("-")[2] == "2":
            #        hlist['g1'].append(host.rstrip())
            #    elif host.split("-")[2] == "3" or host.split("-")[2] == "4":
            #        hlist['g2'].append(host.rstrip())
            if host.split("-")[2] == "1":
                hlist['g1'].append(host.rstrip())
            elif host.split("-")[2] == "2":
                hlist['g2'].append(host.rstrip())
        elif host.split(".")[0].split("-")[-1] == "lon":
            if host.split("-")[1].strip("1234") == "msg" or host.split("-")[1].strip("1234") == "dstore":
                if host.split("-")[2] == "1":
                    hlist['g1'].append(host.rstrip())
                elif host.split("-")[2] == "2":
                    hlist['g2'].append(host.rstrip())
            else:
                if host.split("-")[2] == "1" or host.split("-")[2] == "2":
                    hlist['g1'].append(host.rstrip())
                elif host.split("-")[2] == "3" or host.split("-")[2] == "4":
                    hlist['g2'].append(host.rstrip())
        else:
            if host.split("-")[1][-1] == "1":
                hlist['g1'].append(host.rstrip())
            elif host.split("-")[1][-1] == '2':
                hlist['g2'].append(host.rstrip())
    return hlist


# End

# Added For CMGTAPI ROLE to find other host as this service does not support HA.
# W-4171797

def FindOtherHost(Hostlist, HostToRemoveList):
    OHOSTS = Hostlist.split(",")
    HostToRemove = HostToRemoveList[0]
    try:
        OHOSTS.remove(HostToRemove)
    except ValueError:
        print("{0} Host does not exists or it has a invalid value".format(HostToRemove))
        sys.exit(1)

    if len(OHOSTS) != 1:
        print("List of Other Host Contains More then One Host, Use with Caution!")

    return ",".join(OHOSTS)


# END

# Added for STMGT Role to find all hosts expect the host is being patched.
# W-4506396
def FindOtherHostIfIdbQuery(dc, cluster, role, HostToRemoveList):
    idb = Idbhost()
    idb.clustinfo(dc, cluster)
    idb.deviceRoles(role)
    allhosts = idb.roles_all[cluster][role]
    if not isinstance(HostToRemoveList, list):
        allhosts = list(set(allhosts) - set(HostToRemoveList.split(",")))
    else:
        allhosts = list(set(allhosts) - set(HostToRemoveList))
    filtered_host = ",".join(allhosts)
    if not filtered_host:
        return HostToRemoveList
    else:
        return filtered_host


# End


def get_version_json():
    """
    :return:
    """
    home = os.path.expanduser("~")
    filepath = "/git/cptops_validation_tools/includes/valid_versions.json"
    path = home + filepath
    try:
        with open(path) as data_file:
            data = json.load(data_file)
    except Exception as e:
        print("Ensure presence of path " + path)
        sys.exit(1)
    return data


# W-4574049 Filter hosts by OS. This is specific CentOS migration project to exclude hosts which are already running on
# CentOS7
def filter_hosts_by_os(hosts, osmajor):
    """
    :param hosts: Total hosts given by user to filter
    :param osmajor: Major OS version [ 6 OR 7 ]
    :return: A list contains hosts which are running on osmajor OS
    """
    host_dict = {}
    allfiltered_hosts_os = []
    all_hosts = hosts.split(",")
    url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?name="
    try:
        response = requests.get(url + hosts, verify=False, timeout=20.0)
        if response.status_code == 200:
            data = response.json()

            for ddict in data:
                host_dict[ddict.get('hostName')] = ddict

            for host in all_hosts:
                if host not in host_dict.keys():
                    allfiltered_hosts_os.append(host)
                else:
                    ddict_host = host_dict.get(host)
                    os_version = ddict_host.get('patchOs')
                    if os_version == osmajor:
                        allfiltered_hosts_os.append(host)
            if len(allfiltered_hosts_os) != 0:
                return ",".join(allfiltered_hosts_os)

    except requests.exceptions.RequestException as e:
        print("Error while connecting to URL %s - %s" % (url, e))
        sys.exit(1)


# W-4574049 block end


# W-4531197 Adding logic to remove already patched host for Case.
def return_not_patched_hosts(hosts, skip_bundle):
    """
    :param hosts:
    :param bundle:
    :param skip_bundle:
    :return:
    """
    url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?name="
    response = requests.get(url + hosts, verify=False)
    host_dict = {}
    not_patched_hosts_all = []
    all_hosts = hosts.split(",")
    try:
        if response.status_code == 200:
            # str_data = response.content.split('(', 1)[1].split(')')[0] # Jarek changes his DB response from PJSON to JSON, This block of code works with PJSON
            # data = json.loads(str_data)
            data = json.loads(response.content)
            json_data = get_version_json().get('CENTOS')

            for ddict in data:
                host_dict[ddict.get('hostName')] = ddict
            for host in all_hosts:
                if host not in host_dict.keys():
                    not_patched_hosts_all.append(host)
                else:
                    ddict_host = host_dict.get(host)
		    if (ddict_host.get('hostOs') in json_data.keys()):
			bundle = json_data.get(ddict_host.get('patchOs')).get('current').get('sfdc-release')
                    if not skip_bundle:
                        jkernel = json_data.get(ddict_host.get('patchOs')).get(bundle).get('kernel')
                        if (bundle not in ddict_host.get('patchCurrentRelease')) or (
                                jkernel not in ddict_host.get('patchKernel')):
                            not_patched_hosts_all.append(host)
                    else:
                        if (ddict_host.get('patchCurrentRelease') < skip_bundle):
                            not_patched_hosts_all.append(host)

            if len(not_patched_hosts_all) != 0:
                return ",".join(not_patched_hosts_all)

    except Exception as e:
        print('Unable to get machine details: ', e)


# End


def compile_template(input, hosts, cluster, datacenter, superpod, casenum, role, num='', cl_opstat='', ho_opstat='',
                     template_vars=None):
    # Replace variables in the templates
    logging.debug('Running compile_template')

    output = input
    build_command = " ".join(sys.argv)
    build_command = build_command.replace("{", "'{")
    build_command = build_command.replace("}", "}'")
    host_list = hosts.split(',')

    global gblSplitHosts
    global gblExcludeList

    try:
        pdict = json.loads(options.idbgen)
        if pdict['superpod']:
            superpod = pdict['superpod']
    except:

        logging.debug('No idbgen passed')

        pass

    # before default ids in case of subsets
    for key, hostlist in gblSplitHosts.iteritems():
        output = output.replace(key, ",".join(hostlist))

    print
    'template_vars', template_vars
    hlist = hosts.split(",")

    if gblExcludeList:
        for excluded_host in gblExcludeList:
            while True:
                try:
                    hlist.remove(str(excluded_host))
                except:
                    break
    hosts = ",".join(hlist)

    # Added (By Amardeep)for Argus WriteD and Metrics role, It will replace the "argustsdbw" with "argusmetrics" as both has be done togeter in a serial manner.
    if "argustsdbw" in hosts:
        argusmetrics = hosts.replace('argustsdbw', 'argusmetrics')
        argustsdbw = hosts
        hosts = ','.join([argustsdbw, argusmetrics])
        if 'v_HOSTM' in output or 'v_HOSTD' in output:
            try:
                output = output.replace('v_HOSTD', argustsdbw)
                output = output.replace('v_HOSTM', argusmetrics)
            except UnboundLocalError:
                pass

    # End

    ## Check MNDS quorum status W-5550663
    tf = common.templatedir + "/" + "hbase-mnds.template"
    if os.path.isfile(template_file):
        with open(tf, 'r') as f:
            mndsData = f.readlines()
    v_MNDS = "".join(mndsData)

    try:
        if re.search(r"mnds", role, re.IGNORECASE):
            logging.debug(v_MNDS)
            output = output.replace('v_MNDS', v_MNDS)
        else:
            output = output.replace('v_MNDS', "- SKIPPING MNDS CHECK.")
    except:
        pass

    ## END ##

    # Ability to reuse templates and include sections. Include in refactoring
    if options.dowork and (datacenter in ("yhu", "yul", "syd", "cdu")):
        options.dowork = "system_update"
        output = getDoWork(output, options.dowork)
    else:
        output = getDoWork(output, options.dowork)

    """This code is to add unique comment to each line in implementation plan.
     e.g - release_runner.pl -forced_host $(cat ~/v_CASE_include) -force_update_bootstrap -c sudo_cmd -m "ls" -auto2 -threads
     -comment 'BLOCK 1'"""
    if 'v_COMMAND' not in output and 'mkdir ' not in output:
        o_list = output.splitlines(True)
        for i in range(len(o_list)):
            # Added to skip linebacker -  W-3779869
            if 'None' not in options.nolinebacker:
                regex_compile = re.compile('bigipcheck|remove_from_pool|add_to_pool', re.IGNORECASE)
                if regex_compile.search(o_list[i]):
                    o_list[i] = o_list[i].strip() + ' -nolinebacker' + "\n"
            if o_list[i].startswith('release_runner.pl') and 'BLOCK' not in o_list[i]:
                if datacenter == "PRD":
                    cmd = o_list[i].strip() + ' property "synner=1" -comment ' + "'BLOCK v_NUM'\n"
                else:
                    cmd = o_list[i].strip() + ' -comment ' + "'BLOCK v_NUM'\n"
                o_list.remove(o_list[i])
                o_list.insert(i, cmd)
            elif o_list[i].startswith('Exec_with') and 'BLOCK' not in o_list[i]:
                cmd = "Exec_with_creds: " + o_list[i][o_list[i].index(':') + 1:].strip() + " && echo 'BLOCK v_NUM'\n"
                o_list.remove(o_list[i])
                o_list.insert(i, cmd)
            elif o_list[i].startswith('Exec') and 'BLOCK' not in o_list[i]:
                cmd = "Exec: echo 'BLOCK v_NUM' && " + o_list[i][o_list[i].index(':') + 1:]
                o_list.remove(o_list[i])
                o_list.insert(i, cmd)
        output = "".join(o_list)

    # Add verify_host to template in memory and replace v_HOSTS to v_CASE_include
    if not options.no_host_v:
        # I made this assumption as role templates shouldn't have 'mkdir' and 'cp' commands, only pre templates
        if 'v_COMMAND' not in output and 'mkdir ' not in output:
            output = output.replace('v_HOSTS', '$(cat ~/v_CASE_include)')
            output_list = output.splitlines(True)
            if role not in ("secrets", "smszk"):
                output_list.insert(1,
                                   '\n- Verify if hosts are patched or not up\nExec: echo "Verify hosts BLOCK v_NUM" && '
                                   '/opt/cpt/bin/verify_hosts.py -H v_HOSTS --bundle v_BUNDLE --case v_CASE\n\n')
            output = "".join(output_list)
    #

    if options.checkhosts:
        hosts = '`~/check_hosts.py -H ' + hosts + '`'

    # UMPS Build Plan Generation Block W-3773536 | T-1747266
    umpshost = hosts
    umpshostlst = umpshost.split(',')
    if re.search(r"prsn|chan|msg|dstore", umpshost):
        idb = Idbhost()
        idb.vip_info(datacenter, 'chatter')
        v_VIP = idb.vip_dict[cluster]
        open("out.txt", 'w').close()
        print("UMPS PLAN GENRATION....")
        hlist = get_umps_hosts(cluster, umpshostlst)
        hlistkeys = sorted(hlist.keys())
        count = 0
        for group in hlistkeys:
            count += 1
            umpsout = output
            if not template_vars:
                if count == 2:
                    open("out.txt", 'w').close()
            for host in hlist[group]:
                build_Umps_Hostlist(host)
            # print(v_CPS1, v_DSTORE1, v_MSG1)
            umpsout = umpsout.replace('v_HOSTS', hosts)
            # umpsout = umpsout.replace('v_HOSTNAME_DSTORE', v_HOSTNAME_DSTORE)
            # umpsout = umpsout.replace('v_HOSTNAME_MSG', v_HOSTNAME_MSG)
            umpsout = umpsout.replace('v_VIP', v_VIP)
            umpsout = umpsout.replace('v_CPS1', v_CPS1)
            umpsout = umpsout.replace('v_DSTORE1', v_DSTORE1)
            umpsout = umpsout.replace('v_MSG1', v_MSG1)
            umpsout = umpsout.replace('v_CLUSTER', cluster)
            umpsout = umpsout.replace('v_DATACENTER', datacenter)
            umpsout = umpsout.replace('v_SUPERPOD', superpod)
            umpsout = umpsout.replace('v_CASENUM', casenum)
            umpsout = umpsout.replace('v_ROLE', role)
            umpsout = umpsout.replace('v_BUNDLE', options.bundle)
            umpsout = umpsout.replace('v_NUM', num)
            with open("out.txt", "a") as ou:
                ou.write(umpsout)
            clearUmpsList()
            try:
                num = str(int(num) + 1)
            except ValueError:
                pass

        with open("out.txt", "r") as out:
            output = out.read()
    # UMPS Build Plan Generation Block END
    else:
        output = output.replace('v_HOSTS', hosts)

        output = output.replace('v_HOST', host_list[0])
        # Added only to facilitate ARGUS_WRITED and ARGUS_METRICS roles to work together
        # End

        # W-4506396
        try:
            if re.search(r"stgmgt|cmgtapi|stgpm|lapp|searchmgr|searchidx|artifactrepo|rps", role, re.IGNORECASE):
                print(role)
                output = output.replace('v_OHOSTS', FindOtherHostIfIdbQuery(datacenter, cluster, role, hosts))
        except:
            pass

        # End
        output = output.replace('v_CLUSTER', cluster)
        output = output.replace('v_DATACENTER', datacenter)
        output = output.replace('v_SUPERPOD', superpod)
        output = output.replace('v_CASENUM', casenum)
        output = output.replace('v_ROLE', role)
        output = output.replace('v_BUNDLE', options.bundle)
        output = output.replace('v_NUM', num)
        # output = output.replace('v_GSIZE', str(options.gsize))

        # W-4574049
        # NOTE - This just an hack to calculate concurrency and threshold for CE7 migration hosts grouping

        if (str(len(hosts.split(',')) / 2)) == '0':
            thresh = str(1)
        else:
            thresh = str(len(hosts.split(',')) / 2)

        if options.hostpercent and options.failthresh:
            output = output.replace('v_GSIZE', str(len(hosts.split(','))))
            output = output.replace('v_FAILTHRESH', thresh)
        else:
            output = output.replace('v_GSIZE', str(options.gsize))
            output = output.replace('v_FAILTHRESH', str(options.failthresh))
        # W-4574049 End

    # # Total hack to pass kp_client concurrency and threshold values. Include in refactoring
    # if options.concur and options.failthresh:
    #     concur = options.concur
    #     failthresh = options.failthresh
    # else:
    #     concur, failthresh = getConcurFailure(role,cluster)
    # output = output.replace('v_CONCUR', str(concur))

    # if options.failthresh:
    #     output = output.replace('v_FAILTHRESH', str(options.failthresh))

    # Added to enable passing the hostfilter inside the plan.
    if options.idbgen and 'hostfilter' in json.loads(options.idbgen):
        input_values = json.loads(options.idbgen)
        output = output.replace('v_HOSTFILTER', input_values['hostfilter'])

    if not template_vars == None:
        if 'monitor-host' in template_vars.keys():
            output = output.replace('v_MONITOR', template_vars['monitor-host'])
        if 'serialnumber' in template_vars.keys():
            output = output.replace('v_SERIAL', template_vars['serialnumber'])
        if 'sitelocation' in template_vars.keys():
            output = output.replace('v_SITELOCATION', template_vars['sitelocation'])
        if 'product_rrcmd' in template_vars.keys():
            output = output.replace('v_PRODUCT_RRCMD', template_vars['product_rrcmd'])
        if 'ignored_process_names' in template_vars.keys():
            output = output.replace('v_IGNORE_PROCS_RRCMD_', template_vars['ignored_process_names'])
        if 'drnostart_rrcmd' in template_vars.keys():
            output = output.replace('v_DRNOSTART_RRCMD_', template_vars['drnostart_rrcmd'])
    # output = output.replace('v_SERIAL', options.monitor)
    output = output.replace('v_CL_OPSTAT', cl_opstat)
    output = output.replace('v_HO_OPSTAT', ho_opstat)
    output = output.replace('v_COMMAND', build_command)
    return output


def getDoWork(input, dowork):
    template_file = common.templatedir + "/" + str(dowork) + ".template"
    if os.path.isfile(template_file):
        with open(template_file, 'r') as f:
            data = f.readlines()
    v_include = "".join(data)
    try:
        if re.search(r"prsn|chan", ','.join(gblSplitHosts['v_HOSTNAME_CPS'])):
            u_include = v_include
            u_include = u_include.replace('v_HOSTS', 'v_CPS1,v_MSG1,v_DSTORE1')
            v_include = u_include
    except:
        pass

    input = input.replace('v_INCLUDE', v_include)
    return input


def getConcurFailure(role, cluster):
    rates = get_json('afw_presets.json')
    cluster_type = ''.join([i for i in cluster if not i.isdigit()])
    if cluster in rates and role in rates[cluster]:
        return rates[cluster][role]['concur'], rates[cluster][role]['failthresh']
    elif cluster_type in rates and role in rates[cluster_type]:
        return rates[cluster_type][role]['concur'], rates[cluster_type][role]['failthresh']
    else:
        return rates['concur'], rates['failthresh']


def prep_template(template, outfile):
    # Determine which bits are necessary to include in the final output.
    # This only preps the template. It does not write out anything.

    global pre_file
    global post_file
    global out_file
    global template_file

    logging.debug('Executing prep_template()')
    if options.clusterstatus == 'STANDBY':
        logging.debug('Template is for a standby cluster')
        template_file = common.templatedir + "/" + str(template) + "_standby.template"
        out_file = outfile + ".sb"
    else:
        logging.debug('Template is for a primary cluster')
        template_file = common.templatedir + "/" + str(template) + ".template"
        out_file = outfile
    print
    out_file

    # Assuming that we do NOT want separate pre/post script for active/standby
    # forcing to use the basename pre/post (for example - search.template.pre)
    # as opposed to search_standby.template.pre

    logging.debug('Using template file: ' + template_file)

    if not os.path.isfile(template_file):
        print(template_file + " is not a file that exists. Check your template name.")
        exit()

    template_basename = re.sub(r'_standby', "", template_file)

    logging.debug('Basename template: ' + template_basename)

    if os.path.isfile(str(template_basename) + ".pre"):
        logging.debug('Pre template exists')
        pre_file = template_basename + ".pre"
    else:
        logging.debug('Using generic pre template')
        pre_file = common.templatedir + "/generic.pre"

    if os.path.isfile(str(template_basename) + ".post"):
        logging.debug('Post template exists')
        post_file = template_basename + ".post"
    else:
        logging.debug('Using generic post template')
        post_file = common.templatedir + "/generic.post"


def gen_plan(hosts, cluster, datacenter, superpod, casenum, role, num, groupcount=0, cl_opstat='', ho_opstat='',
             template_vars={}):
    # Generate the main body of the template (per host)
    logging.debug('Executing gen_plan()')
    print
    "Generating: " + out_file
    s = open(template_file).read()
    org_host = hosts
    global not_patched_hosts
    global not_os_hosts

    # W-4574049 Compile template for hosts which are filtered by OS
    if options.os:
        hosts = filter_hosts_by_os(hosts, options.os)
        if hosts is None:
            s = "- Skipping, hosts {0} already running on CentOS7".format(org_host)
        else:
            for h in hosts.split(","):
                not_os_hosts.append(h)
            s = compile_template(s, hosts, cluster, datacenter, superpod, casenum, role, num, cl_opstat, ho_opstat,
                                 template_vars)

    # W-4574049 block end

    # W-4531197 Adding logic to remove already patched host for Case.
    elif options.delpatched or options.skip_bundle:
        if not options.skip_bundle:
            options.skip_bundle = None
        hosts = return_not_patched_hosts(hosts, options.skip_bundle)
        if hosts == None:
            s = "- Skipped Already Patched host {0} for bundle {1} or {2}".format(org_host, options.bundle,
                                                                                  options.skip_bundle)
        else:
            for h in hosts.split(","):
                not_patched_hosts.append(h)
            s = compile_template(s, hosts, cluster, datacenter, superpod, casenum, role, num, cl_opstat, ho_opstat,
                                 template_vars)
    else:
        s = compile_template(s, hosts, cluster, datacenter, superpod, casenum, role, num, cl_opstat, ho_opstat,
                             template_vars)
    # End

    f = open(out_file, 'w')
    f.write(s)
    f.close()


def apply_grouptags(content, tag_id):
    return 'BEGIN_GROUP: ' + tag_id + '\n\n' + content + '\n\n' + \
           'END_GROUP: ' + tag_id + '\n'


def rewrite_groups(myglob, taggroups):
    myglob.sort(key=humanreadable_key)
    groupid = 1
    i = 1
    content = ''
    logging.debug("Files in output dir: " + str(len(myglob)))
    if taggroups > len(myglob):
        raise Exception(
            'taggroups parameter is greater than the number of groups, try reducing value for maxgroupsize or taggroups')
    # we need to decrement the taggroups if there will be hosts left over in the last group
    if len(myglob) % taggroups != 0:
        taggroups -= 1

    gtsize = len(myglob) / taggroups
    gtsize = 1 if gtsize == 0 else gtsize

    print
    'Tag groups : ' + str(taggroups)
    print
    'tag group size :' + str(gtsize)
    print
    'number of files ' + str(len(myglob))
    for f in myglob:
        print
        'rewriting file : ' + f
        content += open(f, "r").read() + '\n\n'
        os.remove(f)
        if i == len(myglob):
            print
            'rewriting all content to file :' + str(groupid) + '_group_plan_implementation.txt'
            content = apply_grouptags(content, str(groupid))
            open(common.outputdir + '/' + str(groupid) + '_group_plan_implementation.txt', 'w').write(content)
            break
        if (i >= gtsize) and (i % gtsize == 0):
            print
            'rewriting all above to file :' + str(groupid) + '_group_plan_implementation.txt'
            content = apply_grouptags(content, str(groupid))
            open(common.outputdir + '/' + str(groupid) + '_group_plan_implementation.txt', 'w').write(content)
            content = ''
            groupid += 1
        i += 1
        # with open(f, "r") as infile:
        #    logging.debug('Writing out: ' + f + ' to ' + consolidated_file)
        #    final_file.write(infile.read() + '\n\n')


def consolidate_plan(hosts, cluster, datacenter, superpod, casenum, role):
    # Consolidate all output into a single implementation plan.
    # This is the bit that tacks on the pre-post scripts

    logging.debug('Executing consolidate_plan()')
    if options.taggroups > 0:
        rewrite_groups(glob.glob(common.outputdir + "/*"), options.taggroups)
    consolidated_file = common.outputdir + '/plan_implementation.txt'
    print
    "Consolidating output into " + consolidated_file
    print
    'Role :' + role

    with open(consolidated_file, 'a') as final_file:
        if options.tags:
            final_file.write("BEGIN_DC: " + datacenter.upper() + '\n\n')

        if pre_file and not options.nested:  # skip pre template for nested

            with open(pre_file, "r") as pre:
                pre = pre.read()
                pre = compile_template(pre, hosts, cluster, datacenter, superpod, casenum, role)

                logging.debug('Writing out prefile ' + pre_file + '  to ' + consolidated_file)
                final_file.write('BEGIN_GROUP: PRE\n' + pre + '\nEND_GROUP: PRE\n\n')

        # Append individual host files.

        read_files = glob.glob(common.outputdir + "/*")
        read_files.sort(key=humanreadable_key)
        for f in read_files:
            if f != common.outputdir + '/plan_implementation.txt':
                with open(f, "r") as infile:
                    logging.debug('Writing out: ' + f + ' to ' + consolidated_file)
                    final_file.write(infile.read() + '\n\n')

        if post_file and not options.nested:  # skip post template for nested
            # Append postfile
            with open(post_file, "r") as post:
                post = post.read()
                post = compile_template(post, hosts, cluster, datacenter, superpod, casenum, role)
                # This code to add auto close case to post templates
                if options.auto_close_case:
                    post_list = post.splitlines(True)
                    str_to_add = "- Auto close case \nExec_with_creds: /opt/cpt/gus_case_mngr.py -c v_CASE --close -y\n\n"
                    post_list.insert(2, str_to_add)
                    post = "".join(post_list)
                logging.debug('Writing out post file ' + post_file + ' to ' + consolidated_file)
                final_file.write('BEGIN_GROUP: POST\n' + post + '\nEND_GROUP: POST\n\n')
        if options.tags:
            final_file.write("END_DC: " + datacenter.upper() + '\n\n')

    with open(consolidated_file, 'r') as resultfile:
        result = resultfile.readlines()

    return result


def cleanup_out():
    cleanup = glob.glob(common.outputdir + "/*")
    for junk in cleanup:
        os.remove(junk)


def find_concurrency(hostpercent):
    """
    This function calculates the host count per block #W-3758985
    :param inputdict: takes inputdict
    :return: maxgroupsize
    """
    a_hosts = []
    n_hosts = []
    idb = Idbhost()
    pod = inputdict['clusters']
    dc = inputdict['datacenter']
    idb.clustinfo(dc, pod)
    role = inputdict['roles']
    idb.deviceRoles(role)
    total_hosts = idb.roles_all.values()[0].values()[0]
    idb.gethost(total_hosts)
    for h in total_hosts:
        if 'ACTIVE' in idb.mlist[h]['opsStatus_Host']:
            a_hosts.append(h)
        else:
            n_hosts.append(h)
    inputdict['maxgroupsize'] = int(hostpercent) * (len(a_hosts)) / 100


def gen_plan_by_idbquery(inputdict):
    # set defaults values
    assert 'datacenter' in inputdict, "must specify 1 or more datacenters"

    idbfilters = {}
    dcs = tuple(inputdict['datacenter'].split(','))
    idbfilters["cluster.dr"] = inputdict['dr'].split(',') if 'dr' in inputdict else 'False'
    idbfilters["cluster.operationalStatus"] = inputdict['cl_opstat'].split(
        ',') if 'cl_opstat' in inputdict else 'ACTIVE'
    idbfilters["operationalStatus"] = inputdict['ho_opstat'].split(',') if 'ho_opstat' in inputdict else 'ACTIVE'

    # for key in ('datacenters','clusters','superpods','roles','clusterTypes','opstat','dr' ):

    if 'roles' in inputdict:
        idbfilters["deviceRole"] = inputdict['roles'].split(',')
    if 'clusters' in inputdict:
        idbfilters["cluster.name"] = inputdict['clusters'].split(',')
    if 'clusterTypes' in inputdict:
        idbfilters["cluster.clusterType"] = inputdict['clusterTypes'].split(',')
    if 'superpods' in inputdict:
        idbfilters["cluster.superpod.name"] = inputdict['superpods'].split(',')
    if 'superpod' in inputdict:
        idbfilters["cluster.superpod.name"] = inputdict['superpod'].split(',')

    # optional paramters
    # defaults

    regexfilters = {}

    # calculate host count for app role
    if options.hostpercent:
        find_concurrency(options.hostpercent)

    gsize = inputdict['maxgroupsize'] if 'maxgroupsize' in inputdict else 1

    grouping = ['superpod']
    if 'grouping' in inputdict:
        grouping = grouping + inputdict['grouping'].split(',')

    template_id = 'AUTO'
    if 'templateid' in inputdict:
        template_id = inputdict['templateid']
    if template_id != "AUTO":
        assert os.path.isfile(
            common.templatedir + "/" + str(template_id) + ".template"), template_id + " template not found"

    if 'hostfilter' in inputdict:  # this is for backwards compatibility
        regexfilters['hostname'] = inputdict['hostfilter']

    if 'regexfilter' in inputdict:
        for pair in inputdict['regexfilter'].split(';'):
            field, regex = pair.split('=')
            field = field.lower()  # for backward compatibility
            regexfilters[field] = regex

    print
    logging.debug('Regexfilters:')
    logging.debug(regexfilters)

    logging.debug(supportedfields)
    logging.debug(idbfilters)
    logging.debug(regexfilters)

    bph = Buildplan_helper(dcs, endpoint, supportedfields, idbfilters)
    bph.apply_regexfilters(regexfilters)
    writeplan = bph.apply_groups(grouping, template_id, gsize)

    consolidate_idb_query_plans(writeplan, dcs)


def consolidate_idb_query_plans(writeplan, dcs):
    allplans = {}
    fullhostlist = []
    writelist = []
    ok_dclist = []
    for template in writeplan:
        allplans[template] = {}
        for dc in dcs:
            if (dc,) not in writeplan[template].keys():
                continue
            allplans[template][dc] = write_plan_dc(dc, template, writeplan)
            ok_dclist.append(dc)

    logging.debug(allplans)
    for template in allplans:
        for dc in set(ok_dclist):
            if not dc in allplans[template].keys():
                continue
            content, hostlist = allplans[template][dc]
            writelist.extend(content)
            fullhostlist.extend(hostlist)

    # Hack to get list of all hosts for scrtkafka validation W-4415118
    # NOTE - Keyword any return True if any element of the iterable is true. If the iterable is empty, return False.

    if any(i for i in writelist if 'v_ALLHOSTS' in i):
        final_write = [i.replace('v_ALLHOSTS', ",".join(fullhostlist)) for i in writelist]
        writelist = final_write
    write_list_to_file(common.outputdir + '/plan_implementation.txt', writelist, newline=False)

    global gblExcludeList

    if gblExcludeList:
        for excluded_host in gblExcludeList:
            while True:
                try:
                    fullhostlist.remove(str(excluded_host))
                except:
                    break
    # Added (By Amardeep)for Argus WriteD and Metrics role, It will replace the "argustsdbw" with "argusmetrics" as both has be done togeter in a serial manner.
    fullhostlist1 = []
    for host in fullhostlist:
        if "argustsdbw" in host:
            fullhostlist1.append(host.replace('argustsdbw', 'argusmetrics'))
    fullhostlist = fullhostlist + fullhostlist1
    # End

    if options.os:
        write_list_to_file(common.outputdir + '/summarylist.txt', not_os_hosts)
        if os.stat(common.outputdir + '/summarylist.txt').st_size == 0:
            os.remove(common.outputdir + '/plan_implementation.txt')


    # Added to remove already pacthed host.
    elif options.delpatched or options.skip_bundle:
        write_list_to_file(common.outputdir + '/summarylist.txt', not_patched_hosts)

        if os.stat(common.outputdir + '/summarylist.txt').st_size == 0:
            os.remove(common.outputdir + '/plan_implementation.txt')

        # Test to track hosts
        # with open("/tmp" + '/not_patched_hosts.txt', 'a') as output, open(
        #                 common.outputdir + '/summarylist.txt', 'r') as input:
        #     while True:
        #         data = input.read()
        #         if data == '':  # end of file reached
        #             break
        #         output.write(data)
        # End
    else:
        write_list_to_file(common.outputdir + '/summarylist.txt', fullhostlist)


def write_plan_dc(dc, template_id, writeplan):
    global gblSplitHosts
    grouptagcount = 0
    results = writeplan[template_id][(dc,)]

    i = 0
    p = 1

    allhosts = []
    allclusters = []
    allsuperpods = []
    allroles = []

    template_vars = {}
    cleanup_out()

    for mygroup in sorted(results.keys()):
        for sizegroup in sorted(results[mygroup]):
            i += 1
            hostnames = results[mygroup][sizegroup]['hostname']
            superpod = ','.join(results[mygroup][sizegroup]['superpod'])
            clusters = results[mygroup][sizegroup]['cluster']
            roles = results[mygroup][sizegroup]['role']
            cluster_operationalstatus = results[mygroup][sizegroup]['cluster_operationalstatus']
            host_operationalstatus = results[mygroup][sizegroup]['host_operationalstatus']
            if options.monitor == True:
                template_vars['monitor-host'] = ','.join(results[mygroup][sizegroup]['monitor-host'])
            if options.serial == True:
                template_vars['serialnumber'] = ','.join(results[mygroup][sizegroup]['serialnumber'])
            template_vars['sitelocation'] = ','.join(results[mygroup][sizegroup]['sitelocation'])
            template_vars['drnostart_rrcmd'] = ','.join(results[mygroup][sizegroup]['drnostart_rrcmd'])
            template_vars['product_rrcmd'] = ','.join(results[mygroup][sizegroup]['product_rrcmd'])
            template_vars['ignored_process_names'] = ','.join(results[mygroup][sizegroup]['ignored_process_names'])
            # gather rollup info
            allhosts.extend(hostnames)
            allclusters.extend(clusters)
            allroles.extend(roles)
            allsuperpods.append(superpod)

            # fileprefix = str(group_enum) + str(i) + '_' + str(clusters)
            fileprefix = str(i)
            gblSplitHosts = build_dynamic_groups(hostnames)
            logging.debug(gblSplitHosts)
            # The following section is to manage dynamic grouping while writing plan. Currently being hardcoded to 10%
            if 'ajna_broker' in roles:
                g_div = int(10 * len(hostnames) / 100)
                if g_div == 0: g_div = 1
                ho_lst = [hostnames[j: j + g_div] for j in range(0, len(hostnames), g_div)]
                for h in ho_lst:
                    prep_template(template_id, common.outputdir + '/' + str(p) + "_plan_implementation.txt")
                    gen_plan(','.join(h).encode('ascii'), ','.join(clusters), dc, superpod, options.caseNum,
                             ','.join(roles), str(p), p, ','.join(cluster_operationalstatus),
                             ','.join(host_operationalstatus), template_vars)
                    p += 1
            else:
                prep_template(template_id, common.outputdir + '/' + fileprefix + "_plan_implementation.txt")
                gen_plan(','.join(hostnames).encode('ascii'), ','.join(clusters), dc, superpod, options.caseNum,
                         ','.join(roles),
                         fileprefix, i, ','.join(cluster_operationalstatus), ','.join(host_operationalstatus),
                         template_vars)

    consolidated_plan = consolidate_plan(','.join(set(allhosts)), ','.join(set(allclusters)), dc,
                                         ','.join(set(allsuperpods)), options.caseNum, ','.join(set(allroles)))
    print
    'Template: ' + template_id
    return consolidated_plan, sorted(allhosts)


def get_clean_hostlist(hostlist):
    hostnames = []
    dcs = []
    roles = []
    pods = []
    hostlist_chk = re.compile(r'\w*-\w*-\d-\w*[\S|,]*')
    output_list = hostlist_chk.search(hostlist)
    if output_list:
        hostlist = output_list.group().split(',')

    if isinstance(hostlist, list):
        for line in hostlist:
            dc = line.split('-')[3]
            role = line.split('-')[1].rstrip('1234567890.')
            pod = line.split('-')[0]
            if pod not in pods:
                pods.append(pod)
            if role not in roles:
                roles.append(role)
            if dc not in dcs:
                dcs.append(dc)
            hostnames.append(line)
    else:
        file = open(hostlist).readlines()
        for line in file:
            dc = line.split('-')[3].rstrip('\n')
            role = line.split('-')[1].rstrip('1234567890.\n')
            pod = line.split('-')[0].rstrip('\n')
            if pod not in pods:
                pods.append(pod)
            if role not in roles:
                roles.append(role)
            if dc not in dcs:
                dcs.append(dc)
            hostnames.append(line.rstrip('\n').rstrip())

    return dcs, hostnames, roles, pods


def gen_nested_plan_idb(hostlist, templates, regex_dict, group_dict, gsize):
    imp_plans = {
        'plan': []
    }
    dcs, hostnames, role, pods = get_clean_hostlist(options.hostlist)
    idbfilters = {'name': hostnames}
    bph = Buildplan_helper(dcs, endpoint, supportedfields, idbfilters, True)
    for nestedtemplate in templates:
        if not os.path.isfile(common.templatedir + '/' + nestedtemplate + '.template'):
            continue
        regexfilters = {}
        groups = []
        refresh = False
        writeplan = bph.apply_groups(groups, nestedtemplate, gsize)
        print
        'options:', regex_dict[nestedtemplate], group_dict[nestedtemplate]
        if regex_dict[nestedtemplate] != '':
            regexfilters = {"hostname": regex_dict[nestedtemplate]}
            refresh = True
        if group_dict[nestedtemplate] != '':
            groups = [group_dict[nestedtemplate]]
            refresh = True
        print
        'REfresh: ', True
        if refresh is True:
            bph.apply_regexfilters(regexfilters)
            writeplan = bph.apply_groups(grouping, templateid, gsize)
            bph.remove_regexfilters()
        consolidate_idb_query_plans(writeplan, dcs)
        imp_plans['plan'].extend(['BEGIN_GROUP: ' + nestedtemplate.upper(), '\n'])
        imp_plans['plan'].extend(open(common.outputdir + '/plan_implementation.txt').readlines())
        imp_plans['plan'].extend(['END_GROUP: ' + nestedtemplate.upper(), '\n', '\n'])
    write_list_to_file(common.outputdir + '/plan_implementation.txt', imp_plans['plan'], newline=False)
    write_list_to_file(common.outputdir + '/summarylist.txt', hostnames, newline=True)


def gen_plan_by_hostlist_idb(hostlist, templateid, gsize, grouping):
    dcs, hostnames, roles, pods = get_clean_hostlist(hostlist)
    idbfilters = {'name': hostnames}

    bph = Buildplan_helper(dcs, endpoint, supportedfields, idbfilters, True)
    writeplan = bph.apply_groups(grouping, templateid, gsize)
    consolidate_idb_query_plans(writeplan, dcs)


def gen_plan_by_hostlist(hostlist, templateid, gsize, groups):
    dcs, hostnames, role, pods = get_clean_hostlist(options.hostlist)

    bph = Buildplan_helper(dcs, None, supportedfields, {}, False, hostnames)
    writeplan = bph.apply_groups(groups, templateid, gsize)
    consolidate_idb_query_plans(writeplan, dcs)


###############################################################################
#                Main
###############################################################################
usage = """
            * Generate an implementation plan based on IDB data.

            ** This script can be called two ways:
                1.) Directly as ./%prog
                2.) Indirectly via hostgetter.py. See usage for hostgetter.py.

            Usage:

            - Process a hostlist in a sequential manner
            %prog -c 123 -l ../etc/hostlist -x -v

            - Process a hostlist in parallel
            %prog -c 123 -l ../etc/hostlist -x -a -v

            - Override the default (role name) template
            %prog -c 123 -l ../etc/hostlist -t spellchecker.glibc -x -a -v

            -get JSON file with all pods for geos for prod and DR
            %prog -g was,chi -o ~/outfile

            """

parser = OptionParser(usage)
parser.add_option("-c", "--case", dest="caseNum", help="The case number to use",
                  default='01234')
parser.add_option("-s", "--superpod", dest="superpod", help="The superpod")
parser.add_option("-S", "--status", dest="clusterstatus", \
                  help="The cluster status - PRIMARY/STANDBY", default="PRIMARY")
parser.add_option("-i", "--clusterance", dest="cluster", help="The clusterance")
parser.add_option("-d", "--datacenter", dest="datacenter", help="The datacenter")
parser.add_option("-t", "--template", dest="template", default="AUTO", help="Override Template")
parser.add_option("-l", "--hostlist", dest="hostlist", help="Path to list of hosts", \
                  default='hostlist')
parser.add_option("-r", "--role", dest="role", help="Host role")
parser.add_option("-H", "--host", dest="host", help="The host")
parser.add_option("-f", "--filename", dest="filename", \
                  default="plan_implementation.txt", help="The output filename")
parser.add_option("-v", action="store_true", dest="verbose", default=False, \
                  help="verbosity")
parser.add_option("-e", action="store_true", dest="endrun", default=False, \
                  help="End the run and consolidate files")
parser.add_option("-m", dest="manual", default=False, \
                  help="Manually override idb")
parser.add_option("-a", action="store_true", dest="allatonce", default=False, \
                  help="End the run and consolidate files")
parser.add_option("-x", action="store_true", dest="skipidb", default=False, \
                  help="Use for testing idbhost")
parser.add_option("-G", "--idbgen", dest="idbgen", help="generate from idb")
parser.add_option("-C", "--cidblocal", dest="cidblocal", action='store_true', default=True, \
                  help="access cidb from your local machine")
parser.add_option("-g", "--geo", dest="geo", help="geo list")
parser.add_option("-o", "--out", dest="out", help="output file")
parser.add_option("-M", dest="grouping", type="str", default="majorset,minorset", help="Turn on grouping")
parser.add_option("--gsize", dest="gsize", type="int", default=1, help="Group Size value")
parser.add_option("--bundle", dest="bundle", default="current", help="Patchset version")
parser.add_option("--monitor", dest="monitor", action="store_true", default=False, help="Monitor host")
parser.add_option("--serial", dest="serial", action="store_true", default=False, help="Monitor host")
parser.add_option("--hostpercent", dest="hostpercent", help="Host percentage for core app")
parser.add_option("--concurr", dest="concur", type="int", help="Concurrency for kp_client batch")
parser.add_option("--failthresh", dest="failthresh", type="int", help="Failure threshold for kp_client batch")
parser.add_option("--nested_template", dest="nested", default=False,
                  help="pass a list of templates, for use with hostlists only")
parser.add_option("--checkhosts", dest="checkhosts", action="store_true", default=False, help="Monitor host")
parser.add_option("--exclude", dest="exclude_list", default=False, help="Host Exclude List")
parser.add_option("-L", "--legacyversion", dest="legacyversion", default=False, action="store_true",
                  help="flag to run new version of -G option")
parser.add_option("-T", "--tags", dest="tags", default=False, action="store_true",
                  help="flag to run new version of -G option")
parser.add_option("--taggroups", dest="taggroups", type="int", default=0, help="number of sub-plans per group tag")
parser.add_option("--dowork", dest="dowork", help="command to supply for dowork functionality")
parser.add_option("--no_host_validation", dest="no_host_v", action="store_true", help="Skip verify remote hosts")
parser.add_option("--auto_close_case", dest="auto_close_case", action="store_true", default="True",
                  help="Auto close cases")
parser.add_option("--nolinebacker", dest="nolinebacker", help="Don't use linebacker")
# W-4531197 Adding logic to remove already patched host for Case.
parser.add_option("--delpatched", dest="delpatched", action='store_true', help="command to remove patched host.")
parser.add_option("--skip_bundle", dest="skip_bundle", help="command to skip bundle")
# End
# W-4574049 Command line option to filter hosts by OS [Specific to CentOS7 Migration ]
parser.add_option("--os", dest="os", help="command to filter hosts based on major set, Valid Options are 6 and 7")
# W-4574049 end


(options, args) = parser.parse_args()
if __name__ == "__main__":
    try:
        if options.os:
            if options.os != "6" and options.os != "7":
                print("\n--os valid options are 6 and 7, provided {0}\n".format(options.os))
                sys.exit(1)

        if options.serial == True:
            endpoint = 'hosts?'
            supportedfields['serialnumber'] = 'serialNumber'
        else:
            endpoint = 'allhosts?'
        if options.monitor == True:
            supportedfields['monitor-host'] = ['cluster.clusterConfigs', {'key': 'monitor-host'}]
        if not options.bundle:
            options.bundle = "bundle"
        else:
            options.bundle = options.bundle

        if options.exclude_list:
            with open(options.exclude_list) as f:
                lines = f.read().splitlines()
            gblExcludeList = lines
        else:
            gblExcludeList = False

        if options.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.ERROR)

        if not os.path.exists(common.outputdir):
            logging.debug('Creating output dir')
            os.makedirs(common.outputdir)

        if options.geo:
            geolist = options.geo.split(',')
            get_dr_prod_by_dc(geolist, options.out)
            exit()

        if options.idbgen:
            inputdict = json.loads(options.idbgen)
            if options.legacyversion:
                gen_plan_by_cluster_hostnumber(inputdict)
                print
                "You ran the legacy version"
            else:
                gen_plan_by_idbquery(inputdict)
                # Genrate json file for blackswan.
                from caseToblackswan import CreateBlackswanJson

                CreateBlackswanJson(inputdict, options.bundle)
                # END#
            exit()
        elif options.allatonce and not options.skipidb:
            cleanup_out()
            hosts = ','.join(get_hosts_from_file(options.hostlist))
            prep_template(options.template, common.outputdir + '/' + 'allhosts_' + options.filename)
            gen_plan(hosts, options.cluster, options.datacenter, options.superpod, options.caseNum, options.role)
            consolidate_plan(hosts, options.cluster, options.datacenter, options.superpod, options.caseNum,
                             options.role)
            exit()

        if options.skipidb:
            # Clean up the old output files
            cleanup_out()

            if options.manual:
                print('Overriding IDB with data from {0}'.format(options.manual))
                json_data = open(options.manual).read()
                data = json.loads(json_data)
                options.role = data["role"]
                options.cluster = data["cluster"]
                options.superpod = data["superpod"]
                options.caseNum = data["casenum"]
                role = options.role
                cluster = options.cluster
                superpod = options.superpod
                casenum = options.caseNum

                hosts = get_hosts_from_file(options.hostlist)
                gblSplitHosts = build_dynamic_groups(hosts)

                if options.allatonce:
                    # process the plan in parallel
                    hostnames = []
                    for hostname in hosts:
                        outfile = common.outputdir + '/allhosts_plan_implementation.txt'
                        hostnames.append(hostname)
                        datacenter = hostname.rsplit('-', 1)[1]

                        if options.template:
                            template = options.template
                        else:
                            template = role

                        allhosts = ','.join(hostnames)
                        hosts = allhosts
                        prep_template(template, outfile)
                        gen_plan(hosts, cluster, datacenter, superpod, casenum, role)

                else:

                    # process the plan in series
                    for hostname in hosts:
                        outfile = common.outputdir + '/' + hostname + '_plan_implementation.txt'
                        hosts = hostname
                        datacenter = hostname.rsplit('-', 1)[1]

                    if options.template:
                        template = options.template
                    else:
                        template = role

                    prep_template(template, outfile)
                    gen_plan(hosts, cluster, datacenter, superpod, casenum, role)

                consolidate_plan(hosts, cluster, datacenter, superpod, casenum, role)
                exit()
            if options.grouping:
                dcs, hostnames, role, pods = get_clean_hostlist(options.hostlist)
                inputdict = {"datacenter": ','.join(dcs), "superpod": 'none', "roles": ','.join(role),
                             "clusters": ','.join(pods)}
                gen_plan_by_hostlist(options.hostlist, options.template, options.gsize, options.grouping.split(','))
                from caseToblackswan import CreateBlackswanJson

                CreateBlackswanJson(inputdict, options.bundle)
                exit()

        if options.nested and options.hostlist:
            groups = options.grouping.split(',')
            templates = open(common.templatedir + "/" + options.nested + '.template').readlines()
            regex_dict = {}
            grouping_dict = {}
            template_list = []
            for template in templates:
                values = template.strip().split(':')
                hostregex = ''
                groupby = ''
                if len(values) == 3:
                    temp, groupby, hostregex = values
                else:
                    temp = values[0]
                grouping_dict[temp] = groupby
                regex_dict[temp] = hostregex
                template_list.append(temp)
            gen_nested_plan_idb(options.hostlist, template_list, regex_dict, grouping_dict, options.gsize)
            exit()

        if options.hostlist:
            # hostlist_chk = re.compile(r'([a-z,0-9,-]*)')
            groups = options.grouping.split(',')
            if not options.template:
                options.template = 'AUTO'
            gen_plan_by_hostlist_idb(options.hostlist, options.template, options.gsize, groups)
            exit()

        if options.endrun:
            # This hack will go away once Mitchells idbhelper module is merged.
            prep_template(options.template, options.filename)
            consolidate_plan(options.host, options.cluster, options.datacenter, options.superpod, options.caseNum,
                             options.role)
        elif not options.idbgen:
            prep_template(options.template, options.filename)
            gen_plan(options.host, options.cluster, options.datacenter, options.superpod, options.caseNum, options.role)

    except Exception:
        cleanup_out()
        raise
else:
    # default options for build_plan unit test
    options.idbgen = True
    gblExcludeList = False
