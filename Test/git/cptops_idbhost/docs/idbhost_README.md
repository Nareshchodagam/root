  Idbhost
=============================

  DESCRIPTION
      The purpose of this module is to retreive specific information related to
      Compute Deploy needs to feed into other programs (Template generation, nagios_monitor).

  Instructions

  How to import -
      from idbhost import Idbhost

  Make an alias of the initial call to the module. You can also set the search path (i.e IDB server) to
  make API calls.
      idb=Idbhost() or
  To make API calls in chi IDB server.
      idb=Idbhost('chi')

  Methods defined here:

  __init__(self, search='cidb')

  clustinfo(self, dc, clustername)
      Reports all the nodes from a specified cluster.

      Variables:
      dc = String value for data-center.
      clustername = String value for Cluster name.

      Objects:

      Idbhost.clustername - Name of the cluster to search.
      Idbhost.clusturl - Url generated to search IDB for cluster information.
      Idbhost.cjson - Json data retreived from the API.
      Idbhost.clusterhost - List of nodes in the specified cluster (Idbhost.clustername).

  gethost(self, hosts)
      Composes the API url for a given host based on the datacenter location.

      Variables:

      hosts = A python list of servers.

      Objects:

      Idbhost.url -- Returns the url(s) of the servers for a host or
                     hostlist in a dictionary.

  hostinfo(self)
      Retrieves the host data in json format for a given host or hosts list.

      Objects:

      Idbhost.hjson -- Contains the json data for a host or hosts list.

  multi_host(self)
      Handles multiple host to extract data for build_plan.py.

      Objects:

      Idbhost.mlist -- Host list dictionary of parsed json host data.

  poddata(self, dc)
      Retrives all the Pod information from the specified datacenter.
         Data is seperated by primary and secondary.

      Variables:

      dc = A python list of datacenters

      Objects:

      Idbhost.dc -- Datacenter
      Idbhost.podurl -- Url string for retreiving the Pod data from IDB
      Idbhost.pjson -- Full pod json data for a specified datacenter.

  podinfo(self)
      Extracts Primary and Secondary Pod information from specified data-center.

      Objects:

      Idbhost.dcs = Dictionary containing Pod information based on datacenter.