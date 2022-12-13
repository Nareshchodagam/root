#!/usr/bin/python
###############################################################################
#
# Purpose: Retrieve host information from iDB and use it in an automated way.
# See usage for more details.
###############################################################################
import sys
import common
import json
import urllib2
import glob
import os
import shutil
import optparse
import subprocess
import pprint
import logging
import re
from common import Common
common=Common()


###############################################################################
#                Constants
###############################################################################
tmpfile = common.tmpdir + '/checkhost.tmp'
iDBurl = {'asg': "https://inventorydb1-0-asg.data.sfdc.net/api/1.03",
          'chi': "https://inventorydb1-0-chi.data.sfdc.net/api/1.03",
          'chx': "https://inventorydb1-0-chx.data.sfdc.net/api/1.03",
          'lon': "https://inventorydb1-0-lon.data.sfdc.net/api/1.03",
          'sfm': "https://inventorydb1-0-sfm.data.sfdc.net/api/1.03",
          'sjl': "https://inventorydb1-0-sjl.data.sfdc.net/api/1.03",
          'tyo': "https://inventorydb1-0-tyo.data.sfdc.net/api/1.03",
          'was': "https://inventorydb1-0-was.data.sfdc.net/api/1.03",
          'wax': "https://inventorydb1-0-wax.data.sfdc.net/api/1.03",
          'cidb': "https://cidb1-0-sfm.data.sfdc.net/cidb-api/1.03",
          }

cache = dict()
###############################################################################
#                Functions
###############################################################################
def chunks(l, n):
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]


def parse_hosts(input_file,cidblocal=False):
    # Loop through the hosts in the hostlist.
    for hostname in input_file:
        # Build the API URL
        hostname=hostname.rstrip('\n')
        if cidblocal:
            #CIDB URL is slightly different, so it needs to be cut up and
            #reassembled.
            derivedc = hostname.split('-')[3]
            derivever = iDBurl['cidb'].split('/')[4]
            derivemethod = iDBurl['cidb'].split('/')[0]
            derivehost = iDBurl['cidb'].split('/')[2]
            derivepath = iDBurl['cidb'].split('/')[3]
            url = derivemethod + '//' + derivehost + '/'  + \
                derivepath + '/' + derivedc + '/'+ derivever + \
                '/allhosts?name=' + \
                hostname + '&expand=cluster,cluster.superpod,superpod.datacenter'
            # Use the java cli tool to sign the CIDB request and return a
            # keyed URL.
            url = os.popen('java -jar '+ common.cidb_jar_path + \
                '/cidb-security-client-0.0.3.jar ' + common.cidb_jar_path + \
                '/keyrepo "' + url + '"' ).read()
        else:
            url = iDBurl[dc] + '/allhosts?name=' + hostname + '&expand=cluster,cluster.superpod,superpod.datacenter'

        logging.debug(url)
        # Send the request.
        r = urllib2.urlopen(url)

        # use the data.
        data=json.load(r)

        if len(data) > 0:
           hosts[hostname]=data['data']
        else:
           print hostname + ' not in iDB'
    return hosts


def pass_to_genplan(hosts):
    if options.allatonce:
        # This is a hack, it strings together all the hostnames and
        # assumes that you are SURE all the hosts are in the same cluster/sp.
        # It picks the first host out of the dictionary, and sets all other
        # variables to that hosts values. (clusterstatus, clustername.. etc)
        # this requires validation of the hostlist up front. It's not dangerous
        # but it will fail if the hosts aren't the same.

        # TODO: Reassess to see if using the RR group is a better way to go here

        for hostname in hosts:
            hostnames.append(hostname)
            allhosts=','.join(hostnames)
            dc=hostname.split('-')[3]
        tokenhost=hosts.itervalues().next()
        hostrole=tokenhost[0]['deviceRole']
        clusterstatus=tokenhost[0]['failOverStatus']
        clustername=tokenhost[0]['cluster']['name']
        superpod=tokenhost[0]['cluster']['superpod']['name']

        if options.template:
            template=options.template
        else:
            template=hostrole

        # Show some debug/info output
        logging.info("Hostname: " + str(allhosts) + " - Role: " + str(hostrole) + \
        " - Superpod: " + str(superpod) + " - Cluster Name: " + \
        str(clustername) + " - Cluster Status: " + str(clusterstatus))

        # Pump out the jams.
        retvalue=os.system("./build_plan.py -s " + str(superpod) + " -S " + \
        str(clusterstatus) + " -i " + str(clustername) + " -r " + \
        str(hostrole) + " -H " + str(allhosts) + " -d " + str(dc) + \
        " -t " + str(template) + \
        " -c " + str(options.caseNum) + " -f " + common.outputdir + '/' + \
        "allhosts_plan_implementation.txt " + verboseoption + ' -a')
    else:
        # Cut up the data into bite sized pieces.
        for hostname,data in hosts.iteritems():
            hostrole=data[0]['deviceRole']
            clusterstatus=data[0]['failOverStatus'] # PRIMARY/STANDBY
            clustername=data[0]['cluster']['name']
            superpod=data[0]['cluster']['superpod']['name']
            dc=hostname.split('-')[3]

            if options.template:
                template=options.template
            else:
                template=hostrole

            # Show some debug/info output
            logging.info("Hostname: " + str(hostname) + " - Role: " + str(hostrole) + \
            " - Superpod: " + str(superpod) + " - Cluster Name: " + \
            str(clustername) + " - Cluster Status: " + str(clusterstatus))

            # Pump out the jams.
            retvalue=os.system("./build_plan.py -s " + str(superpod) + " -S " + \
            str(clusterstatus) + " -i " + str(clustername) + " -r " + \
            str(hostrole) + " -H " + str(hostname) + " -d " + str(dc) + \
            " -t " + str(template) + \
            " -c " + str(options.caseNum) + " -f " + common.outputdir + '/' + \
            str(hostname) + "_plan_implementation.txt " + verboseoption )

        #######################################################################
        # End the run - hack until Mitchells hostgetter module is merged.
        #######################################################################

        retvalue=os.system("./build_plan.py -s " + str(superpod) + " -S " + \
        str(clusterstatus) + " -i " + str(clustername) + " -r " + \
        str(hostrole) + " -H " + str(hostname) + " -d " + str(dc) + \
        " -t " + str(template) + \
        " -c " + str(options.caseNum) + " -f " + common.outputdir + '/' + \
        str(hostname) + "_plan_implementation.txt " + verboseoption + ' -e' )

def describe_host(host,cidblocal=False):
    # Print out all the idb data fetchable for a given host.
    # Simply display it on the screen.

    f=open(tmpfile,'w')
    f.write(host)
    f.close()
    filename=open(tmpfile,'r')
    hostdata=parse_hosts(filename,cidblocal)
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(hostdata)
    f.close()
    os.remove(tmpfile)

def gen_request(reststring,cidblocal=False,derivedc='',debug=False):
    # Build the API URL
    dc=derivedc.lower()
    if cidblocal:
        #CIDB URL is slightly different, so it needs to be cut up and
        #reassembled.
        derivever = iDBurl['cidb'].split('/')[4]
        derivemethod = iDBurl['cidb'].split('/')[0]
        derivehost = iDBurl['cidb'].split('/')[2]
        derivepath = iDBurl['cidb'].split('/')[3]
        url = derivemethod + '//' + derivehost + '/'  + \
        derivepath + '/' + dc + '/'+ derivever + reststring
        # Use the java cli tool to sign the CIDB request and return a
        # keyed URL.
        url = os.popen('java -jar '+ common.cidb_jar_path + '/cidb-security-client-0.0.3.jar ' + common.cidb_jar_path + '/keyrepo "'+ url + '"' ).read()
    else:
        url = iDBurl[dc] + reststring

    print url
    logging.debug(url)

    # Send the request.
    r = urllib2.urlopen(url)
    # use the data.
    data=json.load(r)
    if debug:
        logging.debug(data)
        logging.debug(data['total'])
    if data['total'] == 1000:
        raise Exception('idb record limit of 1000, you may be missing records')

    return data

def get_dr_prod_by_dc(dclist,filename,cidblocal=True):
  rawresults = dict()
  for dc in dclist:
    reststring = '/clusters?operationalStatus=active&superpod.dataCenter.name=' +dc
    rawresults[dc]=gen_request(reststring,cidblocal,dc)
  dcs = dict()
  for key,vals in rawresults.iteritems():
    drgrp = dict()
    drgrp['Secondary'] = ','.join(sorted([val['name'] for val in vals if val['dr'] ] ))
    drgrp['Primary'] = ','.join(sorted([val['name'] for val in vals if not val['dr'] ] ))
    dcs[key] = drgrp


  if filename:
    with open(filename, 'w') as outfile:
      json.dump(dcs, outfile)
    with open(filename) as json_data:
      d = json.load(json_data)
      json_data.close()
      pp = pprint.PrettyPrinter(indent=2)
      pp.pprint(d)
  return json.dumps(dcs,indent=2)

def cacher(current_obj,arglist):
    # loop through fields from left to right caching ibased on JacksonId if they point to a json object returning if they are cached
    for arg in arglist:
        if type(current_obj[arg]) is unicode:
          current_obj = cache[current_obj[arg]]
        else:
          current_obj=current_obj[arg]
          cache[current_obj['@' + arg + 'JacksonId']] = current_obj
    return current_obj




def get_hosts_by_enum(clusterlist,dr,dc,roles,grouping,cidblocal=True,debug=False):
    superpods=dict()
    assert(grouping.values()!=[False,False],"must group by at least one value")     
    for cluster in clusterlist:
        for role in roles:
          #pass2 get deviceroles and hostlists back and assign to the correct cluster
            reststring = '/allhosts?operationalStatus=active&cluster.dr=' + str(dr).lower() + '&deviceRole=' + role + '&cluster.name=' + cluster + '&fields=name,deviceRole,cluster.name,cluster.superpod.name&expand=cluster'
            print reststring
            current = gen_request(reststring,cidblocal,dc,debug)
            if current['total'] > 0:
              for hval in current['data']:
                  sptemp = cacher(hval,['cluster','superpod'])['name']
                  minorset = hval['name'].split('-')[2]
                  majorset = ''.join([s for s in hval['name'].split('-')[1] if s.isdigit()])
                  list_ident_temp = ''
                  if grouping['cluster'] == True:
                      list_ident_temp = cluster
                  if grouping['role'] == True:
                      list_ident_temp = list_ident_temp + '-' + role
                  if grouping['majorset'] == True:
                      list_ident_temp = list_ident_temp + '-' + majorset
                  if grouping['minorset'] == True:
                      list_ident_temp = list_ident_temp + '-' + minorset
                  print list_ident_temp    

                  if sptemp not in superpods:
                      superpods[sptemp]={}
                  if list_ident_temp not in superpods[sptemp]:
                      superpods[sptemp][list_ident_temp]={}
                  print hval['name']
                  superpods[sptemp][list_ident_temp][hval['name']] = {
                       #add more per host values as necessary
                      'clustername' : cacher(hval,['cluster'])['name'],
                      'rolename' : hval['deviceRole'],
                  }

      #assign hosts to device roles after splitting into groups per maxgroupsize
    j = json.dumps(superpods)
    pprint.pprint(j,indent=2)
    return j

def chunks(l, n):
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]

def merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        elif isinstance(value,list):
            destination[key] = destination[key] + value if (key in destination) else value
        else:
            destination[key] = value

    return destination

def gen_plan_by_cluster_hostnumber(inputdict):
    dc = inputdict['datacenter']
    roles = inputdict['roles'].split(',')
    #optional paramters
    # defaults
    template_id = ''
    grouping={ 
              "cluster" : False,
              "role" : False,
              "majorset" : False, 
              "minorset" : False
        }
    
    dr=inputdict['dr'] if 'dr' in inputdict else False
    template_suffix = '.' + inputdict['template_suffix'] if 'template_suffix' in inputdict else ''
    gsize = inputdict['maxgroupsize'] if 'maxgroupsize' in inputdict else 1
    
    if 'grouping' in inputdict:
      for grp in inputdict['grouping'].split(','):
        if grp in grouping.keys():
            grouping[grp] = True
                
    
    if 'templateid' in inputdict:
       template_id = inputdict['templateid']
    elif gsize>1 and len(roles)>1:
       raise Exception('if maxgroupsize is > 1 and you have specified more than one role you need a template')
    


    results=json.loads(get_hosts_by_enum(inputdict['cl_list'],dr,dc,roles,grouping,cidblocal=True,debug=False))
    #generate template
    fullhostlist=[]
    ro = ''
    for sp in results.keys():
       for host_enum in sorted(results[sp].keys()):
           i = 0
           for hostnames in chunks(sorted(results[sp][host_enum].keys()),gsize):
                fullhostlist.extend(hostnames)
                cl =  ','.join(set([results[sp][host_enum][host]['clustername'] for host in hostnames]))
                ro = ','.join(set([results[sp][host_enum][host]['rolename'] for host in hostnames]))
                i += 1
                fileprefix = host_enum + str(i) + '_' + cl
                #build individual plans setting template to role name unless a template is specified
                #want to use template for role by default unless overridden
                template_id = ro + template_suffix if len(template_id)==0 else template_id + template_suffix
                template_id = template_id + '.dr' if dr else template_id
                os.system("./build_plan.py -s " + sp + \
                " -i " + str(cl) + " -d " + dc + " -r " + \
                ro +  " -t " + template_id + " -H " + ','.join(hostnames).encode('ascii') + " -d " + str(dc) + \
                " -c " + str(options.caseNum) + " -f " + common.outputdir + '/' + fileprefix + "_plan_implementation.txt")


    # roll all plans into one text file adding pre and post logic
    os.system("./build_plan.py -c " +str(options.caseNum) + " -e -r " + ro + " -t " + template_id + " -H " + ','.join(fullhostlist) + " -i " \
              + ','.join(inputdict['cl_list']) +  " -d " + dc + " -s none")


def gen_dc_plan(inputdict):
  # gen_dc_plan(dc_list,sp_list,cl_list,clustergroup=4,hostgroup=2):
  results=json.loads(gethostlists(inputdict['dc_list'],cidblocal=True,debug=False,maxgroupsize=inputdict['maxgroupsize']))

  #apply filters fpr SP CL and role
  for dc in results.keys():
    for sp in sorted(results[dc].keys()):
      if sp not in inputdict['sp_list']:
        del results[dc][sp]
      else:
        for cl in sorted(results[dc][sp].keys()):
          if cl not in inputdict['cl_list']:
            del results[dc][sp][cl]
          else:
            for ro in sorted(results[dc][sp][cl].keys()):
              if ro not in sorted(inputdict['roles']):
                del results[dc][sp][cl][ro]

  #apply merge
  for dc in results.keys():
    for sp in results[dc].keys():
      for cllist in chunks(results[dc][sp].keys(),inputdict['clustersize']):
        if len(cllist) > 1: #don't merge if it is only one pod
          clstr=','.join(cllist)
          results[dc][sp][clstr]={}
          for cl in cllist:
            results[dc][sp][clstr]=merge(results[dc][sp][cl],results[dc][sp][clstr])
            del results[dc][sp][cl]
  #generate template
  for dc in results.keys():
    print dc
    for sp in sorted(results[dc].keys()):
      print ' ' + sp
      for cl in sorted(results[dc][sp].keys()):
        print '    ' + cl
        for ro in sorted(results[dc][sp][cl].keys()):
          print '        ' +ro
          for gp in results[dc][sp][cl][ro]:
            hostnames = results[dc][sp][cl][ro][gp]
            print '                   ' + gp + ' ' + str(hostnames)
            #   print '               release_runner.pl -invdb_mode -superpod ' +  sp  + ' -cluster ' + cl + '  -device_role ' + ro + ' -host ' + ','.join(mylist)
            # Show some debug/info output
            #logging.info("Hostname: " + str(hostnames) + " - Role: " + str(ro) + \
            #" - Superpod: " + str(sp) + " - Cluster Name: " + \
            #str(cl)
            # ./build_plan.py -s SP1 -i NA7,NA24 -H host1,host2,host3 -t search -r search -c 000001 -d was
            retvalue=os.system("./build_plan.py -s " + str(sp) + \
            " -i " + str(cl) + " -d " + dc + " -r " + \
            ro +  " -t " + ro + " -H " + ','.join(hostnames).encode('ascii') + " -d " + str(dc) + \
            " -c " + str(options.caseNum) + " -f " + common.outputdir + '/' + str(cl) + "_" + gp + "_plan_implementation.txt")







###############################################################################
#                Main
###############################################################################

if __name__ == "__main__":

    usage="""
            * Retrieve information about a host from iDB
            Usage:
            - Process a hostlist and send it's result to gen_plan.py
            %prog -c <CASENUM> -l /path/to/hostlist [default]
            - Print out data about a single host
            %prog -d ops-myhost-dc
            - Process a hostlist in an "all at once fashion" (pass csv of hostnames) i
              IMPORTANT must all be of the same cluster this is not checked
            %prog -a -c <CASENUM>
            - use CIDB from your local
            %prog -C -a -c 0000001 -l ~/tyospellcklist
            - Override default template
            %prog -c <CASENUM> -t spellchecker.glibc
            %prog -c <CASENUM> -C -G '{"cl_list" : ["NA7","NA11","NA12","NA14","CS9"] ,"datacenter": "was" , "role": "search" }'
            -generate implementation plan grouped by minorset and major set (1-1, 1-2, 2-2 etc..) given a list f clusters
            -size of hostlist = number of clusters (eg 5 above) this can be overriden downwards by optional groupsize parameter
            """
    parser = optparse.OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum", help="The case number to use")
    parser.add_option("-r", "--role", dest="role", help="Host role")
    parser.add_option("-t", "--template", dest="template", help="Override Template")
    parser.add_option("-g", "--geo", dest="geo", help="geo list")
    parser.add_option("-o", "--out", dest="out", help="output file")
    parser.add_option("-G", "--idbgen", dest="idbgen", help="generate from idb")
    parser.add_option("-d", "--describe_host", dest="describe_host", \
                      help="Print information about a single host")
    parser.add_option("-a", "--all", dest="allatonce", action='store_true', default=False,\
                      help="Run all the hosts at once")
    parser.add_option("-l", "--hostlist", dest="hostList", \
                      help="A text file with a list of hosts", default='hostlist')
    parser.add_option("-C", "--cidblocal", dest="cidblocal", action='store_true', default=True,\
                      help="access cidb from your local machine")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, \
                      help="verbosity")
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
        verboseoption='-v'
    else:
        logging.basicConfig(level=logging.ERROR)
        verboseoption=''
###############################################################################
#                Prep Work
###############################################################################


# Clean up the old output files
    cleanup=glob.glob(common.outputdir + "/*")
    for junk in cleanup:
        os.remove(junk)

    hosts=dict()
    hostnames=[]
    if options.geo:
       geolist = options.geo.split(',')
       get_dr_prod_by_dc(geolist,options.out)
    elif options.idbgen:
      inputdict = json.loads(options.idbgen)
      print inputdict.keys()
      gen_plan_by_cluster_hostnumber(inputdict)
    elif options.describe_host:
        describe_host(options.describe_host,options.cidblocal)
    else:
        filename=open(options.hostList)
        hosts=parse_hosts(filename,options.cidblocal)
        pass_to_genplan(hosts)



