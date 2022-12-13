#!/usr/bin/python
#
#
import requests,re,pprint,sys,glob,os,argparse,logging,json,concurrent.futures
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from modules.grouper import Groups
from caseToblackswan import CreateBlackswanJson
from idbhost import Idbhost


# Global assignments
pp = pprint.PrettyPrinter(indent=2)
global new_data
global hbase_rnd_idb_flag
active_hosts = []


def tryint(s):
    """
        convert key to string for ordering using human readable_key
    """
    try:
        return int(s)
    except:
        return s


def sort_key(s):
    """
        function for sorting lists of values to make them readable from left to right
    """
    s = str(s)

    return [tryint(c) for c in re.split('([0-9]+)', s)]


def url_response(url):
    response = requests.get(url, verify=False)
    if response.json() is None:
        logging.error("No Data Present")
        sys.exit(1)
    return response.json()


def get_data(cluster, role, dc):
    '''
    Function queries blackswan for data. It then strips the necessary information and recreates it
    into the master_json dictionary.
    :return:
    '''
    master_json = {}
    ice_chk = re.compile(r'ice|mist')
    nonactive_json = {}
    if cluster != "NA":
        url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?cluster={}&role={}&dc={}".format(cluster, role, dc)
    else:
        url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?role={}&dc={}".format(role, dc)

    data = url_response(url)
    allhosts_for_vohosts = []

    for host in data:
        logging.debug("{}: patchCurrentRelease:{} clusterStatus:{} hostStatus:{} hostFailover:{}".format(host['hostName'],
                                                                                                         host['patchCurrentRelease'],
                                                                                                         host['clusterStatus'],
                                                                                                         host['hostStatus'],
                                                                                                         host['hostFailover']))
        json_data = {'RackNumber': host['hostRackNumber'], 'Role': host['roleName'],
                     'Bundle': host['patchCurrentRelease'], 'Majorset': host['hostMajorSet'],
                     'Minorset': host['hostMinorSet'], 'OS_Version': host['patchOs']}
        host_json = json.dumps(json_data)
        allhosts_for_vohosts.append(host["hostName"])
        if host['hostStatus'] == "ACTIVE":
            active_hosts.append(host['hostName'])

        def _sorting_host(json_file):
            if host['superpodName'] in pod_dict.keys():
                if options.skip_bundle:
                    if host['patchCurrentRelease'] < options.skip_bundle or "migration" in templateid .lower():
                        json_file[host['hostName']] = json.loads(host_json)
                    else:
                        logging.debug("{}: patchCurrentRelease is {}, skipped".format(host['hostName'], host['patchCurrentRelease']))
                else:
                    json_file[host['hostName']] = json.loads(host_json)
            else:
                logging.debug("{}: Superpod is {}, excluded".format(host['hostName'], host['superpodName']))

        if host['hostFailover'] == failoverstatus or failoverstatus == None:
            if host['clusterStatus'] in set(cl_status.split(",")):
                if host['hostStatus'] in set(ho_status.split(",")):
                    _sorting_host(master_json)
                else:
                    logging.debug("{}: hostStatus is {}, added to non active json".format(host['hostName'], host['hostStatus']))
            else:
                logging.debug("{}: clusterStatus is {}, added to non active json".format(host['hostName'], host['clusterStatus']))
            if host['clusterStatus'] != "ACTIVE" or host['hostStatus'] != "ACTIVE":
                if host['clusterStatus'] in set(cl_status.split(",")) and host['hostStatus'] not in set(ho_status.split(",")):
                    _sorting_host(nonactive_json)
                else:
                    logging.debug("{}: hostStatus is {}, added to active json ".format(host['hostName'], host['hostStatus']))
        else:
            logging.debug("{}: failoverStatus is {}, excluded".format(host['hostName'], host['hostFailover']))

    def _sorting_jsons(json_file):
        json_file, os_ce6, os_ce7 = bundle_cleanup(json_file, options.bundle)
        json_file = hostfilter_chk(json_file)
        if options.os_version:
            json_file = os_chk(json_file)
        return json_file, os_ce6, os_ce7
    master_json, os_ce6, os_ce7 = _sorting_jsons(master_json)
    nonactive_json, os_ce6, os_ce7 = _sorting_jsons(nonactive_json)
    if master_json:
        logging.debug("Master Json {}".format(master_json))
    if nonactive_json:
        logging.debug("Non-Active Json {}".format(nonactive_json))
    if not master_json and not nonactive_json:
        logging.error("No servers match any filters.")
        sys.exit(1)
    return master_json, nonactive_json, allhosts_for_vohosts, os_ce6, os_ce7


def hostfilter_chk(data):
    if hostfilter:
        host_filter = re.compile(r'{}'.format(hostfilter))
        for host in data.keys():
            if not host_filter.match(host):
                logging.debug("{} does not match ...".format(host))
                del data[host]
    return data

def get_hostlist_data(data):
    """
    This queries each host to build the master_json file.
    :param data
    :return: master_json
    """
    master_json = {}
    host_url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts"
    hl_fh = open(data, "r")
    for host in hl_fh:
        host_url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts/{}".format(host.rstrip("\n"))
        host_data = url_response(host_url)
        json_data = {'RackNumber': host_data['hostRackNumber'], 'Role': host_data['roleName'],
                     'Bundle': host_data['patchCurrentRelease'], 'Majorset': host_data['hostMajorSet'],
                     'Minorset': host_data['hostMinorSet'], 'OS_Version': host_data['patchOs'],
                     'Cluster_Name': host_data['clusterName'], 'Cluster_Status': host_data['clusterStatus'],
                     'Host_Status': host_data['hostStatus'], 'SuperPod': host_data['superpodName']}
        host_json = json.dumps(json_data)
        master_json[host_data['hostName']] = json.loads(host_json)
    logging.debug(master_json)
    return master_json

def find_concurrency(hostpercent, master_json):
    """
    This function calculates the host count per block #W-3758985
    :param inputdict: takes inputdict
    :return: maxgroupsize
    """
    pod = inputdict['clusters']
    dc = inputdict['datacenter']
    role = inputdict['roles']
    inputdict['maxgroupsize'] = round(float(hostpercent) * (len(master_json)) / 100)


def os_chk(data):
    for host in data.keys():
        if options.os_version != data[host]['OS_Version']:
            logging.debug("{}: OS_Version is {}, excluded".format(host,
                                                                  data[host]['OS_Version']))
            del data[host]
    return data


def bundle_cleanup(data, targetbundle):
    '''
    This function checks excludes the hosts that are already patched
    :param data:
    :return:
    '''
    current_bundle = {}
    url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/patch-bundles"
    bundles = url_response(url)
    if targetbundle.lower() == "current":
        for bundle in bundles:
            if bundle['current'] == True:
                current_bundle[str(int(float(bundle['osMajor'])))] = bundle['release']
        c7_ver = current_bundle['7']
        c6_ver = current_bundle['6']
    elif targetbundle.lower() == "canary":
        # get canary bundle info and assign to
        # c7_ver and c6_ver respectively
        for bundle in bundles:
            if bundle['canary'] == True:
                current_bundle[str(int(float(bundle['osMajor'])))] = bundle['release']
        c7_ver = current_bundle['7']
        c6_ver = current_bundle['6']
    else:
        # if any other specific bundle values are passed
        c7_ver = c6_ver = targetbundle
    if "migration" not in templateid.lower() :
        for host in data.keys():
            if data[host]['OS_Version'] == "7" and data[host]['Bundle'] >= c7_ver:
                logging.debug("{}: patchCurrentRelease is {}, excluded".format(host, data[host]['Bundle']))
               # del data[host]
            elif data[host]['OS_Version'] == "6" and data[host]['Bundle'] >= c6_ver:
                logging.debug("{}: patchCurrentRelease is {}, excluded".format(host, data[host]['Bundle']))
               # del data[host]
    return data, c6_ver, c7_ver


def ice_mist_check(hostname):
    ice_chk = re.compile(r'ice|mist|^stm')

    if options.ice:
        if ice_chk.match(hostname):
            logging.debug("Host matches skipping...")
            return 1
        else:
            return 0


def validate_templates(tempalteid):
    '''
    This functions validates that all templates are in place.
    :return:
    '''
    # check if templates exist
    ######
    template = "{}/templates/{}.template".format(os.getcwd(), templateid)
    template_1 = "{}/templates/{}.template.pre".format(os.getcwd(), templateid)
    template_2 = "{}/templates/{}.template.post".format(os.getcwd(), templateid)
    work_template = "{}/templates/{}.template".format(os.getcwd(), options.dowork)

    if not os.path.isfile(template) or not ("migration" in templateid or os.path.isfile(work_template)):
        logging.error("No such file or directory")
        sys.exit(1)

    pre_template = template_1 if os.path.isfile(template_1) else "{}/templates/generic.pre".format(os.getcwd())
    post_template = template_2 if os.path.isfile(template_2) else "{}/templates/generic.post".format(os.getcwd())

    logging.debug("Defined Templates")
    logging.debug(template)
    logging.debug(work_template)
    logging.debug(pre_template)
    logging.debug(post_template)

    return template, work_template, pre_template, post_template


def prep_template(work_template, template):
    '''
    This function does the prep work to the template by adding the comment line and block v_NUM.
    :return:
    '''
    with open(work_template, 'r') as do:
        dw = do.read()

    with open(template, 'r') as out:
        output = out.read()
        output = output.replace('v_INCLUDE', dw)

    """This code is to add unique comment to each line in implementation plan.
             e.g - release_runner.pl -forced_host $(cat ~/v_CASE_include) -force_update_bootstrap -c sudo_cmd -m "ls" -auto2 -threads
             -comment 'BLOCK 1'"""
    if 'v_COMMAND' not in output and 'mkdir -p ~/releaserunner/remote_transfer' not in output:
        o_list = output.splitlines(True)
        for i in range(len(o_list)):
            # Added to skip linebacker -  W-3779869
            #if not options.nolinebacker:
            #    regex_compile = re.compile('bigipcheck|remove_from_pool|add_to_pool', re.IGNORECASE)
            #    if regex_compile.search(o_list[i]):
            #        o_list[i] = o_list[i].strip() + ' -nolinebacker' + "\n"
            if o_list[i].startswith('release_runner.pl') and 'BLOCK' not in o_list[i]:
                cmd = o_list[i].strip() + ' -comment ' + "'BLOCK v_NUM'\n"
                o_list.remove(o_list[i])
                o_list.insert(i, cmd)
            elif o_list[i].startswith('Exec_with') and 'BLOCK' not in o_list[i]:
                cmd = "Exec_with_creds: " + o_list[i][
                    o_list[i].index(':') + 1:].strip() + " && echo 'BLOCK v_NUM'\n"
                o_list.remove(o_list[i])
                o_list.insert(i, cmd)
            elif o_list[i].startswith('Exec') and 'BLOCK' not in o_list[i]:
                cmd = "Exec: echo 'BLOCK v_NUM' && " + o_list[i][o_list[i].index(':') + 1:]
                o_list.remove(o_list[i])
                o_list.insert(i, cmd)
        output = "".join(o_list)

    return output

def replace_common_variables(output):
    '''
    This function is the used to replace the common variables between pre, post and template.
    :param output: The file where replacements are required.
    '''
    output = output.replace('v_CLUSTER', new_data['Details']['cluster'])
    output = output.replace('v_DATACENTER', new_data['Details']['dc'])
    output = output.replace('v_SUPERPOD', new_data['Details']['Superpod'])
    output = output.replace('v_ROLE', new_data['Details']['role'])
    if role == "ffx":
        output = output.replace('v_HO_OPSTAT', 'any')
        output = output.replace('v_CL_OPSTAT', 'any')
    output = output.replace('v_HO_OPSTAT', new_data['Details']['ho_status'])
    output = output.replace('v_CL_OPSTAT', new_data['Details']['cl_status'])
    if options.bundle in ["current", "canary"] and os_ce6 != os_ce7:
        output = output.replace('--bundle v_BUNDLE', "--osce6 {0} --osce7 {1}".format(os_ce6, os_ce7))
        output = output.replace('-a v_BUNDLE', "--osce6 {0} --osce7 {1}".format(os_ce6, os_ce7))
    elif os_ce6 == os_ce7:
        output = output.replace('v_BUNDLE', os_ce7)
    else:
        output = output.replace('v_BUNDLE', options.bundle)
    return output

def compile_template(hosts, template, work_template, file_num, nonactive=False):
    '''
    This function put the template together substitute variables with information it obtains from
    command line and Atlas/Blackswan.
    :return:
    '''
    outfile = os.getcwd() + "/output/{0}_{1}_plan_implementation.txt".format(file_num, case_unique_id)
    output = prep_template(work_template, template)

    if 'v_COMMAND' not in output and 'mkdir -p ~/releaserunner/remote_transfer' not in output:
        output = output.replace('v_HOSTS', '$(cat ~/v_CASE_include)')
        output_list = output.splitlines(True)
        insert_num = 0
        if nonactive:
            output_list.insert(insert_num, "- This block is of non-active hosts using {}\n".format(template.split('/')[-1]))
            insert_num += 1
        if role not in ("praccn","smszk") and "migration" not in template.lower():
           output_list.insert(insert_num, "\n- Verify if hosts are patched or not up\nExec_with_creds: /opt/cpt/bin/verify_hosts.py "
                    "-H v_HOSTS --bundle v_BUNDLE --case v_CASE  && echo 'BLOCK v_NUM'\n\n")
        elif "migration" in template.lower():
            output_list.insert(insert_num, "\n- Verify if hosts are migrated or not up\nExec_with_creds: /opt/cpt/bin/verify_hosts.py "
                                        "-H v_HOSTS --bundle v_BUNDLE --case v_CASE -M && echo 'BLOCK v_NUM'\n\n")
        output = "".join(output_list)

    ###Argus can be patched independently as part of https://salesforce.quip.com/TynRAf80fsnJ

    """
    if 'argus_writed_matrics' in template.lower():
        for host in hosts:
            if 'argustsdbw' in host:
                argusmetrics = host.replace('argustsdbw', 'argusmetrics')
                argustsdbw = host
                if 'v_HOSTM' in output or 'v_HOSTD' in output:
                    try:
                        output = output.replace('v_HOSTD', argustsdbw)
                        output = output.replace('v_HOSTM', argusmetrics)
                    except UnboundLocalError:
                        pass
        hosts.append(argusmetrics)
    """
    output = compile_vMNDS_(output)
    output = output.replace('v_HOSTS', ','.join(hosts))
    output = replace_common_variables(output)
    if "migration" in template.lower():
        if len(active_hosts) != 0:
            output = output.replace('v_HOST', active_hosts[0])
        else:
            logging.error("No active host present in the cluster to fetch APP version")
    else:
        output = output.replace('v_HOST', hosts[0])
    output = output.replace('v_NUM', str(file_num))
    # other host and v_OHOSTS are used to create a check against all but the host to be patched (i.e. lapp, rps)
    other_hosts = list(set(allhosts_for_vohosts) - set(hosts))
    output = output.replace('v_OHOSTS', ','.join(other_hosts))
    output = output.replace('v_ALLHOSTS', ','.join(allhosts_for_vohosts))
    if 'v_PRODUCT_RRCMD' in output:
        products ,ignore_processes = product_rrcmd(role)
        output = output.replace('v_PRODUCT_RRCMD', ','.join(products))
        #add ignore processes here if required

    f = open(outfile, 'w')
    f.write(output)
    f.close()
    for t in hosts:
        sum_file.write(t + "\n")


def compile_pre_template(template):
    '''
    This function configures the pre template.
    :param new_data:
    :param template:
    :return:
    '''
    with open(template, 'r') as out:
        output = out.read()
    if re.search(r"mnds|dnds", new_data['Details']['role'], re.IGNORECASE) and hbase_rnd_idb_flag:
        output = output.replace('/opt/cpt/bin/update_patching_status.py --start --cluster v_CLUSTER','/opt/cpt/bin/update_patching_status.py --start --cluster v_CLUSTER;echo "skip_the_failure"')
    output = output.replace('v_HOSTS', ','.join(allhosts))
    output = replace_common_variables(output)

    return output


def compile_post_template(template):
    '''
    This function configures the post template.
    :param new_data:
    :param template:
    :return:
    '''
    build_command = " ".join(sys.argv)
    build_command = build_command.replace("{", "'{")
    build_command = build_command.replace("}", "}'")

    with open(template, 'r') as out:
        output = out.read()
    if re.search(r"mnds|dnds", new_data['Details']['role'], re.IGNORECASE) and hbase_rnd_idb_flag:
        output = output.replace('/opt/cpt/bin/update_patching_status.py --cluster v_CLUSTER','/opt/cpt/bin/update_patching_status.py --cluster v_CLUSTER;echo "skip_the_failure"')
    output = output.replace('v_COMMAND', build_command)
    output = replace_common_variables(output)

    return output


def compile_vMNDS_(output):
    """
    :param template: template
    :return: output
    """
    global hbase_rnd_idb_flag
    # Load Hbase hbase-mnds template.
    hbaseDowork_ = "{}/templates/{}.template".format(os.getcwd(), "hbase-mnds")

    # Check for hbase-mnds template existence.
    if os.path.isfile(hbaseDowork_):
        with open(hbaseDowork_, 'r') as f:
            mndsData = f.readlines()

    # Load the template data into variable.
    v_MNDS = "".join(mndsData)
    def _replace_skip_steps(output):
        """Function to append the echo skip_the_failure step to ignore the failures if any
        https://gus.lightning.force.com/lightning/r/0D5B0000016a5nj/view
        """
        output = output.replace('~/current/bigdata-util/util/build/ant cluster stopLocalNode',
                                '~/current/bigdata-util/util/build/ant cluster stopLocalNode;echo "skip_the_failure"')
        output = output.replace('~/current/bigdata-kerberos/kerberos/build/ant -- -w krb stopLocal',
                                '~/current/bigdata-kerberos/kerberos/build/ant -- -w krb stopLocal;echo "skip_the_failure"')
        output = output.replace('~/current/bigdata-kerberos/kerberos/build/ant -- keytab-service -s stop',
                                '~/current/bigdata-kerberos/kerberos/build/ant -- keytab-service -s stop;echo "skip_the_failure"')
        output = output.replace('~/current/bigdata-kerberos/kerberos/build/ant -- -w krb startLocal',
                                '~/current/bigdata-kerberos/kerberos/build/ant -- -w krb startLocal;echo "skip_the_failure"')
        output = output.replace('~/current/bigdata-util/util/build/ant -- cluster startLocalNode',
                                '~/current/bigdata-util/util/build/ant -- cluster startLocalNode;echo "skip_the_failure"')
        return output

    # Replace the v_MNDS variable in Hbase Mnds template.
    try:
        if re.search(r"mnds", new_data['Details']['role'], re.IGNORECASE) and hbase_rnd_idb_flag:
            logging.debug(v_MNDS)
            output = output.replace('v_MNDS', v_MNDS)
            output = output.replace('/home/sfdc/bigdops/gatekeeper/gatekeeper.py',
                                    '/home/sfdc/bigdops/gatekeeper/gatekeeper.py;echo "skip_the_failure"')
            output = _replace_skip_steps(output)
        elif re.search(r"mnds", new_data['Details']['role'], re.IGNORECASE):
            logging.debug(v_MNDS)
            output = output.replace('v_MNDS', v_MNDS)
        elif re.search(r"dnds", new_data['Details']['role'], re.IGNORECASE) and hbase_rnd_idb_flag:
            output = output.replace('v_MNDS', "- SKIPPING MNDS CHECK.")
            # r&d flag marked in idb, modify app start/stop
            output = _replace_skip_steps(output)
        else:
            output = output.replace('v_MNDS', "- SKIPPING MNDS CHECK.")
    except:
        pass

    # Return the plan_implimentation with changed v_MNDS.
    return output
    #TODO: move this newly added logic to outside of compile_v_MNDS function and make it to execute only once for a cluster (case?).


def create_masterplan(consolidated_file, pre_template, post_template):
    '''
    This function basically takes all the plans in the output directory and consolidates
    them into one plan.
    :return:
    '''
    read_files = glob.glob(os.getcwd() + "/output/*" + case_unique_id + "_plan_implementation.txt")
    read_files.sort(key=sort_key)
    logging.debug(read_files)
    try:
        logging.debug("Removing Old file {}".format(consolidated_file))
        os.remove(consolidated_file)
    except OSError:
        pass
    final_file = open(consolidated_file, 'a')
    with open(pre_template, "r") as pre:
        pre = compile_pre_template(pre_template)
        final_file.write('BEGIN_GROUP: PRE\n' + pre + '\nEND_GROUP: PRE\n\n')

    for f in read_files:
        if f != consolidated_file:
            with open(f, "r") as infile:
                # print('Writing out: ' + f + ' to ' + consolidated_file)
                final_file.write(infile.read() + '\n\n')

    post_file = compile_post_template(post_template)
    post_list = post_file.splitlines(True)
    case_post = "\n- Auto close case \nExec_with_creds: /opt/cpt/gus_case_mngr.py -c v_CASE --close -y\n\n"
    post_list.append( case_post)
    post = "".join(post_list)
    final_file.write('BEGIN_GROUP: POST\n' + post + '\nEND_GROUP: POST\n\n')
    cleanup()


def cleanup():
    '''
    This function is a cleanup routine for the output directory.
    :return:
    '''
    cleanup = glob.glob(os.getcwd() + "/output/*" + case_unique_id + "_plan_implementation.txt")
    logging.debug("Cleaning up output directory")
    for junk in cleanup:
        if junk != consolidated_file:
            os.remove(junk)


def product_rrcmd(role_name) :
    '''
    This function is used mainly in Reimage/Migration to capture the deployed products on a particular role.
    :return:
    '''


    products = {
        'chatterbox': ['sshare', 'prsn'],
        'chatternow': ['chan', 'dstore', 'msg', 'prsn'],
        'mandm-hub': ['mgmt_hub'],
        'caas': ['app'],
        'lightcycle-snapshot': ['app', 'cbatch', 'dapp'],
        'mandm-agent': ['app', 'cbatch', 'dapp'],
        'mandm-kafka': ['ajna_broker'],
        'mandm-zookeeper': ['ajna_zk'],
        'ajna-topic-deployer': ['ajna_zk'],
        'ajna-topics-api': ['ajna_zk'],
        'ajna-rest-endpoint': ['funnel'],
        'pbspectrum': ['pbsmatch'],
        'mq-broker': ['mq'],
        'acs': ['acs'],
        'searchserver': ['search'],
        'sfdc-base': ['ffx', 'cbatch', 'app', 'dapp'],
        'insights-redis': ['insights_redis', 'insights_iworker'],
        'insights-edgeservices': ['insights_redis', 'insights_iworker'],
        'waveagent': ['insights_redis', 'insights_iworker'],
        'wave-connector-agent': ['insights_redis', 'insights_iworker'],
        'wave-cassandra': ['insights_redis', 'insights_iworker']
    }
    ignored_process_names ={'redis-server': ['sfdc-base'],'memcached': ['sfdc-base']}
    product_rrcmd=[]
    ignore_process=[]
    for key in products.keys():
        if role_name in products[key]:
            product_rrcmd.append(key)
            for pkey in ignored_process_names :
                if key in ignored_process_names[pkey]:
                    ignore_process.append(pkey)
    return (product_rrcmd,ignore_process)


def group_worker(templateid, gsize):
    '''
    "This function is responsible for doing the work associated with the gsize variable.
    it ensures the number of host done in parallel are translated correctly into the v_HOSTS
    variable.
    :param templateid:
    :param new_data:
    :param grouping:
    :param gsize:
    :return:
    '''
    def _sub_groups_worker(data, file_num, host_group, template, work_template, nonactive=False):

        total_host = 0
        for key,value in data['Hostnames'].items():
            total_host = total_host + len(value)

        def _compile_template(hosts, file_num):
            logging.debug(hosts)
            logging.debug("File_Num: {}".format(file_num))
            non_active = (True if nonactive else False)
            compile_template(hosts, template, work_template, file_num, non_active)
            file_num = file_num + 1
            host_group = []
            return host_group, file_num
        for key in sorted(data['Hostnames'].keys()):
            for host in data['Hostnames'][key]:
                host_group.append(host)
                if len(host_group) == gsize:
                    host_group, file_num =_compile_template(host_group, file_num)
                elif host == data['Hostnames'][key][-1]:
#### The following section is to manage dynamic grouping while writing plan[W-6755335]. Currently being hardcoded to 10%
                    if 'ajna_broker' in role:
                        group_div = int(10 * total_host / 100)
                        if group_div == 0:
                            group_div = 1
                        elif group_div > 10:
                            group_div = 10
                        ho_lst = [host_group[j: j + group_div] for j in range(0, len(host_group), group_div)]
                        for ajna_hosts in ho_lst:
                            host_group, file_num = _compile_template(ajna_hosts, file_num)
                    else:
                        host_group, file_num = _compile_template(host_group, file_num)
        return file_num
    host_group = []
    file_num = 1
    template, work_template, pre_template, post_template = validate_templates(templateid)
    if new_data != None:
        file_num = _sub_groups_worker(new_data, file_num, host_group, template, work_template)
    if new_data_nonactive and nonactive_straight:
        host_group = []
        template = "{}/templates/{}.template".format(os.getcwd(), "straight-patch-Goc++")
        file_num = _sub_groups_worker(new_data_nonactive, file_num, host_group, template, work_template, nonactive=True)
    elif new_data_nonactive:
        host_group = []
        _ = _sub_groups_worker(new_data_nonactive, file_num, host_group, template, work_template, nonactive=True)

    sum_file.close()
    create_masterplan(consolidated_file, pre_template, post_template)


def main_worker(templateid, gsize):
    '''
    This function works with the byrack data. It just prints the contents of the
    value from the new_data dictionary to populate the v_HOSTS variable. Probably needs
    to be renamed.
    :param templateid:
    :param new_data:
    :param file_num:
    :return:
    '''
    def _sub_main_worker(data, file_num, total_groups, host_count, byrack_group, nonactive=False):

        def _compile_template(hosts, file_num, total_groups, host_count, byrack_group):
            non_active = (True if nonactive else False)
            compile_template(hosts, template, work_template, file_num, non_active)
            file_num = file_num + 1
            total_groups = total_groups + 1
            host_count = host_count + len(byrack_group)
            byrack_group = []
            return file_num, total_groups, host_count, byrack_group
        for pri in data['Grouping'].iterkeys():
            for key, value in data['Grouping'][pri].iteritems():
                if gsize == 0:
                    logging.debug("{} {}".format(key, value))
                    file_num, total_groups, host_count, byrack_group = _compile_template(value, file_num, total_groups, host_count, byrack_group)
                else:
                    for host in value:
                        byrack_group.append(host)
                        if len(byrack_group) == gsize:
                            logging.debug(byrack_group)
                            file_num, total_groups, host_count, byrack_group = _compile_template(byrack_group, file_num, total_groups, host_count, byrack_group)
                        elif host == value[-1]:
                            logging.debug(byrack_group)
                            file_num, total_groups, host_count, byrack_group = _compile_template(byrack_group, file_num, total_groups, host_count, byrack_group)
        return total_groups, host_count , file_num
    file_num = 1
    total_groups = 0
    host_count = 0
    byrack_group = []
    template, work_template, pre_template, post_template = validate_templates(templateid)
    if new_data:
        total_groups, host_count, file_num = _sub_main_worker(new_data, file_num, total_groups, host_count, byrack_group)
    if new_data_nonactive and nonactive_straight:
        byrack_group = []
        template = "{}/templates/{}.template".format(os.getcwd(), "straight-patch-Goc++")
        total_groups, host_count, file_num = _sub_main_worker(new_data_nonactive, file_num, total_groups, host_count, byrack_group, nonactive=True)
    elif new_data_nonactive:
        byrack_group = []
        total_groups, host_count, _ =_sub_main_worker(new_data_nonactive, file_num, total_groups, host_count, byrack_group, nonactive=True)
    logging.debug("Total # of groups: {}".format(total_groups))
    logging.debug("Total # of servers to be patched: {}".format(host_count))
    sum_file.close()
    create_masterplan(consolidated_file, pre_template, post_template)

# check for r&d flag in idb to modify app start/stop accordingly
def hbase_rnd_idb_check(datacenter,cluster_name) :
    global hbase_rnd_idb_flag
    idb_dev_check_url = "clusterconfigs?cluster.name={0}&key=bigdata_patch_custom_scripts&fields=key,value".format(cluster_name)
    idb = Idbhost(datacenter)
    idbout, _ = idb._get_request(idb_dev_check_url, datacenter)
    if (len(idbout["data"]) > 0) and (idbout["data"][0]["key"] == "bigdata_patch_custom_scripts") and (idbout["data"][0]["value"] == "true"):
        hbase_rnd_idb_flag = True
# check for zone & value for sayonara cluster for mnds role and datacenter xrd WI:- W-7519329
def sayonara_zone_idb_check(master_json, datacenter):
    def _get_zoneinfo_idb(host):
        idb_zone_check_url = "hosts?name={0}&fields=name,hostConfigs.key,hostConfigs.value".format(
            host)
        idb = Idbhost(datacenter)
        idbout, _ = idb._get_request(idb_zone_check_url, datacenter)
        return idbout
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        idb_result = executor.map(_get_zoneinfo_idb, master_json)
        idb_output = [each for each in idb_result]
        for each in (idb_output[i]["data"] for i in range(len(master_json))):
            hostname = each[0]["name"]
            zone_value_found = False
            for hostconfig in each[0]["hostConfigs"]:
                if hostconfig["key"] == "zone":
                    for host, details in master_json.items():
                        if host == hostname:
                            details["Zone"] = hostconfig["value"]
                            master_json[host] = details
                            zone_value_found = True
            if not zone_value_found:
                print("This host {0} is configured to any zone so skipping...".format(hostname))
                del master_json[hostname]
    return master_json

def hostlist_validate(master_json):
    """
    """
    role_diff = []
    cluster_diff = []
    pod_diff = []
    for host in master_json:
        if master_json[host]['Role'] not in role_diff:
            role_diff.append(master_json[host]['Role'])
        elif master_json[host]['Cluster_Name'] not in cluster_diff:
            cluster_diff.append(master_json[host]['Cluster_Name'])
        elif master_json[host]['SuperPod'] not in pod_diff:
            pod_diff.append(master_json[host]['SuperPod'])
    print "\nDifferences Report"
    print "============================="
    print "\nRole Information = {}".format(role_diff)
    print "Cluster Information = {}".format(cluster_diff)
    print "SuperPod Information = {}".format(pod_diff)
    print "Template Used = {}".format(options.templateid)
    if options.role not in role_diff:
        print "\nDifferences"
        print "Defined role \"{}\" not in hostlist".format(options.role)
    print "\nPlease confirm the above differences before continuing"
    value = raw_input("Do you wish to continue creating the plan? (Y/N)")
    if value == "Y" or value == "y":
        print "Continuing....."
    else:
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build_Plan")
    group1 = parser.add_argument_group('Standard', 'Command Line Options')
    group2 = parser.add_argument_group('Advanced', 'Additonal Parameters')
    group1.add_argument("-r", "--role", dest="role", help="Device RoleName")
    group1.add_argument("-d", "--datacenter", dest="dc", help="Datacenter")
    group1.add_argument("-p", "--pod", dest="pod", help="Superpod")
    group1.add_argument("-c", "--cluster", dest="cluster", help="Cluster")
    group1.add_argument("-t", "--template", dest="templateid", help="Template")
    group1.add_argument("-g", "--grouping", dest="grouping", help="Host Grouping (majorset|minorset|byrack)")
    group1.add_argument("--maxgroupsize", dest="maxgroupsize", help="# of servers in parallel")
    group1.add_argument("--dr", dest="dr", action="store_true", default=False, help="DR Host only")
    group1.add_argument("--bundle", dest="bundle", default="current", help="Patchset version")
    group1.add_argument("--gsize", dest="gsize", default=1, help="Group Size value")
    group1.add_argument("--dowork", dest="dowork", help="command to supply for dowork functionality")
    group1.add_argument("-G", "--idbgen", dest="idbgen", help='Create json string for input (i.e \'{"dr": "FALSE", "datacenter": "prd", "roles": "sdb", "templateid": "sdb", "grouping": "majorset", "maxgroupsize": 1}\')')
    group1.add_argument("-o", "--os", dest="os_version", help="Filter servers by OS Version")
    group2.add_argument("--taggroups", dest="taggroups", default=0, help="number of sub-plans per group tag")
    group2.add_argument("--nolinebacker", dest="nolinebacker", action="store_true", default=False, help="Don't use linebacker")
    group2.add_argument("--hostpercent", dest="hostpercent", help="percentange of hosts in parallel")
    group2.add_argument("--no_ice", dest="ice", action="store_true", default=False, help="Include ICE host in query")
    group2.add_argument("--skip_bundle", dest="skip_bundle", help="command to skip bundle")
    group2.add_argument("-l", "--hostlist", dest="hostlist", help="File containing list of servers")
    group2.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose Logging")
    group2.add_argument("--straight", dest="straight", action="store_true", default=False, help="Flag for generation straight patch cases  for non active hosts")
    options = parser.parse_args()

    ###############################################################################
    #                Constants
    ###############################################################################
    bundle = options.bundle
    dowork = options.dowork
    cwd = os.getcwd()
    if not os.path.isdir(cwd + "/output"):
        os.mkdir(cwd + "/output")
    if options.idbgen:
        op_dict = json.loads(options.idbgen)
        if not op_dict["dr"].lower() == "true":
            site_flag = "PROD"
        else:
            site_flag = "DR"
        case_unique_id = "_".join([op_dict["roles"], op_dict["datacenter"], op_dict["superpod"], op_dict["clusters"], site_flag])
        consolidated_file = cwd + "/output/{0}_plan_implementation.txt".format(case_unique_id)
        summary = cwd + "/output/{0}_summarylist.txt".format(case_unique_id)
        if os.path.isfile(summary):
            os.remove(summary)
        sum_file = open(summary, 'a')
    ###############################################################################

    if options.verbose and options.hostlist:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Bundle: {}".format(bundle))
        logging.debug("Dowork: {}".format(dowork))
    elif options.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Bundle: {}".format(bundle))
        logging.debug("Dowork: {}".format(dowork))
        logging.debug("Current Working Directory {}".format(cwd))
        logging.debug("Ending file {}".format(consolidated_file))
        logging.debug("Summary File {}".format(summary))
        logging.debug("Linebacker Option: {}".format(options.nolinebacker))
    else:
        logging.basicConfig(level=logging.ERROR)


    if options.idbgen:
        inputdict = json.loads(options.idbgen)
        logging.debug(inputdict)
        role = inputdict['roles']
        dc = inputdict['datacenter']
        grouping = inputdict['grouping']
        templateid = inputdict['templateid']
        dr = inputdict['dr']

        # options parameters
        try:
            pod = inputdict['superpod']
        except KeyError:
            pod = "NA"

        try:
            hostfilter = inputdict['hostfilter']
        except KeyError:
            hostfilter = None
        try:
            failoverstatus = inputdict['regexfilter']
            failoverstatus = failoverstatus.split("=")[1]
        except KeyError:
            failoverstatus = None

        try:
            cluster = inputdict['clusters']
        except KeyError:
            cluster = "NA"

        # Error checking for variables.
        try:
            cl_status = inputdict['cl_opstat']
        except KeyError:
            cl_status = "ACTIVE"
        try:
            ho_status = inputdict['ho_opstat']
        except KeyError:
            ho_status = "ACTIVE"
        hbase_rnd_idb_flag = False
        if dc.lower() in ['prd', 'crd'] and role.lower() in ['dnds','mnds']:
            hbase_rnd_idb_check(dc, cluster)
        try:
            nonactive_straight = inputdict['nonactive_straight']
        except KeyError:
            nonactive_straight = None

    elif options.hostlist:
        # Check for require parameters for hostlist
        if not options.role or not options.templateid or not options.grouping or not options.dowork or\
                not options.bundle or not options.dc:
            print "Missing required arguments (Role, Template, Grouping, Dowork, Bundle, Datacenter)"
            sys.exit(1)
        master_json = get_hostlist_data(options.hostlist)
        hostlist_validate(master_json)
        case_unique_id = options.templateid
        role = options.role
        dc = options.dc
        grouping = options.grouping
        templateid = options.templateid
        dr = "False"
        consolidated_file = cwd + "/output/{0}_plan_implementation.txt".format(case_unique_id)
        summary = cwd + "/output/{0}_summarylist.txt".format(case_unique_id)
        if os.path.isfile(summary):
            os.remove(summary)
        sum_file = open(summary, 'a')
        grp = Groups("active", "active", "SP4", role, "ia2", "na142", options.gsize, grouping, templateid, options.dowork)
        if options.grouping == "majorset":
            new_data, allhosts = grp.majorset(master_json)
            logging.debug("By Majorset: {}".format(new_data))
            group_worker(options.templateid, options.gsize)
            sys.exit(0)
        elif options.grouping == "minorset":
            new_data, allhosts = grp.minorset(master_json)
            logging.debug("By Minorset: {}".format(new_data))
            group_worker(options.templateid, options.gsize)
            sys.exit(0)
        elif options.grouping == "byrack":
            new_data, allhosts = grp.rackorder(master_json)
            logging.debug("By Rack Data: {}".format(new_data))
            main_worker(options.templateid, options.gsize)
            sys.exit(0)
        elif options.grouping == "all":
            new_data, allhosts = grp.all(master_json)
            logging.debug("By All: {}".format(new_data))
            group_worker(options.templateid, options.gsize)
            sys.exit(0)
        elif options.grouping == "zone":
            new_data, allhosts = grp.zone(master_json)
            logging.debug("By Zone: {}".format(new_data))
            group_worker(options.templateid, options.gsize)
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(1)

    # If POD,CLuster info is not passed to this script, Below logic retrieves the info from Blackswan/Atlas
    single_cluster = False
    if pod == "NA" and cluster == "NA":
        cluster = []
        pod_dict = {}
        url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?role={}&dc={}".format(role, dc)
        data = url_response(url)
        for host in data:
            pod = host['superpodName']
            cluster = host['clusterName']
            if pod not in pod_dict:
                pod_dict[pod] = []
            if cluster not in pod_dict[pod]:
                pod_dict[pod].append(cluster)

    elif pod != "NA" and cluster == "NA":
        url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?role={}&dc={}&sp={}".format(role, dc, pod)
        data = url_response(url)
        pod_dict = {pod: []}
        for host in data:
            cluster = host['clusterName']
            if cluster not in pod_dict[pod]:
                pod_dict[pod].append(cluster)

    elif pod == "NA" and cluster != "NA":
        url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/hosts?role={}&dc={}&cluster={}".format(role, dc, cluster)
        data = url_response(url)
        single_cluster = True
        pod = data[0]['superpodName']
        pod_dict = {pod: cluster}

    else:
        pod_dict = {pod: cluster}
        single_cluster = True

    for pod, clusters in pod_dict.items():
        inputdict['superpod'] = pod
        total_cluster_list = []
        if not single_cluster:
            clusters = ",".join(clusters)
            total_cluster_list.append(clusters)
        inputdict['clusters'] = clusters
        CreateBlackswanJson(inputdict, options.bundle, case_unique_id)
    if total_cluster_list:
        cluster = ",".join(total_cluster_list)

    cleanup()
    master_json, nonactive_json, allhosts_for_vohosts, os_ce6, os_ce7 = get_data(cluster, role, dc)
    if options.straight:
        master_json = {}
        if not master_json and not nonactive_json:
            logging.error("No servers match any filters.")
            sys.exit(1)
    if "migration" in templateid:
        nonactive_json = {}
        if not master_json and not nonactive_json:
            logging.error("No servers match any filters.")
            sys.exit(1)
    if "sayonara1a" == cluster.lower() and dc.lower() == "xrd" and role.lower() == "mnds":
        master_json = sayonara_zone_idb_check(master_json, dc)
        nonactive_json = sayonara_zone_idb_check(nonactive_json, dc)
    if options.hostpercent:
        find_concurrency(options.hostpercent, master_json)
    try:
        gsize = inputdict['maxgroupsize']
    except KeyError:
        if grouping == "byrack":
            gsize = 0
        else:
            gsize = 1
    grp = Groups(cl_status, ho_status, pod, role, dc, cluster, gsize, grouping, templateid, dowork)
    def _for_grouping_with_nonactive(obj, grouping):
        new_data_nonactive, allhosts_nonactive, new_data, allhosts = {}, {}, {}, {}
        if nonactive_json:
            nonactive_hosts, allhosts_nonactive = obj(nonactive_json)
            new_data_nonactive = nonactive_hosts.copy()
            logging.debug("By {0} Non Active:- {1}".format(str(grouping).capitalize(), new_data_nonactive))
        new_data, allhosts = obj(master_json)
        logging.debug("By {0} Active:- {1}".format(str(grouping).capitalize(), new_data))
        return new_data_nonactive, new_data, allhosts, allhosts_nonactive
    groupingDict = {"majorset": grp.majorset, "minorset": grp.minorset, "byrack": grp.rackorder, "all": grp.all, "zone": grp.zone}
    if grouping in ["majorset", "minorset", "byrack", "all", "zone"]:
        groupBy = groupingDict[grouping]
        new_data_nonactive, new_data, allhosts, allhosts_nonactive = _for_grouping_with_nonactive(groupBy, grouping)
        if grouping == "byrack":
            main_worker(templateid, gsize)
        else:
            group_worker(templateid, gsize)
    else:
        sys.exit(1)
