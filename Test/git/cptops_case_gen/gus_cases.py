#!/usr/bin/env python
'''
   Script for creating cases in Gus authenticating via Kerberos
'''
from GUS.base import Auth
from GUS.base import Gus
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


try:
    import yaml
except:
    logging.debug('no yaml installed')

configdir = os.environ['HOME'] + "/.cptops/config"
config = ConfigParser.ConfigParser()
try:
    config.readfp(open(configdir + '/creds.config'))
except IOError:
    logging.error("No creds.config file found in %s", configdir)
    sys.exit(1)

def create_incident(cat, subcat, subject, desc, dc, status, priority):

    gusObj = Gus()
    recordType = 'Incident'
    incidentDict = { 'Category': cat,
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

def create_implementation_plan(implanDict, caseId, session):
    logging.debug(implanDict)
    gusObj = Gus()
    case = gusObj.add_implementation_row(caseId, implanDict, session)
    logging.debug(case)

def createLogicalConnector(Dict, caseId, session):
    logging.debug(Dict)
    gusObj = Gus()
    logical_connector = gusObj.addLogicalConnectorRow(caseId, Dict, session)
    logging.debug(logical_connector)
    return logical_connector

def createLogicalHostsDict(Id,caseId):
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
            if re.match(r'#',line):
                continue
            if re.match(r'Subject', line):
                line = line.replace('v_SUBJECT', subject)
            if re.match(r'Case-Owner', line):
                #line = line.replace('v_USERNAME', '005c0000001RDS7')
                line = line.replace('v_USERNAME', '005B0000000GyQ')
            line = line.rstrip()
            (key,val) = line.split(':', 1)
            if key == 'Description':
                msg = "\n\nHostlist:\n" + "\n".join(hosts)
                val+= msg
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

def getCaseNum(caseId,session):
    gusObj = Gus()
    case_details = gusObj.get_case_details(caseId,session)
    return case_details

def gen_time():
    now = datetime.now()
    start_time = now + timedelta(days = 1)
    end_time = start_time + timedelta(hours = 5)
    return start_time.isoformat(),end_time.isoformat()

def create_implamentation_planner(data, caseId, session,role=None,insts=None,DCS=None):
    logging.debug(data)
    logging.debug(insts)
    if DCS != None:
        try:
            dcs_data = json.loads(DCS)
            DCS = dcs_data.keys()
        except Exception, e:
            if not isinstance(DCS, list):
                print('here')
                DCS = DCS.split(',')
    else:
        DCS = data['DCs'].split(',')
    print(DCS)
    details = data['Details']
    start_time,end_time = gen_time()
    case_details = getCaseNum(caseId, session)
    case_number = case_details['CaseNumber']
    for dc in DCS:
        print(dc)
        if 'dcs_data' in locals():
            d = dcs_data[dc]
        data['DCs'] = data['DCs'].replace('v_DATACENTER', dc.upper())
        data['Details']['Case__c'] = caseId
        data['Details']['Description__c'] = dc.upper()
        data['Details']['SM_Data_Center__c'] = dc
        data['Details']['SM_Instance_List__c'] = data['Details']['SM_Instance_List__c'].replace('v_INSTANCES', insts.upper())
        #data['Details']['SM_Instance_List__c'] = insts.upper()
        details['SM_Estimated_End_Time__c'] = end_time
        details['SM_Estimated_Start_Time__c'] = start_time
        print(details)
        data['Details']['SM_Implementation_Steps__c'] = '\n'.join(data['Implementation_Steps'])
        if role != None:
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace('v_DATACENTER', dc)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace('v_Role', role)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace('v_Case', case_number)
        logging.debug(data['Details'])
        create_implementation_plan(data['Details'], caseId, session)

def createImplamentationPlannerYAML(data, caseId, session,role=None,DCS=None):
    logging.debug(data)
    if DCS != None:
        DCS = DCS.split(',')
    else:
        DCS = data['DCs'].split(',')
    print(DCS)
    details = data['Details']
    start_time,end_time = gen_time()
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
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace('v_DATACENTER', dc)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace('v_Role', role)
            data['Details']['SM_Implementation_Steps__c'] = data['Details']['SM_Implementation_Steps__c'].replace('v_Case', case_number)
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

def get_json_change_details(filename, subject, hosts, infratype):
    hl_len = str(len(hosts))
    msg = "\n\nHostlist:\n" + "\n".join(hosts)
    with open(filename) as data_file:
        data = json.load(data_file)
    details = data['Details']
    if 'Verif' in data:
        logging.debug('\n'.join(data['Verif']))
        details['Verification'] = '\n'.join(data['Verif'])
    details['Description'] += msg
    details['Subject'] = subject + " [" + hl_len + "]"
    details['Infrastructure-Type'] = infratype
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

def genChangeDetails(subject, case_data, desc_data, inst):
    if inst != None:
        subject = inst + " " + subject
        desc_data['Description'] = inst + " " + desc_data['Description']
    case_data['Subject'] = subject
    case_data['Description'] = desc_data['Description']
    if options.owner:
        case_data['Case-Owner'] = options.owner
    return case_data

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

    try:
        fObj = open(filename)
    except IOError:
        logging.error("No such file or directory")
        sys.exit(1)
    attachRes = gusObj.attach(fObj, name, cId, session)
    fObj.close()
    logging.debug("%s %s %s %s" % (filename, name, cId, session))
    logging.debug(attachRes)
    return attachRes

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

def submitCase(caseId, session):
    gusObj = Gus()
    results = gusObj.submitCase(caseId, session)
    logging.debug("%s %s %s" % (results, caseId, session))
    logging.debug(results)
    return results

def update_case(status, priority, cId, session):
    gusObj = Gus()
    logging.debug(status, priority, cId, session)
    caseDict = { 'ParentId': cId,
                            'Status': status,
                            'Priority': priority }
    print(caseDict)
    changed_status = gusObj.update_case_details(cId, caseDict, session)
    return changed_status

def add_case_comment(comment, cId, session):
    gusObj = Gus()
    logging.debug(comment, cId, session)
    new_comment = gusObj.add_case_comment(comment, cId, session)
    logging.debug(new_comment)
    return new_comment

def checkEmptyFile(filename):
    try:
        if os.stat(filename).st_size == 0:
            print('%s is empty. Exiting.' % filename)
            sys.exit(1)
    except OSError:
        print('No file %s. Exiting.' % filename)
        sys.exit(1)

def getCaseId(caseNum,session):
    gusObj = Gus()
    case_details = gusObj.get_case_details_caseNum(caseNum,session)
    if case_details:
        return case_details.rstrip()
    else:
        logging.error("Case %s not found.", caseNum)
        sys.exit(1)

def getExistingPlanId(caseId, session):
    gusObj = Gus()
    object = 'Attachment'
    query = "Select Id, Name,OwnerId,ParentId from " + object + " \
    where ParentId='" + caseId + "'"
    details = gusObj.run_query(query, session)
    logging.debug(details['records'])
    return details['records'][0]['Id']

def moveExistingPlan(name, Id, session):
    gusObj = Gus()
    details = gusObj.renameAttach(name, Id, session)
    logging.debug(details)
    return details

def PreApproveCase(caseId, session):
    gusObj = Gus()
    Dict = {
                'Status': 'Approved, Scheduled',
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
    parser.add_option("-c", "--case", dest="caseId",
                            help="The caseId of the case to attach the file ")
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
    parser.add_option("--infra", dest="infra", help="Infrastructure type")
    parser.add_option("--approved", action="store_true", dest="pre_appr", help="Change cases status to Approved")
    parser.add_option("-n", "--new", action="store_true", dest="newcase",
                                    help=
                                    """Create a new case. Required args :
                                    Category, SubCategory, Subject, Description, DC, Status and Prioriry.
                                    -n -C Systems -b SubCategory Hardware -s Subject 'DNS issue 3' -d 'Mail is foobar\'d, DSET Attached.' -D ASG -S New -P Sev3
                                    """)
    parser.add_option("-a", "--attach", dest="attach", action="store_true", help="Attach a file to a case")
    parser.add_option("-t", "--comment", dest="comment", help="text to add to a case comment")
    parser.add_option("-y", "--yaml", dest="yaml", action="store_true", help="patch details via yaml file")
    parser.add_option("-u", "--update", action="store_true", dest="update", help="Required if you want to update a case")
    parser.add_option("-o", "--owner", dest="owner", help="Sets the owner of the case")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # set username and details of case

    try:
        gpass = config.get('GUS', 'guspassword')
    except ConfigParser.NoOptionError,e:
        gpass = getpass.getpass("Please enter your GUS password: ")
    try:
        username = config.get('GUS', 'username')
        client_id = config.get('GUS', 'client_id')
        client_secret = config.get('GUS', 'client_secret')
    except:
        print('Problem getting username, client_id or client_secret')
        sys.exit()
    # instantiate auth object and generate session dict
    authObj = Auth(username,gpass,client_id,client_secret)
    session = authObj.login()
    if options.iplan:
        checkEmptyFile(options.iplan)

    infratype="Supporting Infrastructure"
    if options.infra:
        infratype = options.infra

    if options.casetype == 'storage':
        logging.debug('casetype of %s' % options.casetype)
        planner_data = ''
        case_data = ''
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
        #come back and refactor this
        if options.implanner:
            _,file_extension = os.path.splitext(options.implanner)
            if file_extension == ".yaml":
                planner_data = getYamlData(options.implanner)
            else:
                print("Case type storage uses yaml files")
                sys.exit()
        if options.filename:
            _,file_extension = os.path.splitext(options.filename)
            if file_extension == ".yaml":
                case_data = getYamlData(options.filename)
            else:
                print("Case type storage uses yaml files")
                sys.exit()
        if options.desc:
            _,file_extension = os.path.splitext(options.desc)
            if file_extension == ".yaml":
                desc_data = getYamlData(options.desc)
            else:
                print("Case type storage uses yaml files")
                sys.exit()
        if planner_data != '':
             print(planner_data)
        if case_data != '':
            print(case_data)
        if options.inst:
            inst = options.inst
        else:
            inst = None
        str = "/".join(dcs_data.keys())
        subject = options.subject + " " + str.upper()
        #subject = options.subject
        change_details = genChangeDetails(subject, case_data, desc_data, inst)
        #caseId='500B0000002HBcEIAW'
        logging.debug(change_details)
        try:
            caseId = create_change_case(change_details, session)
        except Exception as e:
            print("Failed to create case : %s" % e)
        planner_data_dict = {}
        try:
            for k,v in dcs_data.items():
                for s,t in planner_data.items():
                    header_str = k + " - " + v + " " + s
                    planner_data_dict[header_str] = t
        except Exception as e:
            print("Problem with dc data : %s" % e)
        print(planner_data_dict)
        for e in planner_data_dict:
            start_time,end_time = gen_time()
            impl_details = {}
            impl_details['Case__c'] = caseId
            impl_details['Description__c'] = e.upper()
            impl_details['SM_Data_Center__c'] = e.split('-')[0].upper()
            impl_details['SM_Estimated_End_Time__c'] = end_time
            impl_details['SM_Estimated_Start_Time__c'] = start_time
            impl_details['SM_Implementation_Steps__c'] = planner_data_dict[e]
            impl_details['SM_Infrastructure_Type__c'] = infratype
            print(impl_details)
            try:
                create_implementation_plan(impl_details, caseId, session)
                #createImplamentationPlannerYAML(planner_data_dict, caseId, session, DCS=options.dc)
            except Exception as e:
                print("Problem creating implementation plan section : %s" % (e))
        #createImplamentationPlannerYAML(planner_data_dict, caseId, session, DCS=options.dc)
        caseNum = getCaseNum(caseId, session)
        logging.debug('The case number is %s' % caseNum['CaseNumber'])

        if options.attach:
            files = options.attach.split(',')
            for f in files:
                logging.debug(f)
                try:
                    os.path.isfile(f)
                    print("Attaching file : %s" % f)
                    attachFile(f, caseId, session)
                except Exception as e:
                    print('The File %s does not exist : %s' % (f,e))
        print(caseNum['CaseNumber'])
    elif options.casetype == 'change':
        insts = ''
        hosts = get_hosts(options.hostlist)

        #case_details = get_change_details(options.filename, options.subject, hosts)
        #logging.debug(case_details)
        if options.yaml:
            try:
                jsoncase = getYamlChangeDetails(options.filename, options.subject, hosts)
            except:
                print('problem with yaml loading')
        else:
            jsoncase = get_json_change_details(options.filename, options.subject, hosts,infratype)
        logging.debug(jsoncase)

        logging.debug(hosts)
        caseId = create_change_case(jsoncase, session)
        #create_implementation_plan(caseId, session)
        if options.yaml:
            planner_json = getYamlData(options.implanner)
        else:
            planner_json = get_json(options.implanner)
        if options.role:
            if options.inst:
                insts = options.inst
            create_implamentation_planner(planner_json, caseId, session,options.role,insts)
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
        if options.iplan:
            iplan = options.iplan
            attach_file(iplan, 'plan_implementation.txt', caseId, session)
        if options.submit:
            submitCase(caseId, session)
        caseNum = getCaseNum(caseId, session)
        logging.debug('The case number is %s' % caseNum['CaseNumber'])
        print('The case number is %s' % caseNum['CaseNumber'])
        if options.logicalHost:
            logical_hosts = getLogicalConnectors(hosts, session)
            for host in logical_hosts:
                dict = createLogicalHostsDict(logical_hosts[host],caseId)
                logging.debug(dict)
                print('Creating logical host connector for %s' % host)
                createLogicalConnector(dict, caseId, session)
        if options.pre_appr:
            PreApproveCase(caseId, session)

    elif options.attach:
        if options.filepath:
            file = options.filepath
        else:
            file = options.filename
        if not options.caseId or not file:
            logging.debug("Case ID or File not specified.")
            sys.exit(1)
        caseId = options.caseId
        name = options.filename
        caseNum = getCaseId(caseId, session)
        attach_file(file, name, caseNum, session)
        print("File %s successfully attached to case %s" % (file, options.caseId))
    elif options.newcase:
        logging.debug(options.category,options.subcategory,options.subject,options.desc,options.dc,options.status,options.priority)
        caseId = create_incident(options.category, options.subcategory, options.subject, options.desc, options.dc, options.status, options.priority)
        logging.debug(caseId)
        print("Case subject %s caseId %s was successfully created" % (options.subject, caseId))
    elif options.update:
        cId = options.caseId
        if options.comment:
            comment = options.comment
            caseNum = getCaseId(cId, session)
            new_comment = add_case_comment(comment, caseNum, session)
        if options.status != 'New':
            print("updating %s %s %s" % (options.status, options.priority, cId))
            caseNum = getCaseId(cId, session)
            case_details = update_case(options.status, options.priority, caseNum, session)
            print("updated %s" % (case_details))
