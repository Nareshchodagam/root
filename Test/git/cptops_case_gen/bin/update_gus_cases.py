#!/usr/bin/env python
'''
        Script for closing/updating cases in Gus
'''
import ConfigParser
import getpass
import logging
import re
import sys
from datetime import datetime
from optparse import OptionParser

from base import Auth
from base import Gus

config = ConfigParser.ConfigParser()
config.readfp(open('creds.config'))


def getImplPlanDetails(caseId, session):
    gusObj = Gus()
    impl_plan_ids = []
    query = "select Id,Case__c from SM_Change_Implementation__c where Case__c='" + caseId + "'"
    case_details = gusObj.run_query(query, session)
    if case_details['records']:
        for r in case_details['records']:
            impl_plan_ids.append(r['Id'])
    return impl_plan_ids


def case_status(status):
    if re.match(r'success', status, re.IGNORECASE):
        impl_status = "Implemented - per plan"
        c_status = "Closed"
        c_outcome = "Successful"
    elif re.match(r'dup', status, re.IGNORECASE):
        impl_status = "Pending Implementation"
        c_status = "Closed - Duplicate"
        c_outcome = "Cancelled"
    elif re.match(r'no', status, re.IGNORECASE):
        impl_status = "Not Implemented"
        c_status = "Closed - Not Executed"
        c_outcome = "Cancelled"
    elif re.match(r'partial', status, re.IGNORECASE):
        impl_status = "Partially Implemented"
    else:
        print ("%s Not a valid Status. It should be Success|Dup|No " % status)
        sys.exit(1)
    if status == "partial" or status == "Partial":
        return impl_status
    else:
        return impl_status, c_status, c_outcome


def closeImplPlan(impl_plan_ids, caseId, session, status):
    gusObj = Gus()
    now = datetime.now()
    end = now.isoformat()
    for id in impl_plan_ids:
        dict = {'Case__c': caseId, 'End_Time__c': end, 'Status__c': '%s' % status}
        details = gusObj.updateImplPlan(id, dict, session)
        logging.debug(details)


def closeCase(caseId, session, c_status, c_outcome):
    gusObj = Gus()
    Dict = {
        'Status': '%s' % c_status,
        'SM_Change_Outcome__c': '%s' % c_outcome,
    }
    details = gusObj.update_case_details(caseId, Dict, session)
    logging.debug(details)


def getCaseId(caseNum, session):
    gusObj = Gus()
    case_details = gusObj.get_case_details_caseNum(caseNum, session)
    return case_details.rstrip()


def getCaseSub(caseId, session):
    gusObj = Gus()
    case_subject = gusObj.get_case_subject_caseNum(caseId, session)
    return case_subject.rstrip()


if __name__ == '__main__':

    usage = """
    Code to send pm ends for all parts of the implementation plan and close the case

    Code to only update the case's Implementation planner status

    %prog -c 0000000 [-v] -s partial
    
    %prog -c 00000000 [-v] -s <status>
    
    Example closing two cases:
    %prog -c 00081381,00081382 -s <success|dup|no|partial>

    success - Closed case successfully
    dup - Close case as duplicate
    no - Close case as Not-Executed
    partial - Update case as Partially Implemneted
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                      help="The case number(s) of the case to attach the file ")
    parser.add_option("-y", "--confirm", action="store_true", dest="confirm", help="Answer yes to prompts.")
    parser.add_option("-s", "--status", dest="status", help="Status of the case")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")  # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # set username and details of case

    if not options.status:
        options.status = "Success"
    if options.status == "partial" or options.status == "Partial":
        impl_status = case_status(options.status)
    else:
        (impl_status, c_status, c_outcome) = case_status(options.status)

    try:
        gpass = config.get('GUS', 'guspassword')
    except ConfigParser.NoOptionError, e:
        gpass = getpass.getpass("Please enter your GUS password: ")
    try:
        username = config.get('GUS', 'username')
        client_id = config.get('GUS', 'client_id')
        client_secret = config.get('GUS', 'client_secret')
    except:
        print('Problem getting username, client_id or client_secret')
        sys.exit()
    # instantiate auth object and generate session dict
    authObj = Auth(username, gpass, client_id, client_secret)
    session = authObj.login()

    if options.caseNum:
        caseDetails = {}
        casenums = options.caseNum.split(',')
        print "Closing/updating the  the following below cases..\n"
        for case in casenums:
            caseId = getCaseId(case, session)
            logging.debug(caseId)
            caseSub = getCaseSub(caseId, session)
            caseDetails[caseId] = case + " - " + caseSub
        for subject in caseDetails.itervalues():
            print subject
        if not options.confirm:
            response = raw_input('\nDo you wish to continue? (y|n) ')
            if response.lower() != "y":
                print "Exiting....."
                sys.exit(1)

        for id in caseDetails.iterkeys():
            impl_plan_ids = getImplPlanDetails(id, session)
            logging.debug(impl_plan_ids)
            if options.status == "partial" or options.status == "Partial":
                closeImplPlan(impl_plan_ids, id, session, impl_status)
            else:
                closeImplPlan(impl_plan_ids, id, session, impl_status)
                closeCase(id, session, c_status, c_outcome)
