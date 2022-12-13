#
#
import os
import sys
import re
import requests
from subprocess import PIPE,STDOUT
import subprocess


global _wrkspc
global _pullid

def pull_files():
    token = os.environ['GIT_TOKEN']
    endpoint = "https://git.soma.salesforce.com/api/v3"
    resource = "/repos/cpt/cptops_case_gen/pulls/%s/files"
    files = []
    filereg = re.compile(r'(?<=templates\/)(.*\.template)$', re.MULTILINE)
    filesurl = endpoint + resource % (_pullid)
    out = requests.get(filesurl, auth=("mgaddy", token))
    data = out.json()
    for file in data:
        if filereg.search(file['filename']):
           f = filereg.search(file['filename'])
           files.append(str(f.group()))
    return files

def run_lint(files):
    rtn_codes = {}
    lint_script = _wrkspc + "/cptops_template-linter/template_lint.py -v -t "
    for file in files:
        command = "python " + lint_script + _wrkspc + "/templates/" + file
        output = subprocess.Popen(command.split(), stdout=PIPE)
        report = output.stdout.read()
        data = output.communicate()[0]
        rc = output.returncode
        rtn_codes[file] = rc
        post_updates(report)
    return rtn_codes

def post_updates(report):
    token = os.environ['GIT_TOKEN']
    endpoint = "https://git.soma.salesforce.com/api/v3"
    comments_resource = "/repos/cpt/cptops_case_gen/issues/%s/comments"
    com_url = endpoint + comments_resource % (_pullid)
    post_comment = {"body": report}
    requests.post(com_url, json=post_comment, auth=("mgaddy", token))

if __name__ == "__main__":
    _wrkspc = os.environ['WORKSPACE']
    _pullid = os.environ['ghprbPullId']
    print _pullid
    print _wrkspc
    files = pull_files()
    rc = run_lint(files)
    for val in rc.itervalues():
       if val != 0:
          exit(1)
