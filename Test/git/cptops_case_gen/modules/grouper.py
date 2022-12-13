#!/usr/bin/python
#
#
import re
import logging
import sys


class Organizer():
    def __init__(self):
        '''

        :param master:
        :param grouped_data:
        '''
        #self.master = master_data
        #self.grpdata = grouped_data
        #Function run order.
        #self.bundleorg()
        #self.prigroups()
        self.testvalue = "Hello"

    def bundleorg(self):
        '''
        Functions that takes master_json to extract bundle information and sort by bundle.
        :return:
        '''
        self.bundle_groups={}
        for k in self.master_data.iterkeys():
            bundle = self.master_data[k]['Bundle']
            if bundle in self.bundle_groups.keys():
                self.bundle_groups[bundle].append(k)
            else:
                self.bundle_groups[bundle]=[k]
        self.creategroups()
        self.cleangroups()

        return self.pri_groups

    def creategroups(self):
        '''
        Function that looks for the number of keys in bundle_groups and creates the necessary
        priority groups in pri_groups dictionary.
        :return:
        '''
        self.pri_groups={}
        self.pri_groups['Details'] = self.details
        self.pri_groups['Grouping'] = {}
        for i in range(0, len(self.bundle_groups.keys())):
            self.pri_groups['Grouping'][i] = {}
        if self.grouptype == "byrack":
            self.orgbyrack()

    def cleangroups(self):
        '''
        Function to remove dictionary keys with empty values.
        :return:
        '''
        for key in self.pri_groups['Grouping'].keys():
            if not any(self.pri_groups['Grouping'][key].values()):
                self.pri_groups['Grouping'].pop(key)

    def orgbyrack(self):
        '''
        Function to support the prioritizng of byrack grouping.
        :return:
        '''
        bundle_keys = self.bundle_groups.keys()
        bundle_keys.sort()
        keycount = len(self.pri_groups.keys())
        racks = []

        if keycount > 1:
            for bkey in bundle_keys:
                for hostval in self.bundle_groups[bkey]:
                    for rackid in self.byrack['Hostnames'].keys():
                        if hostval in self.byrack['Hostnames'][rackid] and rackid not in racks:
                            racks.append(rackid)
                            self.pri_groups['Grouping'][bundle_keys.index(bkey)].update({rackid: self.byrack['Hostnames'][rackid]})
                            self.byrack['Hostnames'].pop(rackid)
                            break
        else:
            for rackid, hostval in self.byrack['Hostnames'].iteritems():
                self.pri_groups['Grouping'][0].update({rackid: hostval})

class Groups(Organizer):
    def __init__(self, cl_status, ho_status, pod, role, dc, cluster, gsize, grouptype, template, dowork):
        Organizer.__init__(self)
        self.bymajor = {}
        self.byminor = {}
        self.byrack = {}
        self.byzone = {}
        self.byall = {}
        self.allhosts = []
        self.pcldcs = ["yul","yhu", "syd", "cdu", "hio", "ttd"]
        #self.hostnum = re.compile(r'\w*-\w*(\d)-(\d*)-\w*')
        self.hostnum = re.compile(r'(\d.*)')
        self.grouptype = grouptype
        self.details = {"cl_status": cl_status,
                        "ho_status": ho_status,
                        "role": role,
                        "Superpod": pod,
                        "dc": dc,
                        "cluster": cluster,
                        "gsize": gsize,
                        "grouping": self.grouptype,
                        "tempalteid": template,
                        "dowork": dowork
                        }

    def rackorder(self, data):
        self.byrack['Details'] = self.details
        self.byrack['Hostnames'] = {}
        self.master_data = data
        pcl_grp = 0
        for host in self.master_data.iterkeys():
            self.allhosts.append(host)
            try:
                racknum = self.master_data[host]['RackNumber']
            except KeyError as valerr:
                print valerr
                raise
            if host.split("-")[3] in self.pcldcs or racknum == "":
                racknum = 'pcl{}'.format(pcl_grp)
                pcl_grp += 1
            if racknum in self.byrack['Hostnames'].keys():
                self.byrack['Hostnames'][racknum].append(host)
            else:
                self.byrack['Hostnames'][racknum] = [host]

        return self.bundleorg(), self.allhosts

    def majorset(self, data):
        self.bymajor['Details'] = self.details
        self.bymajor['Hostnames'] = {}
        self.master_data = data
        for host in self.master_data.iterkeys():
            self.allhosts.append(host)
            try:
                majorset = self.master_data[host]['Majorset']
            except KeyError as valerr:
                print valerr
                raise
            #regout = self.hostnum.search(host.split("-")[1])
            #regout = self.hostnum.search(host)
            #majorset = int(regout.group())
            if majorset in self.bymajor['Hostnames'].keys():
                self.bymajor['Hostnames'][majorset].append(host)
            else:
                self.bymajor['Hostnames'][majorset] = [host]

        return self.bymajor, self.allhosts

    def zone(self, data):
        self.byzone['Details'] = self.details
        self.byzone['Hostnames'] = {}
        self.master_data = data
        for host in self.master_data.iterkeys():
            self.allhosts.append(host)
            try:
                zone = self.master_data[host]["Zone"]
            except KeyError as valerr:
                print valerr
                raise
            if zone in self.byzone['Hostnames'].keys():
                self.byzone['Hostnames'][zone].append(host)
            else:
                self.byzone['Hostnames'][zone] = [host]

        return self.byzone, self.allhosts

    def minorset(self, data):
        self.byminor['Details'] = self.details
        self.byminor['Hostnames'] = {}
        self.master_data = data
        for host in self.master_data.iterkeys():
            self.allhosts.append(host)
            try:
                minorset = self.master_data[host]['Minorset']
            except KeyError as valerr:
                print valerr
                raise
            #regout = self.hostnum.search(host.split("-")[2])
            #minorset = regout.groups()
            if minorset in self.byminor['Hostnames'].keys():
                self.byminor['Hostnames'][minorset].append(host)
            else:
                self.byminor['Hostnames'][minorset] = [host]

        return self.byminor, self.allhosts

    def all(self, data):
        self.byall['Details'] = self.details
        self.byall['Hostnames'] = {"straight patch":[]}
        self.master_data = data

        for host in self.master_data.iterkeys():
            self.allhosts.append(host)
            self.byall['Hostnames']["straight patch"].append(host)
        return self.byall, self.allhosts

