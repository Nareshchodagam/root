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
import os.path
from datetime import datetime, date, time, timedelta

config = ConfigParser.ConfigParser()
config.readfp(open('creds.config'))

    
def getCaseId(caseNum,session):
    gusObj = Gus()
    case_details = gusObj.get_case_details_caseNum(caseNum,session)
    return case_details.rstrip()

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
    
def attach_file(filename, caseId, session):
    gusObj = Gus()
    name = 'plan_implementation.txt'
    logging.debug(name,filename)
    fObj = open(filename)
    attachRes = gusObj.attach(fObj, name, caseId, session)
    fObj.close()
    logging.debug("%s %s %s %s" % (filename, name, caseId, session))
    logging.debug(attachRes)
    return attachRes
    
if __name__ == '__main__':
    
    usage = """
    Code to attach a new implementation plan and rename the original.
    
    %prog -c 00000000 [-f filename] [-o oldfilename] [-v]
    
    Example closing two cases:
    %prog -c 00081381 -f plan_implementation.txt -o plan_implementation.previos -v
    
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                            help="The case number(s) of the case to attach the file ")
    parser.add_option("-f", "--file", dest="filename",
                            help="The file to attach")
    parser.add_option("-o", "--oldfile", dest="oldfilename",
                            help="The file to attach")
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
    
    if not options.filename:
        print('No file to attach. Exiting')
        sys.exit()
    
    if options.oldfilename:
        name = options.oldfilename
    else:
        name = 'plan_implementation.previous'
    
    if options.caseNum and options.filename:
        #casenums = options.caseNum.split(',')
        caseId = getCaseId(options.caseNum, session)
        plan_id = getExistingPlanId(caseId, session)
        moveExistingPlan(name, plan_id, session)
        attach_file(options.filename, caseId, session)
        
        