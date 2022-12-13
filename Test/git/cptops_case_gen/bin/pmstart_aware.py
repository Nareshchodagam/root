#!/usr/bin/env python
'''
        Script for closing cases in Gus
'''
from base import Auth
from base import Gus
from common import Common 
import pprint
from optparse import OptionParser
import base64
import logging
import ConfigParser
import getpass
import re
import json
import sys
from datetime import datetime, date, time, timedelta
try:
    import pyczar
except:
    print('no %s installed' % 'pyczar')

config = ConfigParser.ConfigParser()
config.readfp(open('vaultcreds.config'))


def getImplPlanDetails(caseId,session):
    gusObj = Gus()
    impl_plan_ids = []
    query = "select Id,Case__c,Status__c from SM_Change_Implementation__c where Case__c='" + caseId +"'"
    case_details = gusObj.run_query(query,session)
    if case_details['records']:
        for r in case_details['records']:
            impl_plan_ids.append(r['Id'])
    return impl_plan_ids

def getImplPlanStatus(caseId,session):
    gusObj = Gus()
    impl_plan_status = []
    query = "select Id,Case__c,Status__c from SM_Change_Implementation__c where Case__c='" + caseId +"'"
    case_details = gusObj.run_query(query,session)
    if case_details['records']:
        for r in case_details['records']:
            impl_plan_status.append(r['Status__c'])
            logging.debug(r['Status__c'])
    return impl_plan_status

def PMStartValid(impl_plan_status):
    if len(impl_plan_status) == 1:
        print(impl_plan_status)
        if 'In Progress' not in impl_plan_status:
            return False
        else:
            return True
    elif len(impl_plan_status) > 1:
        for pmstat in impl_plan_status:
            if pmstat != 'In Progress':
                return False
            else:
                return True
        
    
def getCaseId(caseNum,session):
    gusObj = Gus()
    case_details = gusObj.get_case_details_caseNum(caseNum,session)
    return case_details.rstrip()

def getCreds():
    pc = pyczar.Pyczar()
    keyDir = config.get('VAULT', 'keydir')
    valut = config.get('VAULT', 'vault')
    server = config.get('VAULT', 'servera')
    port = config.get('VAULT', 'port')
    new_server = pc.change_server(server,port)
    client_id = pc.get_secret(valut, 'client_id', keyDir)
    client_secret = pc.get_secret(valut, 'client_secret', keyDir)
    username = pc.get_secret(valut, 'username', keyDir)
    passwd = pc.get_secret(valut, 'passwd', keyDir)
    return client_id,client_secret,username,passwd
    
if __name__ == '__main__':
    
    usage = """
    Code to send pm ends for all parts of the implementation plan and close the case
    
    %prog -c 00000000 [-v]
    
    Example closing two cases:
    %prog -c 00081381,00081382
    
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                            help="The case number(s) of the case to attach the file ")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # set username and details of case
    try:
        client_id,client_secret,username,passwd = getCreds()
        logging.debug('%s, %s, %s' % (client_id,client_secret,username))
 
    except Exception as e:
        print('Problem getting username, client_id or client_secret: %s')
        sys.exit()
    # instantiate auth object and generate session dict
    authObj = Auth(username,passwd,client_id,client_secret)
    session = authObj.login()
    
    if options.caseNum:
        casenums = options.caseNum.split(',')
        for case in casenums:
            caseId = getCaseId(case, session)
            logging.debug(caseId)
            impl_plan_ids = getImplPlanDetails(caseId,session)
            impl_plan_status = getImplPlanStatus(caseId,session)
            logging.debug("%s %s" % (impl_plan_ids,impl_plan_status))
            pmstatus = PMStartValid(impl_plan_status)
            logging.debug(pmstatus)
            while pmstatus != True:
                print("PM Status is currently %s" % pmstatus)
                proceed = raw_input("Continue(yes) or Exit(no)?")
                yes = ('Y', 'y', 'YES', 'yes')
                if proceed in yes:
                    pmstatus = PMStartValid(impl_plan_status)
                else:
                    sys.exit(1)
            else:
                break
            sys.exit(0)
                