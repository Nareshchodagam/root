#!/usr/bin/python
#
# Python Unit Test for idbhost module.
#
#
import unittest
import sys
from idbhost import Idbhost



""" Below is a list of the test that are performed against that Idbhost module.
"""
global testDB
testDB = {'asg': "https://inventorydb1-0-asg.data.sfdc.net/api/1.03",
                  'chi': "https://inventorydb1-0-chi.data.sfdc.net/api/1.03",
                  'chx': "https://inventorydb1-0-chx.data.sfdc.net/api/1.03",
                  'lon': "https://inventorydb1-0-lon.data.sfdc.net/api/1.03",
                  'sfm': "https://inventorydb1-0-sfm.data.sfdc.net/api/1.03",
                  'sjl': "https://inventorydb1-0-sjl.data.sfdc.net/api/1.03",
                  'tyo': "https://inventorydb1-0-tyo.data.sfdc.net/api/1.03",
                  'was': "https://inventorydb1-0-was.data.sfdc.net/api/1.03",
                  'wax': "https://inventorydb1-0-wax.data.sfdc.net/api/1.03",
                  'dfw': "https://inventorydb1-0-dfw.data.sfdc.net/api/1.03",
                  'phx': "https://inventorydb1-0-phx.data.sfdc.net/api/1.03",
                  'cidb': "https://cidb1-0-sfm.data.sfdc.net/cidb-api/1.03"
                  }


class IdbTest(unittest.TestCase):

    def testIntro(self):
        search = "chx"
        if search:
            print "\nTest that search value is valid ..."
            self.assertTrue(search in testDB,"Search is not valid.")
            idb=Idbhost(search)
            print "Test that search url matches expected result ..."
            self.assertEqual(testDB[search], idb.iDBurl[search])

        idb=Idbhost()
        print "Test that cidblocal parameter is set to True ..."
        self.assertTrue(idb.cidblocal, "CIDB seach not set to true by default.")
        print "Test that cidb url matches expected result ..."
        self.assertEqual(testDB['cidb'], idb.iDBurl['cidb'])

    def testGetHost(self):
        host = 'blitz2sr2-release1-1-sfm'
        hosts = ['blitz2sr2-release1-1-sfm', 'blaze1cs2-app2-1-sfm']

        # Testing gethost action from a single host.
        idb=Idbhost('sfm')
        idb.gethost(host)
        print "\nTest that single string is converted to list ..."

        #self.assertIsinstance(idb.hosts, list, "Host not converted to list format")
        print "Test that host url matches the expected result ..."
        self.assertEqual(testDB['sfm'] + '/allhosts?name=' + host + '&expand=cluster,cluster.superpod,superpod.datacenter,deviceRole', idb.url[host])

        # Testing gethost action for multiple host.
        idb=Idbhost('sfm')
        idb.gethost(hosts)
        print "Test that multiple host urls all match expected results ..."
        for host in hosts:
            self.assertEqual( testDB['sfm'] + '/allhosts?name=' + host + '&expand=cluster,cluster.superpod,superpod.datacenter,deviceRole', idb.url[host])

    def testBadHost(self):
        hosts = ['blitz2sr2-release1-1-sfm', 'blitz-release5-1-sfm']
        idb=Idbhost('sfm')
        idb.gethost(hosts)
        #Testing if badhost is detected and captured.
        print "\nTest that bad host is detected and captured ..."
        self.assertTrue('blitz-release5-1-sfm' in idb.failedhost, "Failed list not returning correct value")
        print "Test that good host is not detected as a failure ..."
        self.assertFalse('blitz2sr2-release1-1-sfm' in idb.failedhost, "Failed list had incorrect value.")

    def testMultiList(self):
        hosts = ['na25-proxy1-1-chi', 'eu4-proxy1-1-lon']
        idb=Idbhost()
        idb.gethost(hosts)
        mlistTest={}
        mlistTest={'eu4-proxy1-1-lon': {'opsStatus_Cluster': u'ACTIVE', 'Environment': u'PRODUCTION', 'deviceRole': u'proxy', 'monitor-host': u'eu4-monitor-lon.ops.sfdc.net', 'superpod': u'SP9', 'opsStatus_Host': u'ACTIVE', 'clustername': u'EU4', 'clusterstatus': u'PRIMARY'},
                   'na25-proxy1-1-chi': {'opsStatus_Cluster': u'ACTIVE', 'Environment': u'PRODUCTION', 'deviceRole': u'proxy', 'monitor-host': u'na25-monitor-chi.ops.sfdc.net', 'superpod': u'SP4', 'opsStatus_Host': u'ACTIVE', 'clustername': u'NA25', 'clusterstatus': u'PRIMARY'}}
        
        #Testing mlist has the expected keys. Test if monitor-host capture is working as expected.
        print "\nTest that mlist reports all the expected keys ..."
        self.assertDictContainsSubset(mlistTest, idb.mlist, "Mlist not reporting expected values.")
        print "Test that monitor-host is reporting accurately ..."
        self.assertEqual(mlistTest['eu4-proxy1-1-lon']['monitor-host'], 'eu4-monitor-lon.ops.sfdc.net', "Values does not equal no host.")
        self.assertNotEqual(mlistTest['na25-proxy1-1-chi']['superpod'],'SP3', "Value is not reporting accurately.")

    def testPodTest(self):
        dc = 'dfw'
        #This check may fail as the primary list changes frequently. 
        prim_list = 'CS50,CS51,NA32,NA7,NA8'
        idb=Idbhost()
        idb.poddata(dc)
        
        print "\nValidate dictionary has Primary and Secondary keys ..."
        for val in 'Primary','Secondary':
            self.assertTrue(val in idb.dcs[dc], "Key is not present in dictionary ...")

        #Test if Primary key report expected values.
        self.assertEqual(prim_list, idb.dcs[dc]['Primary'], "Primary list values are not the expected results")
    
    def testRoleList(self):
        dc = 'chi'
        test_list = ['cs14-ffx1-3-chi', 'cs14-ffx1-4-chi', 'cs14-ffx1-5-chi', 'cs14-ffx2-3-chi', 'cs14-ffx2-4-chi', 'cs14-ffx2-5-chi']
        role = 'ffx'
        clust_list = ['cs14', 'na25']
        test_clustlist = ['na25-ffx1-1-chi', 'na25-db1-1-chi', 'na25-app2-1-chi' ]
        
        idb=Idbhost()
        idb.clustinfo('chi', clust_list)
        idb.deviceRoles(role)
        
        #Test test_clustlist in idb.clusterhost file
        print "\nTesting idb.clusterhost contents for expected results....."
        for val in test_clustlist:
            self.assertTrue(val in idb.clusterhost['na25'], "idb.clusterhost is missing host entries")
            
        #Test test_list in idb.roles_all file
        print "Testing idb.roles_dict for sorted list of expected results....."
        self.assertTrue(test_list == idb.roles_all['cs14'][role])
        
    def testidbquery(self):
        idb=Idbhost()
        myresults=idb.idbquery(['chi','was'],'allhosts?',['name','cluster.name','cluster.superpod.name'],{'cluster.superpod.name' : 'SP1', 'cluster.name' : 'NA9'} ) 
        
        for key in myresults:
            self.assertTrue(key in 'chi','was', "should return entry for each dc")

