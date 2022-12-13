## Basic usage
  
  Importing the module:
  ```python
  from idbhost import Idbhost
  ```
  
  Instantiating Idbhost:
  ```python
  idb = Idbhost()
  ```
  
  The default search path is the "local" (if in a datacenter; PRD otherwise) iDB. You can specify the iDB/location during instantiation:
  ```python
  idb = Idbhost('chi')
  ```
  
  Requests for local resources go to iDB. Requests for resources from another DC are automatically directed to the appropriate ciDB endpoint.
  
## Authentication
  
  This module can authenticate to iDB/ciDB in the following ways:
  
  1. **Client certificates** - You need a client certificate and key to use this method.
   * path to client cert: ~/.cptops/auth/client.pem
   * path to client key: ~/.cptops/auth/client.key
   * The above cert and key is only for cpt team, but you can pass your own cert and key to Idbhost:
   ```
    idb = Idbhost(site='frf', user=None, pswd=None, path_pem='/home/sbhathej/auth/client.pem', path_key='/home/sbhathej/auth/client.key')
   ```
  
  2. **Kerberos creds passed during instantiation** - If you are using Katzmeow or any other program which already has your Kerberos credentials you can pass them to Idbhost:
  ```python
  idb = Idbhost(site='frf', user='myusername', pswd='s00p3rSecretPass')
  ```
  
  3. **Kerberos creds taken from stdin** - If the client cert and key are not detected and no credentials are passed in, Idbhost will present a prompt on stdin for the username and password.
  ```python
  >>> idb = Idbhost()
  DEBUG:root:parsing site out of: hostname-715abc2
  DEBUG:root:using site: prd
  DEBUG:root:client cert and key not found
  DEBUG:root:no creds were passed in, requesting them on stdin
  Username: myusername
  Password:
  ```
  
  All three methods will also need the internal root CA verify the server certificate. This comes included in the repo under the auth/ directory. The module checks auth/ and ~/.cptops/auth/ for the internal_ca.pem file.
  
## Examples
  
  Information for a single host or multiple hosts.
  ```python
  idb.gethost('na8-proxy1-1-chi')
  idb.gethost(['hbase1a-dnds9-8-frf','na8-proxy1-1-chi'])
  ```
  
  Host information can be retrieved from the mlist variable as a dictionary.
  ```python
  >>> pp.pprint(idb.mlist)
  {'hbase1a-dnds9-8-frf': {'Environment': u'PRODUCTION',
                         'clustername': u'HBASE1A',
                         'clusterstatus': u'PRIMARY',
                         'deviceRole': u'dnds',
                         'monitor-host': u'ops0-monitor-frf.ops.sfdc.net',
                         'opsStatus_Cluster': u'ACTIVE',
                         'opsStatus_Host': u'ACTIVE',
                         'superpod': u'SP1'},
   'na8-proxy1-1-chi': {'Environment': u'PRODUCTION',
                      'clustername': u'NA8_DECOMMISSIONED',
                      'clusterstatus': u'PRIMARY',
                      'deviceRole': u'proxy',
                      'monitor-host': u'na8-monitor-chi.ops.sfdc.net',
                      'opsStatus_Cluster': u'DECOM',
                      'opsStatus_Host': u'ACTIVE',
                      'superpod': u'SP1'}}
  ```
  
  Example of extracting data values from mlist.
  ```python
  >>> from idbhost import Idbhost
  >>> idb=Idbhost()
  >>> hosts=['na8-proxy1-1-chi', 'na5-proxy1-1-was']
  >>> idb.gethost(hosts)
  >>> for i in hosts:
  ...   print "%s ==" % i, idb.mlist[i]['monitor-host']
  ...
  na8-proxy1-1-chi == na8-monitor-chi.ops.sfdc.net
  na5-proxy1-1-was == na5-monitor-was.ops.sfdc.net
  ```
  
  Retrieval of all pods in a DC. Results are stored as a dictionary in the dcs variable.
  ```python
  >>> idb.poddata('frf')
  >>> print idb.dcs
  {'frf': {'Primary': u'CS82,CS83,CS84,CS85,EU4,EU6,EU7,EU9', 'Secondary': u'CS81,CS86,CS87,CS88,CS89,EU1,EU11,EU2,EU3'}}
  ```
  
  Retrieval of all hosts within a datacenter cluster. Results are stored as a dictionary in the clusterhost variable.
  ```python
  >>> idb.clustinfo('chi', 'cs14')
  >>> print idb.clusterhost
  {'cs14': ['cs14-cbatch1-1-chi', 'cs14-dapp1-1-chi', ..., 'cs14-db1-4-chi']}
  >>> idb.clustinfo('ukb', 'opsedns')
  >>> print idb.clusterhost
  {'opsedns': ['ops0-edns1-1-ukb', 'ops0-edns2-2-ukb', 'ops0-edns1-2-ukb', 'ops0-edns2-1-ukb']}
  ```
  
  Retrieval of all hosts in given clusters with given roles. Results are stored as a dict of a dict of a list in the roles_all variable.
  ```python
  >>> clust_list = ['cs88', 'eu11']
  >>> dc = 'par'
  >>> idb.clustinfo(dc, clust_list)
  >>> role = ['search', 'mgmt_hub']
  >>> idb.deviceRoles(role)
  >>> pprint(idb.roles_all)
  {'cs88': {'mgmt_hub': ['cs88-hub1-1-par', 'cs88-hub2-1-par'],
            'search': ['cs88-search21-1-par',
                       'cs88-search21-2-par',
                       ...
                       'cs88-search43-4-par',
                       'cs88-search43-5-par']},
   'eu11': {'mgmt_hub': ['eu11-hub1-1-par', 'eu11-hub2-1-par'],
            'search': ['eu11-search21-1-par',
                       'eu11-search21-2-par',
                       ...
                       'eu11-search43-4-par',
                       'eu11-search43-5-par']}}
  ```
  
  Roles are also divided by primary and standby.
  ```python
  >>> idb.deviceRoles('mgmt_hub')
  >>> pprint(idb.roles_primary)
  {'cs88-Primary': {'mgmt_hub': ['cs88-hub1-1-par']},
   'eu11-Primary': {'mgmt_hub': ['eu11-hub1-1-par']}}
  >>> pprint(idb.roles_standby)
  {'cs88-Standby': {'mgmt_hub': ['cs88-hub2-1-par']},
   'eu11-Standby': {'mgmt_hub': ['eu11-hub2-1-par']}}
  ```