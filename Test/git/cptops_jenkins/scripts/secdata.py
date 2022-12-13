#!/usr/bin/env python

#W-4546859 - Logic to create cases of hosts provide in CSV file basically a sheet given by security.
# --csv <csv_file_path.csv> --role <optional or comma reprated roles ex:- ffx,search,samcompute>

import requests
import json
from os.path import expanduser
from sys import exit
import csv
import os
from shutil import rmtree
import re
import time

class Secsheet(object):
    """
    # This instance reads a CSV file in "Cloud,Role,FQDN" format, basically a sheet provided by security team.
    # Generates a directory under ~/git/cptops_case_gen/hostlist/security-data/<role_name>/
    # Creates a file putting hosts under role directory with hosts statuses.
    # Creates a consolidated file under ~/git/cptops_case_gen/hostlist/security-data/total_count.txt with example details of all roles below:-
    # Ex:- pbsmatch                 -->    {'2017.11': 1, 'total_count': 1}
    #      samcompute               -->    {'total_count': 311, 'PROVISIONING': 2, '2017.12': 54, 'ACTIVE': 95, '2017.09': 5, '2017.08': 155}
    #      vc                       -->    {'total_count': 1, '2017.09': 1}
    #      ffx                      -->    {'hostNotinDB': 11, 'PROVISIONING': 8, '2017.11': 1571, '2017.12': 2, 'IN_MAINTENANCE': 12, 'total_count': 2548, 'ACTIVE': 5, 'HW_PROVISIONING': 40, '2017.08': 875, 'DECOM': 15, '2017.09': 9}
    # Creates cases on based on host status provided by user, based on that a satatus file will taken as a hostlist from the appropriate role Ex:- decom.txt.
    """

    def get_json(self, filepath):
        """
        # Takes a .json file and provides a dictionary(hash table).

        :param filepath:
        :return:
        """

        try:
            with open(filepath) as data_file:
                data = json.load(data_file)
        except Exception as e:
            print("Ensure presence of path " + filepath)
            exit(1)
        return data


    def get_valid_version(self):
        """
        # return's  a valid version file as a hash table(dictionary).
        :return:
        """
        home = expanduser("~")
        filepath = "/git/cptops_validation_tools/includes/valid_versions.json"
        path = home + filepath
        return self.get_json(path)


    def get_case_preset(self):
        """
        # resturn's a cases preset file as a hash table.

        :param preset_file:
        :return:
        """
        home = expanduser("~")
        filepath = "/git/cptops_jenkins/scripts/case_presets.json"
        path = home + filepath
        return self.get_json(path)


    def pod_data(self):
        """
        # Returns a custom pod data to be used in future.
        # Currently this is not used, reserved for future.

        :return:
        """
        preset = self.get_case_preset()
        presetdict = {}

        for type in preset:
            for data in preset.get(type):
                presetdict[preset.get(type).get(data).get('ROLE')] = {'GROUPSIZE': preset.get(type).get(data).get('GROUPSIZE'),
                                                                      'TEMPLATEID': preset.get(type).get(data).get('TEMPLATEID')}

        return presetdict


    def read_csv_dict_out(self, file):
        """
        # Read user provided security sheet and returns a hash table whare key is role and value is list of hosts relevent to that role.

        :param file:
        :return:
        """
        data = {}
        rolelist = []
        try:
            with open(file, 'rU') as fd:
                reader = csv.reader(fd)
                for r in reader:
                    rolelist.append(r[1])
            rolelist = list(set(rolelist[1:]))
            for d in rolelist:
                data[d] = list()

            with open(file, 'rU') as fd1:
                reader = csv.reader(fd1)
                [(row, role, data.setdefault(role,[]).append(row[2])) for row in reader for role in rolelist if role in row[1]]
            return data
        except Exception as e:
            print(e)
            print("\nERROR: Unable to read {0} file.\n".format(file))
            exit(1)


    def readAllHosts(self):
        """
        # Download a ALL Host CSV file from database and returns a custom nested hash table ex:- {role:{host:{keys:values}}}

        :return:
        """
        rolelist = []
        data = {}
        retdata = {}
        url = "https://ops0-cpt1-1-xrd.eng.sfdc.net:9876/api/v1/csv/all-hosts"

        try:
            if not os.path.isfile('all.csv'):
                print("DB data does not exist, fetching now...\n")
                response = requests.get(url, verify=False)
                if response.status_code == 200:
                    with open('all.csv', 'w') as cs:
                        cs.writelines(response.content.decode('utf-8'))

            if (time.time() - (os.path.getmtime('all.csv')) > 600):
                print("DB data is more than 10 min old, fetching new one...\n")
                response = requests.get(url, verify=False)
                if response.status_code == 200:
                    with open('all.csv', 'w') as cs:
                        cs.writelines(response.content.decode('utf-8'))

            else:
                print("DB data is not more than 10 min old, skipping download...\n")

            with open('all.csv', 'rU') as f:
                resader = csv.reader(f)
                for r in resader:
                    rolelist.append(r[22])

            rolelist = list(set(rolelist))
            rolelist = list(set(rolelist[1:]))

            for d in rolelist:
                data[d] = []

            with open('all.csv', 'rU') as fd1:
                reader = csv.reader(fd1)
                [(row, role, data.setdefault(role, []).append({row[0]: {'hostStatus': row[1],
                                                               'hostOs': row[2],
                                                               'hostKernel': row[3],
                                                               'hostRelease': row[4],
                                                               'hostRma': row[5],
                                                               'clusterName': row[9],
                                                               'clusterStatus': row[10],
                                                               'clusterDr': row[13],
                                                               'spName': row[14],
                                                               'dcName': row[15],
                                                               'dcProd': row[17],
                                                               'roleOnboarded': row[23]
                                                               }})) for row in reader for role in rolelist if role in row[22]]

            for ro in data.keys():
                d = {}
                for hl in data.get(ro):
                    d.update(hl)
                retdata.setdefault(ro, d)
        except Exception as e:
            print(e)
        return retdata


    def host_filter(self, bundle, file, role=None):
        """
        # returns a depth hash table ex:- {role:{host:{states:[hosts]}}}

        :param bundle:
        :param file:
        :return:
        """
        requests.packages.urllib3.disable_warnings()  #Supress https insucure SSL cert warning, only works with python2, use urllib3 with python3.
        hostdict = self.read_csv_dict_out(file)
        json_data = self.get_valid_version().get('CENTOS')
        all_role = hostdict.keys()
        filterhostdict = {}
        found = []

        if role != None:
            all_role = role.split(',')

        for role in all_role:
            print("\nProcessing Role {0}...".format(role))
            filterdict = {}
            try:
                hosts = ",".join(hostdict.get(role)).replace(".ops.sfdc.net", "")
                hosts = list(set(hosts.split(',')))

                try:
                    data = self.readAllHosts()
                    hlist = data.get(role).keys()
                    for host in hosts:
                        hdata = data.get(role).get(host)

                        if host in hlist:
                            found.append(host)
                            if hdata.get('hostOs'):
                                hostos = hdata.get('hostOs')
                            else:
                                hostos = '6'

                            jkernel = json_data.get(hostos).get(bundle).get('kernel')
                            if bundle < hdata.get('hostRelease'):
                                filterdict.setdefault(hdata.get('hostRelease'), []).append(host)
                            elif (bundle not in hdata.get('hostRelease')) and (jkernel not in hdata.get('hostKernel')):
                                if (hdata.get('clusterStatus') == 'ACTIVE') and (hdata.get('hostStatus') == 'ACTIVE'):
                                    filterdict.setdefault('ACTIVE', []).append(host)
                                elif (hdata.get('clusterStatus') == 'DECOM') or (hdata.get('hostStatus') == 'DECOM'):
                                    filterdict.setdefault('DECOM', []).append(host)
                                elif (hdata.get('clusterStatus') == 'IN_MAINTENANCE') or (hdata.get('hostStatus') == 'IN_MAINTENANCE'):
                                    filterdict.setdefault('IN_MAINTENANCE', []).append(host)
                                elif (hdata.get('clusterStatus') == 'HW_PROVISIONING') or (hdata.get('hostStatus') == 'HW_PROVISIONING'):
                                    filterdict.setdefault('HW_PROVISIONING', []).append(host)
                                elif (hdata.get('clusterStatus') == 'PROVISIONING') or (hdata.get('hostStatus') == 'PROVISIONING'):
                                    filterdict.setdefault('PROVISIONING', []).append(host)
                                elif (hdata.get('clusterStatus') == 'PRE_PRODUCTION') or (hdata.get('hostStatus') == 'PRE_PRODUCTION'):
                                    filterdict.setdefault('PRE_PRODUCTION', []).append(host)
                                else:
                                    filterdict.setdefault('UNKNOWN', []).append(host)
                            else:
                                filterdict.setdefault(bundle, []).append(host)
                        else:
                            filterdict.setdefault('hostNotinDB', []).append(host)
                        filterhostdict[role] = filterdict


                except Exception as e:
                        print(e)
            except:
                print("Role {0} not found in CSV.".format(role))
        return filterhostdict


    def total_count(self, data):
        """
        # returns a hash table with total count.

        :param bundle:
        :param file:
        :return:
        """
        datadict = data
        count = {}

        for role in datadict.keys():
            statecount = {}
            for state in datadict.get(role).keys():
                if len(datadict.get(role).get(state)) != 0:
                    statecount[state] = len(datadict.get(role).get(state))
            count[role] = statecount
            count.get(role)['total_count'] = sum(count.get(role).values())
        print("\nTotal Role Wise Count.")
        print("%s\n" % count)
        return count


    def save_to_file(self, bundle, file, role=None):
        """
        # save data to file.

        :param bundle:
        :param file:
        :return:
        """
        cwd = os.path.expanduser("~")
        datadir = "/git/cptops_case_gen/hostlists/security_data"
        path = cwd + datadir

        if os.path.isdir(path):
            print('Data direcectory exists {0}, deleting...\n'.format(path))
            if os.listdir(path):
                rmtree(path)
            else:
                os.rmdir(path)

        if not os.path.isdir(path):
            print("\nCreating fresh data directory {0}\n".format(path))
            os.mkdir(path)
        print("Reading CSV format 'Cloud,Role,FQDN' file {0} ".format(file))

        secdata = self.host_filter(bundle, file, role)
        count = self.total_count(secdata)
        countpath = path + "/total_count.txt"

        with open(countpath, 'a') as cf:
            for role in count:
                cf.write("%s\t\t\t --> \t%s\n" % (role, count.get(role)))

        for role in secdata.keys():
            rolepath = path+ "/" +role
            os.mkdir(rolepath)
            for state in secdata.get(role).keys():
                if len(secdata.get(role).get(state)) != 0:
                    filepath = rolepath + "/" + state + ".txt"
                    with open(filepath.lower(), 'a') as f:
                        for host in secdata.get(role).get(state):
                            f.write("%s\n" % host)
        return secdata


    def gen_plan(self, bundle, csv, status, role=None):
        """
        # return the preset to generate the cases.

        :param bundle:
        :param csv:
        :param status:
        :param role:
        :return:
        """
        status = status.upper().split(',')
        print("\nGenerating Cases for role %s with status %s\n" % ('ALL' if not role else role.upper(), ','.join(status)))
        datadir = "security_data"
        preset = {}

        data = self.save_to_file(bundle, csv, role)
        if role:
            role = role.split(',')
        else:
            role = data.keys()

        for r in role:
            for state in status:
                if re.search(r'DECOM|HW_PROVISIONING|PRE_PRODUCTION|PROVISIONING', state):
                    if r == 'ffx':
                        groupsize = "5"
                        templateid = "ffx"
                    else:
                        groupsize = "25"
                        templateid = "straight-patch"

                try:
                    hosts = data.get(r).get(state)
                    try:
                        if len(hosts) != 0:
                            preset[r + "_" + state + "_prod"] = {
                                "PROD": {"PODGROUP": datadir + "/" + r + "/" + state.lower() + ".txt",
                                         "TEMPLATEID": templateid,
                                         "GROUPSIZE": groupsize,
                                         "TAGGROUPS": 0,
                                         "INFRA": "Supporting Infrastructure",
                                         "ROLE": r,
                                         "CASETYPE": "hostlist"}}
                    except:
                        print("State {0} not fount in role {1}".format(state, r))
                except Exception:
                    print("Role {0} not found in CSV.\n".format(r))

        return preset,data
