#!/usr/bin/python
#
#
import os
import subprocess
import re

case_file = '/case_builder/cases.sh'
cmd_type = re.compile(r'^(python\s[a-z_.]*)')

os.chdir('/home/jenkins/git/cptops_case_gen/bin')

if os.path.isfile(case_file):
    with open(case_file, 'r') as f:
        for line in f:
            ln_check = cmd_type.match(line)
            if ln_check.group() == "python gus_cases.py":
                os.environ['https_proxy'] = "http://public-proxy1-0-sfm.data.sfdc.net:8080/"
                os.system(line)
            else: 
                os.environ['https_proxy'] = ""
                os.system(line)