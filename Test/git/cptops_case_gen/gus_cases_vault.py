#!/usr/bin/env python
'''
    Script for creating cases in Gus
'''
from GUS.base import Auth
from GUS.base import Gus
from requests import patch
from optparse import OptionParser
import base64
import logging
import ConfigParser
import getpass
import re
import json
import sys
import os
from datetime import datetime, date, time, timedelta
from caseToblackswan import UploadDataToBlackswanV1, ApiKeyTest, GetHostField
from vault import Vault

try:
    import yaml
except:
    print('no yaml installed')

configdir = os.environ['HOME'] + "/.cptops/config"
config = ConfigParser.ConfigParser()
try:
    config.readfp(open(configdir + '/vaultcreds.config'))
except IOError:
    logging.error("No vaultcreds.config file found in %s", configdir)
    sys.exit(1)

os.environ['NO_PROXY'] = "secretservice.dmz.salesforce.com"


def saveSession(savedsession, session):
    with open(savedsession, 'w') as f:
        json.dump(session, f)


def getSession(savedsession):
    with open(savedsession, 'r') as f:
        session = json.load(f)
        return session


def validLogin(session):
    gusObj = Gus()
    object = 'Case'
    query = "select Id from " + object + " limit 1"
    logging.debug(query)
    try:
        case_query = gusObj.run_query(query, session)
        if case_query['totalSize'] == 1 and case_query['done'] == True:
            return True
        else:
            return False
    except Exception as e:
        print('%s' % e)
        return False


def getCreds():
    vault = Vault()
    client_id = vault.get_secret_by_key("client_id", "gus")
    client_secret = vault.get_secret_by_key("client_secret", "gus")
    username = vault.get_secret_by_key("apiaccess_username", "gus")
    passwd = vault.get_secret_by_key("apiaccess_password", "gus")
    return client_id, client_secret, username, passwd


def create_incident(cat, subcat, subject, desc, dc, status, priority):
    gusObj = Gus()
    recordType = 'Incident'
    incidentDict = {'Category': cat,
                    'SubCategory': subcat,
                    'Subject': subject,
                    'Description': desc,
                    'DC': dc,
                    'Status': status,
                    'Priority': priority,
                    }
    logging.debug(incidentDict)
    caseId = gusObj.create_incident_case(recordType, incidentDict, session)
    logging.debug(caseId)
    return caseId


def close_case(caseId, session):
    logging.info("Case didn't match the requirements, So closing it..")
    gusObj = Gus()
    closeDict = {"Status": "Closed - Not Executed"}
    if gusObj.close_case(closeDict, caseId, session):
        caseNum = getCaseNum(caseId, session)
        print("Successfully closed the case:- {0}".format(caseNum["CaseNumber"]))
    sys.exit(0)


def create_implementation_plan(implanDict, caseId, session):
    #import pdb;pdb.set_trace()
    logging.debug(implanDict)
    gusObj = Gus()
    impl_plan = gusObj.add_implementation_row(caseId, implanDict, session)
    if not impl_plan:
        close_case(caseId, session)
    logging.debug(impl_plan)
    return impl_plan["id"]


def get_ci_fullPath(dc, sp, pods, role, caseId, session, hosts):
    after_role_filter = []
    after_cluster_filter = []
    if len(role.split(",")) > 1:
        after_role_filter = GetHostField("roleName", hosts, apikey)
    if len(pods.split(",")) > 1:
        after_cluster_filter = GetHostField("clusterName", hosts, apikey)

    def _fullpath_for_role(role, pods):
        def _configure_cifullPath(sp_level=False, cluster_level=False, basic_level=False):
            Sfdc = "Salesforce.SFDC_Core"
            if sp_level:
                ci_fullPath = Sfdc+".{0}.{0}-{1}.{2}.{3}".format(dc.upper(), sp.upper(), pods.upper(), role.lower())
            elif cluster_level:
                ci_fullPath = Sfdc+".{0}.{1}.{2}".format(dc.upper(), pods.upper(), role.lower())
            elif basic_level:
                ci_fullPath = Sfdc+".{0}.{1}".format(dc.upper(), role.lower())
            return ci_fullPath

        gusObj = Gus()
        if role.lower() == "cms":
            ci_fullPath = _configure_cifullPath(basic_level=True)
        else:
            ci_fullPath = _configure_cifullPath(sp_level=True)
        cItem = gusObj.get_cItem_id(ci_fullPath, session)
        if not cItem["records"]:
            ci_fullPath = _configure_cifullPath(cluster_level=True)
            cItem = gusObj.get_cItem_id(ci_fullPath, session)
            if not cItem["records"]:
                ci_fullPath = _configure_cifullPath(basic_level=True)
                cItem = gusObj.get_cItem_id(ci_fullPath, session)
        if not cItem:
            close_case(caseId, session)
        return cItem["records"][0]["Id"]
    list_of_final_ids = []
    if not after_role_filter and not after_cluster_filter:
        full_path_id = _fullpath_for_role(role, pods)
        list_of_final_ids.append(full_path_id)
    elif after_role_filter and not after_cluster_filter:
        for role in after_role_filter:
            full_path_id = _fullpath_for_role(role, pods)
            list_of_final_ids.append(full_path_id)
    elif not after_role_filter and after_cluster_filter:
        for pods in after_cluster_filter:
            full_path_id = _fullpath_for_role(role, pods)
            list_of_final_ids.append(full_path_id)
    else:
        for role in after_role_filter:
            for pods in after_cluster_filter:
                full_path_id = _fullpath_for_role(role, pods)
                list_of_final_ids.append(full_path_id)
    return list_of_final_ids


def create_configuration_item(cItemDict, session):
    logging.debug(cItemDict)
    gusObj = Gus()
    c_Item = gusObj.add_configuration_item(cItemDict, session)
    if not c_Item:
        close_case(caseId, session)
    logging.debug(c_Item)


def createLogicalConnector(Dict, caseId, session):
    logging.debug(Dict)
    gusObj = Gus()
    logical_connector = gusObj.addLogicalConnectorRow(caseId, Dict, session)
    logging.debug(logical_connector)
    return logical_connector


def createLogicalHostsDict(Id, caseId):
    data = {
        'Logical_Host__c': Id,
        'Case_Record__c': caseId,
        'Exit_Code__c': '100',
        'Exit_Message__c': 'Not Started'
    }
    return data


def getLogicalConnectors(hosts, session):
    gusObj = Gus()
    object = 'Tech_Asset_Discovery__c'
    objecta = 'SM_Logical_Host__c'
    os_details = {}
    for h in hosts:
        logging.debug(h)
        if h != None:
            query = "Select Id, Host_Name__c from " + objecta + " \
            where Host_Name__c='" + h + "'"
            details = gusObj.run_query(query, session)
            if 'records' in details and details['totalSize'] != 0:
                os_details[h] = details['records'][0]['Id']
    return os_details


def get_change_details(filename, subject, hosts):
    d = {}
    with open(filename) as f:
        for line in f:
            if re.match(r'#', line):
                continue
            if re.match(r'Subject', line):
                line = line.replace('v_SUBJECT', subject)
            if re.match(r'Case-Owner', line):
                # line = line.replace('v_USERNAME', '005c0000001RDS7')
                line = line.replace('v_USERNAME', '005B0000000GyQ')
            line = line.rstrip()
            (key, val) = line.split(':', 1)
            if key == 'Description':
                msg = "\n\nHostlist:\n" + "\n".join(hosts)
                val += msg
            d[key] = val
    return d


def get_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def getYamlData(filename):
    with open(filename) as data_file:
        data = yaml.load(data_file)
    return data


def getCaseNum(caseId, session):
    gusObj = Gus()
    case_details = gusObj.get_case_details(caseId, session)
    return case_details


def gen_time():
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=5)
    return start_time.isoformat(), end_time.isoformat()


def create_implamentation_planner(data, caseId, session, role=None, insts=None, DCS=None, superpod=None, hosts=None, cItem_attachment=False):
    logging.debug(data)
    logging.debug(insts)
    if DCS != None:
        try:
            dcs_data = json.loads(DCS)
            DCS = dcs_data.keys()
        except Exception, e:
            if not isinstance(DCS, list):
                DCS = DCS.split(',')
    else:
        DCS = data['DCs'].split(',')
    print(DCS)
    details = data['Details']
    start_time, end_time = gen_time()
    case_details = getCaseNum(caseId, session)
    case_number = case_details['CaseNumber']
    for dc in DCS:
        print(dc)
        #import pdb;pdb.set_trace()
        if 'dcs_data' in locals():
            insts = dcs_data[dc]
        data['DCs'] = data['DCs'].replace('v_DATACENTER', dc.upper())
        data['Details']['Case__c'] = caseId
        data['Details']['Description__c'] = dc.upper() + " " + insts
        if re.search(r'-', dc):
            dc, sp = dc.split('-')
        data['Details']['SM_Data_Center__c'] = dc
        details['SM_Estimated_End_Time__c'] = end_time
        details['SM_Estimated_Start_Time__c'] = start_time
        data['Details']['SM_Instance_List__c'] = ('' if cItem_attachment else insts.upper())
        print(details)
        data['Details']['SM_Implementation_Steps__c'] = '\n'.join(data['Implementation_Steps'])
        if role != None:
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace(
                'v_DATACENTER', dc)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace(
                'v_Role', role)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace(
                'v_Case', case_number)
        logging.debug(data['Details'])
        if cItem_attachment:
            impl_plan_id = create_implementation_plan(data['Details'], caseId, session)
            ci_fullPath_ids = get_ci_fullPath(dc, superpod, insts, role, caseId, session, hosts)
            for fullpath_id in ci_fullPath_ids:
                cItemDict = {}
                cItemDict["Change_Implementation__c"] = impl_plan_id
                cItemDict["Configuration_Item__c"] = fullpath_id
                create_configuration_item(cItemDict, session)
        else:
            create_implementation_plan(data['Details'], caseId, session)


def createImplamentationPlannerYAML(data, caseId, session, role=None, DCS=None):
    logging.debug(data)
    if DCS != None:
        DCS = DCS.split(',')
    else:
        DCS = data['DCs'].split(',')
    print(DCS)
    details = data['Details']
    start_time, end_time = gen_time()
    case_details = getCaseNum(caseId, session)
    case_number = case_details['CaseNumber']
    for dc in DCS:
        print(dc)
        data['DCs'] = data['DCs'].replace('v_DATACENTER', dc.upper())
        data['Details']['Case__c'] = caseId
        data['Details']['Name'] = dc.upper()
        data['Details']['SM_Data_Center__c'] = dc
        details['SM_Estimated_End_Time__c'] = end_time
        details['SM_Estimated_Start_Time__c'] = start_time
        data['Details']['SM_Implementation_Steps__c'] = data['Implementation_Steps']
        if role != None:
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace(
                'v_DATACENTER', dc)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace(
                'v_Role', role)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace(
                'v_Case', case_number)
        logging.debug(data['Details'])
        create_implementation_plan(data['Details'], caseId, session)


def getYamlChangeDetails(filename, subject, hosts):
    hl_len = str(len(hosts))
    output = getYamlData(filename)
    msg = "\n\nHostlist:\n" + "\n".join(hosts)
    output['Description'] += msg
    output['Subject'] = subject + " [" + hl_len + "]"

    logging.debug(output['Description'])
    logging.debug(output['Subject'])
    logging.debug(output['Verification'])
    return output


def get_json_change_details(filename, subject, hosts, infratype, full_instances, role):
    with open(filename) as data_file:
        data = json.load(data_file)
    details = data['Details']
    if 'Verif' in data:
        logging.debug('\n'.join(data['Verif']))
        details['Verification'] = '\n'.join(data['Verif'])
        details['Subject'] = subject
    summary = "PRA unavailable in kingdoms where latest image deployed while rollback is actioned. PRA will remain available in all other kingdoms so no impact to access."
    details['Risk-Summary'] = summary
    try:  # added this try method to exit incase the hostlist file is empty
        if hosts != None:
            hl_len = str(len(hosts))
            if re.search("hdaas", hosts[0]):
                msg = "\n\nHostlist:\n" + "Check attached hostlist"
            else:
                msg = "\n\nHostlist:\n" + "\n".join(hosts)
            details['Description']
            details['Subject'] = " Hardening OS: Deploy current OS image " + subject + " [" + hl_len + "]"
    except IndexError:
        logging.error("Hostlist file(summarylist.txt) is empty, Please check ")
        sys.exit(0)
    details['Infrastructure-Type'] = "Supporting Infrastructure"
    details['TestingMethod'] = "Auto"
    details['AutoTestEnv'] = "PRD"
    details['Canary_plan'] = "A part of canary is done through CP framework and remaining through CPT tooling"
    details['Rollback_test'] = "Yes"
    if "migration" in options.subject.lower():
        details['Backout_plan'] = "Reimage the host to old version using Gingham /Racktastic"
        details['Rollback_process'] = "Whether the change is successful/failed , the host can be reimaged to older version when required"
        details['Patch-Desc'] = "Reimage the host to latest OS version"
    else:
        details['Backout_plan'] = " Rollback to previous image."
        details['Rollback_process'] = " Reverting the config in praccn to use the previous image will effectively keep PRA in it's current state "

    if full_instances != '':
        details['SM_Instance_List__c'] = full_instances
        logging.debug(details['SM_Instance_List__c'])
    logging.debug(details['Description'])
    logging.debug(details['Subject'])
    logging.debug(details['Verification'])
    return details


def check_exists(lst):
    pass


def get_verification(filename):
    with open(filename) as f:
        data = f.readlines()
    return data


def get_hosts(hostlist):
    hlist = []
    with open(hostlist) as f:
        for line in f:
            hlist.append(line.rstrip())
    return hlist


def create_change_case(tmplDict, session):
    gusObj = Gus()
    logging.debug(tmplDict)
    caseId = gusObj.create_change_case(tmplDict, session)
    logging.debug(caseId)
    return caseId


def attach_file(filename, name, cId, session):
    gusObj = Gus()

    fObj = open(filename)
    attachRes = gusObj.attach(fObj, name, cId, session)
    fObj.close()
    if not attachRes:
        close_case(cId, session)
    logging.debug("%s %s %s %s" % (filename, name, cId, session))
    logging.debug(attachRes)
    return attachRes


def submitCase(caseId, session):
    gusObj = Gus()
    results = gusObj.submitCase(caseId, session)
    logging.debug("%s %s %s" % (results, caseId, session))
    logging.debug(results)
    return results


def update_case(status, priority, cId, session):
    gusObj = Gus()
    logging.debug(status, priority, cId, session)
    caseDict = {'ParentId': cId,
                'Status': status,
                'Priority': priority}
    print(caseDict)
    changed_status = gusObj.update_case_details(cId, caseDict, session)
    return changed_status


def add_case_comment(comment, cId, session):
    gusObj = Gus()
    logging.debug(comment, cId, session)
    new_comment = gusObj.add_case_comment(comment, cId, session)
    logging.debug(new_comment)
    return new_comment


def combineInstanceValues(data):
    """
    Takes a dict containing a set of instances and combines them into a list
    Input : dict with dc and instance in comma separated list
    Output : comma separated str of instances
    """
    logging.debug(data)
    insts = []
    for d in data:
        insts.append(data[d])
    print(insts)
    output = ",".join(insts)
    return output


def checkEmptyFile(filename):
    try:
        if os.stat(filename).st_size == 0:
            print('%s is empty. Exiting.' % filename)
            sys.exit(1)
    except OSError:
        print('No file %s. Exiting.' % filename)
        sys.exit(1)


def update_implplan(filename, case_num):
    with open(filename, 'r') as my_file:
        file_data = my_file.read()
        file_data = file_data.replace('v_CASE', case_num['CaseNumber'])
    return file_data


def PreApproveCase(caseId, session):
    gusObj = Gus()
    Dict = {
        'Status': 'Approved, Scheduled',
    }
    details = gusObj.update_case_details(caseId, Dict, session)
    logging.debug(details)


# Added to create cases which are not standard Pre-Approved
def new_unassigned_case(caseId, session):
    gusObj = Gus()
    Dict = {
        "Change-Type": "Minor",
        'Status': 'New/Unassigned'
    }
    details = gusObj.update_case_details(caseId, Dict, session)
    logging.debug(details)


def updateCaseInformation_(caseId, session):
    """
    WI : #W-5497258 - User Story - CHANGE CASE TOOLING UPDATE
    New Changes made in GUS ref Doc: https://salesforce.quip.com/CrvDAUP4brXu
    :param caseId: caseID
    :param session: access_token and instance url dict
    :return: http response code


    """

    def caseDetailUpdate__(id, dict, ses):
        """
        Gus Object not updated to take these(new) changes, so creating a patch request apart of gus obj.
        :param id:
        :param dict:
        :param ses:
        :return:
        """
        token_, ins_ = str(ses['token']), ses['instance']
        api_ver_ = config.get('GUS', 'api_ver')
        url_ = str(ins_) + '/services/data/' + api_ver_ + '/sobjects/Case/' + id
        header_ = {
            'Authorization': "Bearer {0}".format(token_),
            'Content-Type': 'application/json',
            'Sforce-Auto-Assign': 'False'
        }

        try:
            res = patch(url_, data=json.dumps(dict), headers=header_)
            return res
        except Exception as e:
            print('Unable to update case: ', e)

    Dict = {
        # "SM_Business_Name__c": "a6nB00000008OQHIA2",
        "SM_Change_Category__c": "a8gB0000000027BIAQ"
    }
    details = caseDetailUpdate__(caseId, Dict, session)
    logging.debug(details)


def update_risk_summary(caseId, session, role):
    gusObj = Gus()
    str_fmt = "Services Affected: %s\n Risk if change is delayed: Will add delay to rollout CE7 for %s " % (role, role)
    print(str_fmt)
    Dict = {
        "Risk-Summary": str_fmt,
    }
    details = gusObj.update_case_details(caseId, Dict, session)
    logging.debug(details)


if __name__ == '__main__':

    usage = """

    This script provides a few different functions: 
    - create a new change case
    - attach a file to a case
    - update case comments
    - create a new incident record

    Creating a new change case:
    %prog -T change -f file with change details -i implan -s "subject to add" -k json for the change 

    Example:
    %prog -T change -f templates/oracle-patch.json -i output/plan_implementation.txt 
            -s "CHI Oracle : shared-nfs SP3 shared-nfs3{2|3}-{1|2}" 
            -k templates/shared-nfs-planer.json -l shared-nfs-sp3.txt
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseId", help="The caseId of the case to attach the file ")
    parser.add_option("-f", "--filename", dest="filename", help="The name of the file to attach")
    parser.add_option("-l", "--hostlist", dest="hostlist", help="The hostlist for the change")
    parser.add_option("-L", "--logicalHost", dest="logicalHost", action="store_true", help="Create Logical host connectors")
    parser.add_option("-V", "--vplan", dest="vplan", help="The verification plan for the change")
    parser.add_option("-i", "--iplan", dest="iplan", help="The implementation plan for the change")
    parser.add_option("-k", "--implanner", dest="implanner", help="The implementation planner json for the change")
    parser.add_option("-p", "--filepath", dest="filepath", help="The path to the file to attach")
    parser.add_option("-s", "--subject", dest="subject", help="The subject of the case")
    parser.add_option("-r", "--role", dest="role", help="The host role of the case")
    parser.add_option("-d", "--description", dest="desc", help="The description of the case")
    parser.add_option("-T", "--casetype", dest="casetype", help="The type of the case")
    parser.add_option("-S", "--status", dest="status", default="New", help="The status of the case")
    parser.add_option("-D", "--datacenter", dest="dc", help="The data center of the case")
    parser.add_option("-P", "--priority", dest="priority", default="Sev3", help="The priority of the case : Sev[1..4]")
    parser.add_option("-C", "--category", dest="category", help="The category of the case")
    parser.add_option("-b", "--subcategory", dest="subcategory", help="The subcategory of the case")
    parser.add_option("-A", "--submit", action="store_true", dest="submit", help="Submit the case for approval")
    parser.add_option("--inst", dest="inst", help="List of comma separated instances")
    parser.add_option("--sp", dest="superpod", help="Super Pod details")
    parser.add_option("--infra", dest="infra", help="Infrastructure type")
    parser.add_option("-n", "--new", action="store_true", dest="newcase",
                      help="""Create a new case. Required args : Category, SubCategory, Subject, Description, DC, Status and Prioriry.-n -C Systems -b SubCategory Hardware -s Subject 'DNS issue 3' -d 'Mail is foobar\'d, DSET Attached.' -D ASG -S New -P Sev3""")
    parser.add_option("-a", "--attach", dest="attach", action="store_true", help="Attach a file to a case")
    parser.add_option("-t", "--comment", dest="comment", help="text to add to a case comment")
    parser.add_option("-y", "--yaml", dest="yaml", action="store_true", help="patch details via yaml file")
    parser.add_option("-u", "--update", action="store_true", dest="update", help="Required if you want to update a case")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")  # will set to False later
    parser.add_option("--cstatus", dest="pre_appr", help="Change cases status to Approved")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # set username and details of case
    savedsession = config.get('SESSION', 'savedsession')
    # check for existing session
    session = ''
    valid_login = ''
    full_instances = ''
    if os.path.isfile(savedsession):
        session = getSession(savedsession)

        logging.debug("%s" % session)

    try:
        valid_login = validLogin(session)
        # some bug here!!
        logging.debug(valid_login)
    except Exception as e:
        print('error : %s' % e)

    if valid_login != True:
        try:
            client_id, client_secret, username, passwd = getCreds()
            logging.debug('%s, %s, %s' % (client_id, client_secret, username))
        except Exception as e:
            print('Problem getting username, client_id or client_secret: %s' % e)
            sys.exit()
        authObj = Auth(username, passwd, client_id, client_secret)
        # save latest session info
        try:
            session = authObj.login()
            print("%s" % session)
            saveSession(savedsession, session)
        except Exception as e:
            print('Failed to store session : %s' % e)
    if options.iplan:
        checkEmptyFile(options.iplan)

    infratype = "Supporting Infrastructure"
    if options.infra:
        infratype = options.infra

    if options.dc:
        # Code added to get the instance list from the cmd
        DCS = options.dc
        if DCS != None:
            try:
                dcs_data = json.loads(DCS)
                print('DC variable contains instance keys')
                full_instances = combineInstanceValues(dcs_data)
                logging.debug(full_instances)
            except Exception as e:
                if options.inst:
                    full_instances = options.inst
                print('DC variable does not contain instance keys : %s' % e)
    if options.casetype == 'change':
        insts = ''
        if options.inst:
            insts = options.inst
        if options.hostlist:
            hosts = get_hosts(options.hostlist)
        else:
            hosts = None

        # case_details = get_change_details(options.filename, options.subject, hosts)
        # logging.debug(case_details)
        if options.yaml:
            try:
                jsoncase = getYamlChangeDetails(options.filename, options.subject, hosts)
            except:
                print('problem with yaml loading')
        else:
            jsoncase = get_json_change_details(options.filename, options.subject, hosts, infratype, full_instances, options.role)
        logging.debug(jsoncase)

        # Checking for Atlas API KEY
       # apikey = ApiKeyTest()

        logging.debug(hosts)
        caseId = create_change_case(jsoncase, session)
        if options.inst == "HDAAS" and options.hostlist:
            print("Due to character limit in the description field, attaching hostlist file for Deepsea")
            hosts = options.hostlist
            attach_file(hosts, 'hostlist.txt', caseId, session)
        # create_implementation_plan(caseId, session)
        if options.yaml:
            planner_json = getYamlData(options.implanner)
        else:
            planner_json = get_json(options.implanner)
        if options.role:
            if options.inst:
                insts = options.inst
            create_implamentation_planner(planner_json, caseId, session, role=options.role, insts=insts,
                                          DCS=options.dc, superpod=options.superpod, hosts=hosts, cItem_attachment=True)
        else:
            if options.dc:
                if options.yaml:
                    createImplamentationPlannerYAML(planner_json, caseId, session, DCS=options.dc)
                else:
                    if options.inst:
                        insts = options.inst
                    create_implamentation_planner(planner_json, caseId, session, DCS=options.dc, insts=insts)
            else:
                create_implamentation_planner(planner_json, caseId, session)
        if options.vplan:
            vplan = options.vplan
            attach_file(vplan, 'verification_plan.txt', caseId, session)
        caseNum = getCaseNum(caseId, session)
        if options.iplan:
            iplan = options.iplan
            output = update_implplan(iplan, caseNum)
            with open(iplan, 'w') as f:
                f.write(output)
            attach_file(iplan, 'plan_implementation.txt', caseId, session)
        if options.submit:
            submitCase(caseId, session)
        logging.debug('The case number is %s' % caseNum['CaseNumber'])
        print(caseNum['CaseNumber'])

        if options.logicalHost:
            logical_hosts = getLogicalConnectors(hosts, session)
            for host in logical_hosts:
                dict = createLogicalHostsDict(logical_hosts[host], caseId)
                logging.debug(dict)
                print('Creating logical host connector for %s' % host)
                createLogicalConnector(dict, caseId, session)
        if options.pre_appr == "approved":
            PreApproveCase(caseId, session)
            updateCaseInformation_(caseId, session)
        elif options.pre_appr == "new":
            new_unassigned_case(caseId, session)
            updateCaseInformation_(caseId, session)

        # TODO - Hack to update RiskSummary for CE7 migrations.
        if "migration" in options.subject:
            update_risk_summary(caseId, session, options.role)

        # Push case Details to blackswan
        case_unique_id = options.iplan.split("/")[1].split("_plan")[0]
        #UploadDataToBlackswanV1(caseNum, case_unique_id, apikey)
        # END#

    elif options.attach:
        if options.filepath:
            file = options.filepath
        else:
            file = options.filename
        caseId = options.caseId
        name = options.filename
        attach_file(file, name, caseId, session)
        print("File %s successfully attached to case %s")
    elif options.newcase:
        logging.debug(options.category, options.subcategory, options.subject, options.desc, options.dc, options.status,
                      options.priority)
        caseId = create_incident(options.category, options.subcategory, options.subject, options.desc, options.dc,
                                 options.status, options.priority)
        logging.debug(caseId)

        print("Case subject %s caseId %s was successfully created" % (options.subject, caseId))
    elif options.update:
        cId = options.caseId
        if options.comment:
            comment = options.comment
            new_comment = add_case_comment(comment, cId, session)
        if options.status != 'New':
            print("updating %s %s %s" % (options.status, options.priority, cId))
            case_details = update_case(options.status, options.priority, cId, session)
            print("updated %s" % (case_details))
