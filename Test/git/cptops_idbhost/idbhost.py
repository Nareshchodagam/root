#!/opt/sfdc/python27/bin/python
#
# mutual auth is not supported without the requests module
# you can try adding stdlib functionality using custom ssl context and urllib2
# good luck
#
import getpass
import itertools
import json
import logging
import re
import sys
import os
# hacky way to get requests from sfdc python 2.7.13
# if called from /opt/rh/python27 IT WILL BREAK DUE TO URLLIB3 INCOMPATIBILITIES!
# worst case use requests from os python 2.6 and make sure there is warning!
# it does't hurt to exhaust all new paths first !
site_packages_new_path="/opt/sfdc/python27/celery_venv/lib/python2.7/site-packages"
if os.path.exists(site_packages_new_path):
    sys.path.append(site_packages_new_path)
try:
    import requests
except ImportError as ex:
    site_packages_old_path="/usr/lib/python2.6/site-packages/"
    if os.path.exists(site_packages_old_path):
        logging.warning("unable to find 'requests' module. getting it from 2.6 site packages. This is not secure")
        sys.path.append(site_packages_old_path)
        import requests
    else:
        raise ImportError(ex)

from collections import defaultdict
from multiprocessing import Process, Queue, Manager
from os import path, environ
from socket import gethostname
from subprocess import PIPE, Popen
from threading import Thread

class Idbhost():
    """
    Help on module Idbhost:

    NAME
        Idbhost

    DESCRIPTION
        The purpose of this module is to retrieve specific information related to
        Compute Deploy needs to feed into other programs (Template generation, nagios_monitor).

    Instructions

    How to import -
        from idbhost import Idbhost

    Make an alias of the initial call to the module. You can also set the search path
    (i.e IDB server) to make API calls.
        idb=Idbhost() or
    To m/ake API calls in chi IDB server.
        idb=Idbhost('chi')
    """

    def __init__(self, site=None, user=None, pswd=None, **kwargs):
        # Determine where we're being executed so we connect to the right IDB server
        if site is not None:
            self.site = site
        else:
            self.site = self.get_my_site()
        self.user = user
        self.pswd = pswd
        self.krb_auth = False

        self.cert_key = self.cert_pem = self.cert_internal = None

        # Set up client cert, if available
        if not kwargs:  # W-4275396 Now users can pass their own key and cert to idb.
            path_pem = environ['HOME']+'/.cptops/auth/client.pem'
            path_key = environ['HOME']+'/.cptops/auth/client.key'
        else:
            path_pem = kwargs.get('path_pem')
            path_key = kwargs.get('path_key')

        if user is None or pswd is None:
            if path_pem is None or path_key is None:
                logging.debug("Client cert or key was not supplied")
                self._get_ticket()
            else:
                if path.exists(path_pem) and path.exists(path_key):
                    self.cert_pem = path_pem
                    self.cert_key = path_key
                    logging.debug('client cert and key path found')
                else:
                    logging.debug('client cert and key path not found')
                    self._get_ticket()

        # Set up the internal root ca to verify the IDB server
        ca_paths = [ path.join(path.dirname(path.realpath(__file__)), 'auth/internal_ca.pem'),
                     environ['HOME']+'/.cptops/auth/internal_ca.pem' ]
        for ca_path in ca_paths:
            if path.exists(ca_path):
                self.cert_internal = ca_path
                logging.debug('found internal root ca ' + ca_path)

        if self.cert_internal is None:
            if os.environ.get('IDB_USER_CRED') != 'True':
                logging.error('could not find internal root ca!')
                sys.exit(1)
            else:
                logging.warning('could not find internal root ca! Will not be using certificate auth !! ')
                self.cert_internal = False

    def _get_ticket(self):   # W-4244967 - Support to read kerb ticket
        # Renew existing kerb ticket and use it to query idb. In case ticket expired,
        # get creds if none were passed, store them if they were; need to get creds
        # here before anything uses threading on us which will mess up stdin
        ticket_refresh = self._refresh_kerb()
        # try checking ticket for now
        if not ticket_refresh:
            ticket_refresh = self._check_kerb()
        if ticket_refresh:
            print("Refreshing kerberos ticket")
            self.krb_auth = True
        if not ticket_refresh:
            print("Can't refresh ticket, getting new one [kinit]")
            self.user, self.pswd = self._get_stdin_creds()
            p = Popen('kinit', stdout=PIPE, stdin=PIPE, stderr=PIPE)
            p.stdin.write(self.pswd + '\n')
            p.stdin.close()


    def get_my_site(self):
        """
        Figures out which idb site to connect to based on current location
        :param: nothing
        :return: 3 letter site code
        """
        hostname = gethostname()
        logging.debug("parsing site out of: "+hostname)
        if re.search(r'internal.salesforce.com', hostname) or not re.search(r'(sfdc.net|salesforce.com)', hostname):
            site = 'prd'
        else:
            inst,hfuc,g,site = hostname.split('-')
            site = site.replace(".ops.sfdc.net", "")
            site = site.replace(".eng.sfdc.net", "")
        logging.debug("using site: "+site)
        return site

    def validatedc(self, dc):
        valid_dcs = ['was', 'chi', 'dfw', 'par', 'asg', 'sjl', 'lon', 'frf', 'tyo',
                     'chx', 'wax', 'sfm', 'phx', 'ukb', 'crd', 'crz', 'prd', 'sfz',
                     'ord', 'iad', 'yul', 'yhu', 'hnd', 'cdu', 'syd', 'xrd', 'fra',
                     'cdg', 'ia2', 'ph2', 'lo2', 'lo3', 'rd1', 'rz1', 'ttd', 'hio']
        if dc not in valid_dcs:
            raise Exception("%s is not a valid DC." % dc)

    def idbquery(self,datacenters,idb_resource,fields,idbfilters,usehostlist=False):
        """
        datacenters: tuple of 3 character datacenter ids eg : was,chi,tyo ..
        idbfilters : dict of key = valid target fieldname, value = tuple of values
        returns : results by reststring
        """
        assert len(datacenters) > 0, "Error no datacenters specified"
        # W-4742325 - Updated code to support pagination iDB
        results = {}
        counter = 0
        maxrecords = 1000
        l = []
        idb_resource = idb_resource+"start={}&"
        reststring_list = self._get_uri_list(idb_resource, fields, idbfilters)
        for dc in datacenters:
            for reststring in reststring_list:
                reststring = reststring.encode("ascii")
                if (usehostlist and reststring.split('=')[2].split('&')[0].split('-')[3] == dc) or (not usehostlist):
                    while True:
                        reststring_f = reststring.format(counter)
                        current, url = self._get_request(reststring_f, dc)
                        l.extend(current['data'])
                        if current['total'] == maxrecords:
                            counter += 1000
                            continue
                        else:
                            break
                else:
                    continue
            results[dc] = l
        return results

    def _get_uri_list(self, idb_resource, fields, idbfilters):
        """
        construct list of reststrings  using dict idbfilters
        """

        requestlist = []
        results=[]
        assert len(fields) > 0, "Error: No fields specified"
        assert len(idbfilters.keys()) > 0, "Error no filters specified"

        #convert each to list if string assigned
        for key,val in idbfilters.items():
            idbfilters[key] = [val] if not isinstance(val,list) else val


        for key in idbfilters:
            assert (isinstance(idbfilters[key], list) and len(idbfilters[key][0]) > 0), "idbfilter " + key + " must have at least one value"
            requestlist.append([(key,val) for val in idbfilters[key] ])


        requestlist.append([('fields', ','.join(fields))] )

        for clauses in itertools.product(*requestlist):
            reststring = idb_resource + '&'.join(['='.join(clause) for clause in clauses ])
            results.append(reststring)

        return results

    def _get_stdin_creds(self):
        """
        get kerberos credentials from stdin
        :param: nothing
        :return: username and password tuple
        """
        user = pswd = ''
        while not user:
            user = getpass.getuser()
        while not pswd:
            pswd = getpass.getpass('Password: ')
        return user, pswd

    def _check_kerb(self):
        """
        check the host system for a kerberos ticket
        :return: boolean
        """
        from celerytasks.lib.interfaces.shellcommand import ShellCommand
        print('Checking kerberos ticket via /usr/bin/klist -s')
        s = ShellCommand()
        ret = s.run('/usr/bin/klist', sudo=False, arguments=['-s'])
        if ret != 0:
            print("It seems kerb ticket expired/not present ")
            return None
        else:
            print("Kerberos ticket found")
            return True

    def _refresh_kerb(self):
        from celerytasks.lib.interfaces.shellcommand import ShellCommand
        # Kerberos tickets expire after 2 hours, so refresh kerberos ticket now
        print('Refreshing kerberos ticket via /usr/bin/kinit -R')
        s = ShellCommand()
        ret = s.run('/usr/bin/kinit', sudo=False, arguments=['-R'])
        if ret != 0:
            print("It seems kerb ticket expired")
            return None
        else:
            print("Kerberos ticket refreshed")
            return True

    def _get_request(self, restring, dc):
        """
        finalize and make the actual connection to idb
        cert target: https://cfg0-<idb,cidb,ddb>apima1-0-<dc>.data.sfdc.net/
        kerb target: https://cfg0-<idb,cidb,ddb>apik1-0-<dc>.data.sfdc.net/
        cidb endpoints: /cidb-api/<dc>/1.04/*
        idb endpoints: /api/1.04/*
        """
        # Figure out if we should be connecting to ddb (ugly), cidb or idb
        if restring.startswith('roleconfigs'):
            url1 = 'https://cfg0-ddb'
            url2 = '1-0-{0}.data.sfdc.net/api/1.02/'.format(self.site) + restring
        elif self.site == dc: #idb
            url1 = 'https://cfg0-idb'
            url2 = '1-0-{0}.data.sfdc.net/api/1.04/'.format(dc.lower()) + restring
        else:               #cidb
            url1 = 'https://cfg0-cidb'
            url2 = '1-0-{0}.data.sfdc.net/cidb-api/{1}/1.04/'.format(self.site, dc.lower()) + restring

        # Initialize a requests session and a return var; fill in details later
        s = requests.Session()
        r = None

        # Process the request
        if self.cert_pem is None or self.cert_key is None:
            # Kerberos auth
            logging.debug('using kerberos authentication with idb')
            url = url1+'apik'+url2
            logging.debug('url %s' % url)

            if self.krb_auth:
                from requests_kerberos.kerberos_ import HTTPKerberosAuth
                s.auth = HTTPKerberosAuth()
                r = s.get(url.rstrip('\n'), verify=self.cert_internal)
            else:
                s.auth = (self.user, self.pswd)
                r = s.get(url.rstrip('\n'), verify=self.cert_internal)

        else:
            # Mutual cert auth
            logging.debug("using client cert to authenticate with idb")
            url = url1+'apima'+url2
            logging.debug('url %s' % url)

            r = s.get(url.rstrip('\n'), cert=(self.cert_pem, self.cert_key), verify=self.cert_internal)

        # Check for some common errors
        if r.status_code == 401:
            logging.error('http status code 401 - unauthorized; check username & password')
            sys.exit(401)
        if r.status_code == 404:
            logging.error('http status code 404 - not found')
            sys.exit(404)
        if r.status_code != 200:
            logging.warning('http status code '+str(r.status_code))

        if r.status_code == 500:
            logging.warning('Failed to load resource: the server responded with a status of 500 (Server Error) for url %s', url)

        # Process and return the data
        data = r.json()
        if 'total' in data.keys():
            if data['total'] == 2000:
                raise Exception('Hit the 2000 record limit in IDB, you may be missing records')
        return data, url

    def _get_products(self, roles):
        """
        Get products from dDB for a list of given roles
        :param: list of roles (or single role str); datacenter
        :return: role->product(s) dict
        """

        # some error checking and conversion
        if not isinstance(roles, list) and not isinstance(roles, str):
            logging.error('_get_products: roles argument is wrong type {0} (expecting list or str)'.format(type(roles)))
            sys.exit(1)
        elif not roles:
            logging.warning('_get_products: no roles given; returning empty list')
            return []
        elif isinstance(roles, str):
            roles = [roles]

        # make sure roles are unique to prevent extraneous calls
        roles = list(set(roles))

        # initialize return dict
        d = {}

        # process each role and add products to the dict
        for role in roles:
            restring = 'roleconfigs?name={0}&fields=name,applicationProfiles.ydProduct'.format(role)
            products, _ = self._get_request(restring, '')
            if products['data']:
                d[products['data'][0]['name']] = [x[u'ydProduct'] for x in products['data'][0]['applicationProfiles']]
            else:
                d[role] = []
        return d






# STUFF THAT PROBABLY SHOULD NOT BE HERE; SPIN OUT ANOTHER CLASS? CUSTOM DATA REQUESTS + PROCESSING

    def gethost(self, hosts):

        """ Composes the API url for a given host based on the datacenter location.

        Variables:

        hosts = A python list of servers.

        Objects:

        Idbhost.url -- Returns the url(s) of the servers for a host or
                       hostlist in a dictionary.
        """
        manager = Manager()
        self.hjson_all = manager.dict()
        self.hjson_configs = manager.dict()
        self.hjson_hwconfig = manager.dict()

        args_list = []
        def thread_func(host, hjson_all, hjson_configs, hjson_hwconfig):
            """
            Threading function for idb.gethost.
            """
            dc = host.split('-')[3]
            self.validatedc(dc)
            url_all = 'allhosts?expand=cluster,cluster.superpod,superpod.datacenter&name=' + host
            url_config = 'allhostconfigs?fields=key,value&host.name=' + host
            url_hwconfig = 'hosts?fields=serialNumber&name=' + host
            host_data = self._get_request(url_all, dc)
            host_config = self._get_request(url_config, dc)
            host_hwconfig = self._get_request(url_hwconfig, dc)
            hjson_all[host] = host_data[0]['data']
            hjson_configs[host] = host_config[0]['data']
            hjson_hwconfig[host] = host_hwconfig[0]['data']

        if isinstance(hosts, list):
            self.hosts = hosts
        else:
            self.hosts = hosts.split(',')
        self.url = {}
        p_list = []
        for host in self.hosts:
            p = Process(target=thread_func, args=(host, self.hjson_all, self.hjson_configs, self.hjson_hwconfig))
            p.start()
            p_list.append(p)
        [process.join() for process in p_list]

        if self.hjson_all:
            self.multi_host()

    def multi_host(self):
        """Handles multiple host to extract data for build_plan.py.

        Objects:

        Idbhost.mlist -- Host list dictionary of parsed json host data.

        """
        self.mlist = {}
        mlist2 = {}
        key_list = ['minorSet', 'majorSet', 'solr_cluster', 'rackNumber']

        for hostname, data in self.hjson_all.items():
            if len(data) > 0:
                clustconfig = data[0]['cluster']['clusterConfigs']
                try:
                    mlist2[hostname] = (item for item in clustconfig if item["key"] ==
                                        "monitor-host").next()
                except StopIteration:
                    mlist2[hostname] = {'value': 'no host'}

                try:
                    self.hjson_hwconfig[hostname][0]['serialNumber']
                except IndexError:
                    self.hjson_hwconfig[hostname] = [{'serialNumber': 'No Serial Number[Unmanaged Host]'}]
                self.mlist[hostname] = {'clusterstatus': data[0]['failOverStatus'],
                                        'opsStatus_Host': data[0]['operationalStatus'],
                                        'opsStatus_Cluster': data[0]['cluster']['operationalStatus'],
                                        'DR': data[0]['cluster']['dr'],
                                        'clusterType': data[0]['cluster']['clusterType'],
                                        'Environment': data[0]['cluster']\
                                        ['environment'], 'superpod': data[0]\
                                        ['cluster']['superpod']['name'],
                                        'clustername': data[0]['cluster']\
                                        ['name'], 'deviceRole': data[0]\
                                        ['deviceRole'], 'monitor-host':\
                                        mlist2[hostname]['value'], 'Serial Number':\
                                        str(self.hjson_hwconfig[hostname][0]['serialNumber'])}
                for conf_data in self.hjson_configs[hostname]:
                    if conf_data['key'] in key_list:
                        self.mlist[hostname][conf_data['key']] = conf_data['value']
            else:
                print("ERROR :- iDB data is missing for host {0}".format(hostname))

    def poddata(self, dc):
        """Retrieves all the Pod information from the specified datacenter.
           Data is seperated by primary and secondary.

        Variables:

        dc = A python list of datacenters

        Objects:

        Idbhost.pjson -- Full pod json data for a specified datacenter.

        """
        if isinstance(dc, list):
            self.dc = dc
        else:
            self.dc = dc.split(',')
        self.pjson = {}
        for dc in self.dc:
            pod_restring = 'clusters?operationalStatus=active&clusterType=POD&superpod.dataCenter.name='\
            + dc
            self.pod_data = self._get_request(pod_restring, dc)
            self.pjson[dc] = self.pod_data[0]['data']
        if self.pjson:
            self.podinfo()

    def podinfo(self):
        """Extracts Primary and Secondary Pod information from specified data-center.

        Objects:

        Idbhost.dcs = Dictionary containing Pod information based on datacenter.

        """

        self.dcs = dict()
        for key, vals in self.pjson.items():
            drgrp = dict()
            drgrp['Secondary'] = ','.join(sorted([val['name'] for val in vals if val['dr']]))
            drgrp['Primary'] = ','.join(sorted([val['name'] for val in vals if not val['dr']]))
            self.dcs[key] = drgrp

    def sp_data(self, dc, pd_status="active", pd_type="pod"):
        """
        Extracts a list of all the active superpods in a Datacenter.

        :param dc: Single datacenter OR a list of datacenters
        :param pd_status: Cluster/POD status, default is active
        :param pd_type: PodType, Cluster/POD
        :return: Nothing, but call another function at the end
        """

        manager = Manager()
        sp_json = manager.dict()
        sp_dict = defaultdict(list)
        self.sp_url = {}
        pod_status = pd_status
        pod_type = pd_type
        dc_list = []

        if isinstance(dc, list):
            dcs = dc
        else:
            dcs = dc.split(',')

        for dc in dcs:
            dc_list.append(dc)

        def thread_sp_data(dc, sp_json):
            sp_restring = 'superpods?fields=name&dataCenter.name=' + dc
            spod_data = self._get_request(sp_restring, dc.upper())
            try:
                sp_json[dc] = spod_data[0]['data']
            except KeyError as e:
                logging.error("Cannot connect to the datacenter %s, %s" % (dc.upper(), e))
        p_list = []
        for dc in dc_list:
            p = Process(target=thread_sp_data, args=(dc, sp_json))
            p.start()
            p_list.append(p)

        [process.join() for process in p_list]

        for key, vals in sp_json.items():
            for val in vals:
                sp_dict[key].append(str(val['name']))
        self.sp_info(dc_list, sp_dict, pod_status, pod_type)

    def sp_info(self, dc, spod_list, pd_status, pd_type):
        """
        Retrieves the Primary and Secondary pods from an given Superpod.

        :param dc: A datacenter OR a list of datacenters
        :param spod_list: List of super_pods in a DataCenter
        :param pd_status: By Default is active
        :param pd_type: PodType, Cluster/POD
        :return:
        """

        manager = Manager()
        mlist_obj = manager.list()
        lst = []
        spods = []
        for spod in spod_list.values():
            spods.extend(spod)

        if isinstance(spods, list):
            spods = spods
        else:
            spods = spods.split(',')

        dcs = [dc[0] for dc in dc]

        def thread_sp_info(sp, dc, obj):
            # Added to support FFX DECOM cluster patching - W-4192330
            data = {'data': []}
            for status in pd_status.split(','):
                spinfo_restring = 'clusters?fields=name,dr,clusterType,operationalStatus&operationalStatus=' \
                              + status + '&clusterType=' + pd_type + '&superpod.dataCenter.name=' + dc + \
                              '&superpod.name=' + sp
                data_iter = self._get_request(spinfo_restring, dc)
                if data_iter[0].get('total') is not None:
                    if data_iter[0]['total'] == 0:
                        logging.debug('No records found for %s', sp)
                    else:
                        data['data'].extend(i for i in data_iter[0]['data'])
                else:
                    logging.error(data_iter[0])
            obj.append((dc, sp, data['data']))

        p_list = []
        for dc, sp in spod_list.items():
            for spod in sp:
                p = Process(target=thread_sp_info, args=(spod, dc, mlist_obj))
                p.start()
                p_list.append(p)
        [process.join() for process in p_list]

        spcl_dict = {}  # Temporary dict to parse data returned from Q.
        for dc, sp, data in mlist_obj:
            if dc not in spcl_dict.keys():
                spcl_dict[dc] = {}
            if sp not in spcl_dict[dc].keys():
                spcl_dict[dc][sp] = []
            spcl_dict[dc][sp].append(data)

        spgrp = {}  # Final dataStructure to return
        for dc in spcl_dict.keys():
            spgrp[dc] = {}
            for sp, data in spcl_dict[dc].items():
                if not spgrp[dc].has_key(sp):
                    spgrp[dc][sp] = []
                dict_len = len(data[0])
                for index in range(0, dict_len):
                    index = int(index)
                    if not data[0][index]['dr']:
                        spgrp[dc][sp].append({'Primary': data[0][index]['name'], 'Operational Status': data[0][index]['operationalStatus']})
                    else:
                        spgrp[dc][sp].append({'Secondary': data[0][index]['name'], 'Operational Status': data[0][index]['operationalStatus']})
        self.spcl_grp = spgrp

    def clusterdata_complete(self, cltype, dc):
        """
        This function returns complete cluster data with cluster type and DC
        :param cltype:
        :param dc:
        :return: cluster data
        """
        if isinstance(dc, list):
            self.dc = dc
        else:
            self.dc = dc.split(',')
        for dc in self.dc:
            pod_restring = 'clusters?operationalStatus=active&clusterType=' + cltype + '&superpod.dataCenter.name=' \
                           + dc
            clusterdata = self._get_request(pod_restring, dc)
        return clusterdata


    def clusterdata(self, dc, idbfilters={"operationalStatus": "active", "clusterType": "POD"}):
        """Retrieves all the Cluster specific information from the specified datacenter
        primary as well as secondary


        Variables:

        dc = A python list of datacenters

        Objects:

        Idbhost.dc -- Datacenter
        Idbhost.cldurl -- Url string for retrieving the Pod data from IDB
        Idbhost.cljson -- Full pod json data for a specified datacenter.

        """
        if isinstance(dc, list):
            self.dc = dc
        else:
            self.dc = dc.split(',')

        filterline = '&'.join(['='.join([key, idbfilters[key]]) for key in idbfilters])
        self.clurl = {}
        self.cljson = {}
        for dc_name in self.dc:
            print(dc_name)
            clust_restring = '/clusters?' + filterline\
            + '&superpod.dataCenter.name=' + dc
            clust_data = self._get_request(clust_restring, dc_name)
            self.cljson[dc] = clust_data['data']

    def _getdc(self):
        hostname_split  = gethostname().split('-')
        if len(hostname_split) == 4:
           dc = hostname_split[3]
        else:
           dc = None


    def checkprod(self,clust_list,dc=None):
        result={}
        clust_list =[clust.lower() for clust in clust_list]
        if dc==None and not self.cidblocal:
            dc = self._getdc()
        if dc == None:
            raise Exception("No production DC supplied")
        self.poddata(dc)
        for record in self.pjson[dc]:
            if record['name'].lower() in clust_list:
                result[record['name']] = not record['dr']
        return result

    def clustinfo(self, dc, clust_list):
        """Reports all the nodes from a specified cluster.

        Variables:
        dc = String value for data-center.
        clustername = String value for Cluster name.

        Objects:

        Idbhost.clustername - Name of the cluster to search.
        Idbhost.clusturl - Url generated to search IDB for cluster information.
        Idbhost.cjson - Json data retrieved from the API.
        Idbhost.clusterhost - List of nodes in the specified cluster (Idbhost.clustername).

        """
        if isinstance(clust_list, list):
            self.clust_list = clust_list
        else:
            self.clust_list = clust_list.split(',')
        self.cjson = {}
        self.clusterhost = {}
        for clustername in self.clust_list:
            # Added pagination support W-4742325
            self.clusterhost[clustername] = []
            counter = 0
            maxrecords = 1000
            while True:
                clustinf_restring = 'allhosts?start=%d&fields=name,failOverStatus,deviceRole&cluster.name=%s' % (counter, clustername)
                clustinfo_data = self._get_request(clustinf_restring, dc)
                if clustername not in self.cjson.keys():
                    self.cjson[clustername] = []
                self.cjson[clustername].append(clustinfo_data[0]['data'])
                total = clustinfo_data[0]['total']
                if total == maxrecords:
                    counter += 1000
                    continue
                else:
                    break
            for records in self.cjson[clustername]:
                for record in records:
                    if "name" in record.keys():
                        self.clusterhost[clustername].append(record["name"])

        #self.clust_summ()

    def clust_summ(self):
        """
        Creates node count summary of the specified cluster.
        """
        if self.cjson:
            self.cluster_summary = {}
            for clustername in self.clust_list:
                for val in self.cjson[clustername]:
                    if val['deviceRole'] in self.cluster_summary:
                        self.cluster_summary[clustername][val['deviceRole']] += 1
                    else:
                        self.cluster_summary[clustername][val['deviceRole']] = 1

    def deviceRoles(self, role):
        """
        Method works with clustinfo function.
        Provides a sorted list of servers based on role(s) for a specified cluster(s)
        """
        if isinstance(role, list):
            self.role = role
        else:
            self.role = role.split(',')
        roletypes = {}
        role_pri = {}
        role_sb = {}
        self.roles_all = {}
        self.roles_primary = {}
        self.roles_standby = {}
        for clustername in self.clust_list:
            for val in self.role:
                roletypes[val] = []
                role_pri[val] = []
                role_sb[val] = []
                for j in self.cjson[clustername]:  # Hack to uncover our list
                    for i in j:
                        if i['deviceRole'] == val:
                            roletypes[val].append(str(i['name']))
                            roletypes[val].sort()
                            if i['failOverStatus'] == "PRIMARY":
                                role_pri[val].append(str(i['name']))
                                role_pri[val].sort()
                            elif i['failOverStatus'] == "STANDBY":
                                role_sb[val].append(str(i['name']))
                                role_sb[val].sort()
            self.roles_all[clustername] = roletypes
            self.roles_primary[clustername + "-Primary"] = role_pri
            self.roles_standby[clustername + "-Standby"] = role_sb
            roletypes = {}
            role_pri = {}
            role_sb = {}

# W-3773536
# T-1747261
    def vip_info(self, dc, clustype):
        """

        :param dc: was,chi or ['was', 'chi']
        :param clustype: CHATTER, POD etc
        :return:  Dictionary containing Key as a Clustername and Values as VIP
        """
        dc = dc
        clustype = clustype
        pjson = {}
        vip = {}

        if type(dc) is list:
            print("list of DC's provided as input.")
        else:
            dc = dc.split(',')
            print("DC argument only takes list, string provided so converting it to a list.")

        for dc in dc:
            clus_restring = 'clusters?operationalStatus=active&clusterType='+ clustype + '&superpod.dataCenter.name=' + dc
            pod_data = self._get_request(clus_restring, dc)
            pjson[dc] = pod_data[0]['data']
            for value in pjson.values():
                for i in value:
                    for j in i.get('clusterConfigs'):
                        if j.get('key') == 'SECURE_APP' and j.get('type') == 'vip':
                            vip[i.get('name')] = j.get('value')
            self.vip_dict = vip
