#!/usr/bin/env python
'''
        Script for interacting with work items in Gus
'''
from GUS.base import Auth
from GUS.base import Gus
import pprint
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

configdir = os.environ['HOME'] + "/.cptops/config"
config = ConfigParser.ConfigParser()
try:
    config.readfp(open(configdir + '/creds.config'))
except IOError:
    logging.error("No creds.config file found in %s", configdir)
    sys.exit(1)

def attachWI(fileName, workItemId, sess):
    gusObj = Gus()
    fObj = open(fileName)
    file_attach = gusObj.attachWI(fObj, fileName, workItemId, sess)
    fObj.close()
    print(file_attach)

def getWorkItemId(workItemNum,session):
    gusObj = Gus()
    case_details = gusObj.getWorkItemDetailsNum(workItemNum,session)
    return case_details.rstrip()


if __name__ == '__main__':
    
    usage = """
    Code to send pm ends for all parts of the implementation plan and close the case
    
    %prog -c 00000000 [-v]
    
    Example closing two cases:
    %prog -c 00081381,00081382
    
    """
    parser = OptionParser(usage)
    parser.add_option("-w", "--workitem", dest="workItem",
                            help="The work item to attach the file(s) to")
    parser.add_option("-a", "--attachments", dest="attachments",
                            help="The file(s) to attach to a workItem")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # set username and details of case

    try:
        gpass = config.get('GUS', 'guspassword')
    except ConfigParser.NoOptionError,e:
        gpass = getpass.getpass("Please enter your GUS password: ")
    username = config.get('GUS', 'username')
    # instantiate auth object and generate session dict
    authObj = Auth(username,gpass)
    session = authObj.login()
    
    
    if options.workItem:
        workItemNum = options.workItem
        work_item_id = getWorkItemId(workItemNum, session)
        print(work_item_id)
        if options.attachments:
            files = options.attachments.split(',')
            print(files)
            for f in files:
              attachWI(f, work_item_id, session)  
    