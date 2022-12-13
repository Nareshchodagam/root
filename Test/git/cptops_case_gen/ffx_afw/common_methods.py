# command commands
import logging
import subprocess
import socket

def getData(filename):
    with open(filename) as data_file:
        data = data_file.readlines()
    return data

def writeOut(data,output_file):
    with open(output_file, 'w') as f:
        for d in data:
            d = d +"\n"
            f.write(d)

def writeOutPlan(data,output_file):
    with open(output_file, 'w') as f:
        for d in data:
            f.write(d)

def where_am_i():
    """
    Figures out location based on hostname
    
    Input : nothing
    Returns : 3 letter site code
    """
    hostname = socket.gethostname()
    logging.debug(hostname)
    if not re.search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst,hfuc,g,site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

def run_cmd(cmdlist):
    """
    Uses subprocess to run a command and return the output
    
    Input : A list containing a command and args to execute
    
    Returns : the output of the command execution
    """
    logging.debug(cmdlist)
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = run_cmd.communicate()
    return out

def get_inst_site(host):
    """
    Splits a host into a list splitting at - in the hostname
    The list contains inst,host function, group and 3 letter site code
    Input : hostname 
    
    Returns : list containing inst,host function and 3 letter site code ignoring group.
    """
    inst,hfunc,g,site = host.split('-')
    short_site = site.replace(".ops.sfdc.net.", "")
    return inst,hfunc,short_site

