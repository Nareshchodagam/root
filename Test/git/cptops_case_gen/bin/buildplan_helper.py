#!/usr/bin/python
#
#
from common import Common
import json
import urllib2
import sys
import os
import logging
import itertools
import re
#from build_plan import supportedfields
common = Common()
import sys
reload(sys)

class Buildplan_helper:
    
    
    def __init__(self, resource, fields, cidblocal, usehostlist=False):
        """
           get = any idb "allhosts?"  
        """
    
        self._product_role_map = {
           'chatterbox' : ['sshare','prsn'],
           'chatternow' : ['chan','dstore','msg','prsn'],
           'mandm-hub' : ['mgmt_hub'],
           'mq-broker' : ['mq'],
           #'onboarding' : [ 'app' ],
           'acs' : [ 'acs' ],
           'searchserver' : [ 'search' ],
           'sfdc-base' : ['ffx','cbatch','app','dapp',\
               { 'ignored_process_names' : ['redis-server','memcached'] }\
            ]
        }
        
        self.cidblocal = cidblocal
        self.idb_resource = resource
        self.fields = fields
        self.cache={}
        
        #one list with all supported fields, majorest and minorset are implied so must be added here for validation
        self.fieldcheck = self.fields.keys() + ['majorset','minorset','datacenter']
        self.usehostlist=usehostlist
        #setting as separate list to preserve order
        self._suffixlist = ['_dr_standby','_dr','_standby','']
        self._templatesuffix= {
                 
                    (True, 'STANDBY') : self._suffixlist[0],
                    (True, 'PRIMARY') : self._suffixlist[1],
                    (False, 'STANDBY') : self._suffixlist[2],
                    (False, 'PRIMARY') : self._suffixlist[3]
                            
                }
        
    
    def gen_request(self,reststring, dc, cidblocal=True, debug=False):
        """
          build request for idb
        """
        
        # Build the API URL
        dc = dc.lower()
        if cidblocal:
            # CIDB URL is slightly different, so it needs to be cut up and
            # reassembled.
            url =  "https://cidb1-0-sfm.data.sfdc.net/cidb-api/%s/1.03/" % dc    + reststring              
            url = os.popen('java -jar ' + common.cidb_jar_path + '/cidb-security-client-0.0.7.jar ' + common.cidb_jar_path + '/keyrepo "' + url + '"').read()
        else:
            url = "https://inventorydb1-0-%s.data.sfdc.net/api/1.03/" % dc + reststring

        print url
        logging.debug(url)

        # Send the request.
        r = urllib2.urlopen(url)
        # use the data.
        data = json.load(r)
        if debug:
            logging.debug(data)
            logging.debug(data['total'])
        if data['total'] == 1000:
            raise Exception('idb record limit of 1000, you may be missing records')
        print str(data['total']) + ' records returned'
        print
        return data
    
        
    def cacher(self,current_obj, arglist):
    # loop through fields from left to right caching ibased on JacksonId if they point to a json object returning if they are cached
        for arg in arglist:
            if type(current_obj[arg]) is unicode:
                current_obj = self.cache[current_obj[arg]]
            else:
                current_obj = current_obj[arg]
            self.cache[current_obj['@' + arg + 'JacksonId']] = current_obj
        
        return current_obj
        
    def check_cache(self,current_obj,argstring):
        """
            cache and return parent values or return current row values
        """
  
        arglist=argstring.split('.')

        try:
            if len(arglist) > 1:
                return self.cacher(current_obj,arglist[:-1])[arglist[-1]]
            else:    
                return current_obj[arglist[-1]]
        except:
            logging.debug (  "Field" + argstring + ' does not exist in row: ' + str(current_obj) )
            raise
        
        
    def row_test_regex(self,row,regexfilters):
        """
          test a row for regexfilters checking against corresponding idb field
          evaluate
        """
    
        retval=True
        for key in self.fields:
            if key in regexfilters and not re.match(regexfilters[key], row[key]):     
                logging.debug( 'regex ' + regexfilters[key] + ' does not match ' + key + ':' + row[key] )
                retval = retval and False
        
        return retval
    
    
    
    
    def apply_regexfilters(self,regexfilters,unfilteredlist):
        """
        regexfilters : dict of key value pairs containing regexes to be applied to each of the fields.values()  
        """
        results = []
        
	for key in regexfilters:
	    logging.debug( "regexfilter: " + key + ", supportedfields: " + ','.join(self.fields.keys()) )
            assert key in self.fields.keys(), "regexfilter  is not a supported field "
            
        for row in unfilteredlist:
            if self.row_test_regex(row,regexfilters):
                results.append( row )
            
        return results
        
        
        
    def get_uri_list(self, idbfilters):
        """
        construct list of reststrings  using dict idbfilters
        """
    
        requestlist = []
        results=[]
        fields = self.fields
        assert len(fields) > 0, "Error: No fields specified"
        assert len(idbfilters.keys()) > 0, "Error no filters specified" 
        
        #convert each to list if string assigned
        for key,val in idbfilters.items():
            idbfilters[key] = [val] if not isinstance(val,list) else val
            
        
        for key in idbfilters:
            assert (isinstance(idbfilters[key], list) and len(idbfilters[key][0]) > 0), "idbfilter " + key + " must have at least one value"
            requestlist.append([(key,val) for val in idbfilters[key] ])
        myfields=[]
        for val in fields.values():
	    if type(val) is list:
	        myfields.append( val[0] )
	    else:
		myfields.append( val )
            
        requestlist.append([('fields', ','.join(myfields))] )
      
        for clauses in itertools.product(*requestlist):
            reststring = self.idb_resource + '&'.join(['='.join(clause) for clause in clauses ])
            results.append(reststring)
    
        logging.debug( results )
        return results
        
    def get_configs_fields(self, jsonresult, configdetails ):
        configlookup = configdetails[1]
        assert len(configlookup) == 1
        allconfigs = self.check_cache(jsonresult,configdetails[0])
        retval = None
        for mykey in configlookup:
	    myvalue = configlookup[mykey]
        for config in allconfigs:
	    if config[mykey] == myvalue:
	        retval = config['value']
        assert not retval is None
        return retval

    def _lookup_product(self,jsonresult,rolename):
        prodlist =[] 
        ignore=""
        for prod in self._product_role_map:
           prodlist_temp = self._product_role_map[prod]
           if rolename in prodlist_temp:
              prodlist.append( prod )
           if prod == 'sfdc-base':
              ignorelist = prodlist_temp[-1]['ignored_process_names']
        if len(prodlist) > 0:
            return (",".join(prodlist), '-ignored_process_names ' + ','.join(ignorelist) + ' ')
        else:
            return "", ""

    
    def format_field(self,jsonresult, row, formatfield):
        retval=False
        if formatfield == 'ignored_process_names_rr_cmd':
           return True
        if type(self.fields[formatfield]) is list:
	   return True
        tempfield = self.check_cache(jsonresult,self.fields[formatfield])
        if formatfield  == 'sitelocation':
           row[formatfield] =  U'Secondary' if tempfield else U'Primary'
           retval = True
        if formatfield  == 'product_rrcmd':
           row[formatfield], row['ignored_process_names_rr_cmd'] = self._lookup_product(jsonresult,tempfield)
           retval = True 
        if formatfield  == 'drnostart_rrcmd':
           row[formatfield] =  U'-drnostart ' if tempfield else ""
           retval = True 
        return retval
           
   
    def get_hosts_from_idbquery(self,datacenters,idbfilters,regexfilters):
        """
           datacenters: tuple of 3 character datacenter ids eg : was,chi,tyo ..
           idbfilters : dict of key = valid target fieldname, value = tuple of values  
           
        """
        assert len(datacenters) > 0, "Error no datacenters specified" 
        
        results = []
        reststring_list = self.get_uri_list(idbfilters)
        for dc in datacenters:    
            for reststring in reststring_list:
                if not self.usehostlist:
                    current=self.gen_request(reststring,dc)
                else:
                    if reststring.split('=')[1].split('&')[0].split('-')[3]==dc:
                        current=self.gen_request(reststring,dc)
                    else:
                        continue       
                if current['total'] > 0:
                    for jsonresult in current['data']:
                        logging.debug( jsonresult )
                        row={}
                        row['datacenter']=dc
                        for key in self.fields:
			    if self.format_field(jsonresult,row, key): #see if there are any special format fields and do them first	
                                continue 
			    if not type(self.fields[key]) is list:
                                row[key] = self.check_cache(jsonresult,self.fields[key])
                            else:
                                row[key] = self.get_configs_fields(jsonresult,self.fields[key])
                            results.append(row)
                else:
                    logging.debug( 'no values for: ' + reststring )
        return self.apply_regexfilters(regexfilters, results)
    

    def set_default_fields(self,res):
        """
         apply grouping defaults majorset, minorset, datacenter, superpod, rolename taken from hostname
         this allows up to do majorset minorset grouping and can be applied to hosts where we have no idbdata
         
        """
        newres=[]
        print res
        for row in res:
            # minorset never present so put it i
            row['minorset'] = row['hostname'].split('-')[2]
            row['majorset'] = ''.join([s for s in row['hostname'].split('-')[1] if s.isdigit()])
        
        
            if 'superpod' not in row.keys():
                row['superpod'] = 'none'
            if 'datacenter' not in row.keys():
                row['datacenter'] = row['hostname'].split('-')[3]
            if 'role' not in row.keys():
                row['role'] = ''.join([s for s in row['hostname'].split('-')[1] if not s.isdigit()])
            if 'cluster' not in row.keys():
                row['cluster'] =  row['hostname'].split('-')[0] 
                
            #all other fields default to empth
            for field in self.fieldcheck:
                if field not in row.keys():
                    row[field] = ''
            
            newres.append(row)
        
        
        return newres
    
    
                               
    def get_groupeddata_old(self,res,group,node=''):
        """
          group hosts into Dict hierarchy or a flat list based on top (usually DC), middlegroup (arbitrary grouping from user and ) optionally node, usually hostname
          which pints to the 'row' dict the contents of which can be summarized
          
        """
    
        groupeddata={}
        
        top=group.pop()
    
        for row in res: 
            assert top in row.keys(), top + " needs to be in row :" + str(row.keys())
            if len(node) > 0:     
                assert node in row.keys(), node + " needs to be in row :" + str(row.keys())
                
            tg_ident=(row[top],)           
            rg_ident = ()
            for field in group:
                assert field in row.keys(), field + " needs to be in row :" + str(row.keys())
                rg_ident = rg_ident + (row[field],)
            
            
            if tg_ident not in groupeddata.keys():
                groupeddata[tg_ident]={}
            if rg_ident not in groupeddata[tg_ident].keys():
                groupeddata[tg_ident][rg_ident] = {}   
            #
            if len(node) > 0: 
                groupeddata[tg_ident][rg_ident][row[node]] = row
        return groupeddata
    
    def prep_plan_info_hostlist(self,hostlist,groups,templateid): 
        
        hostnames=[]
        for host in hostlist:
            hostnames.append( { 'hostname' : host })
            

        return self._prep_plan_info_common(hostnames,groups,templateid)
        
    
    def _prep_plan_info_common(self,results,groups,templateid):
        """
        this function a) sets default fields for grouping, b) groups query results then c) applies the relevant template
        
        """
        groups = [['datacenter'],['superpod'] + groups, ['hostname']]
        
        for field_list in groups:
            for item in field_list:
                assert item in self.fieldcheck, "grouping field must be a supported field"
       
        if len(results)==0:    
            print 'No records qualify check your query filters'              
        results = self.set_default_fields(results)
        
        
        groupedhosts = self.get_groupeddata(results,groups)    
        
        writeplan = self._apply_templates(groupedhosts,templateid)
       
        return writeplan
    
   
        
    def prep_idb_plan_info(self,dcs,idbfilters,regexfilters,groups,templateid):
        """
        entry point function for generating an idb based plan
        """
        groups = [['datacenter'],['superpod'] + groups,['hostname']]
        for field_list in groups:
            for item in field_list:
                assert item in self.fieldcheck, "grouping field must be a supported field"
        
        if templateid.lower()=='AUTO'.lower():
            #if AUTO group by idb template values
            groups[:0]=[['role','dr','failoverstatus']]
        
            
             
        results = self.get_hosts_from_idbquery(dcs,idbfilters,regexfilters)
        for row in results:
            print row
        if len(results)==0:    
            print 'No records qualify check your query filters'              
        results = self.set_default_fields(results)
         
        groupedhosts = self.get_groupeddata(results,groups)
        
            
        writeplan = self._apply_templates(groupedhosts,templateid)
       
        
        return writeplan
      
    def _remove_missing_templates(self,writeplan):
        """
          remove those plans which are not in templates directory and warn for them
        """
        assert len(writeplan.keys())>0, "no data available to write plans"
        missingplans=[]
        for templateid in writeplan.keys():
            template_file = common.templatedir + "/" + str(templateid) + ".template"
            if not os.path.isfile(template_file ):
                print "WARNING : " + template_file + " is not in place. Corresponding hosts will be skipped"
                missingplans.append(templateid)
        
        #clean up missing plans        
        for templateid in missingplans:
            del writeplan[templateid]
        return writeplan
        
    
    def _apply_templates(self,groupedhosts,templateid):   
        """
        take a structure of idb values groupedhosts, grouped by idb template values  (role, dr, failverstatus)
        assert for idb values corresponding to template
        check for template files warning where not present
        return a structure grouped by autogenerated template or initial templateid
        
        """  
        
        writeplan={}
        
        if templateid.upper()!='AUTO':
            writeplan[templateid] = groupedhosts
        else:
            print groupedhosts.keys()
            
            for templatevals in groupedhosts.keys():
                assert templatevals[1:] in self._templatesuffix.keys(), "template idb identifer " + str(templatevals) + " not defined in in " + str(self._templatesuffix)  
                templateid= templatevals[0] + self._templatesuffix[templatevals[1:]]
                logging.debug ( 'derived templateid ' + templateid )
                writeplan[templateid] = groupedhosts[templatevals]
       
        
        self._remove_missing_templates(writeplan)
            
        return writeplan
     
        
        
    def get_groupeddata(self,res,groups):
        """
          group hosts into hierarchical dict based on arbitrary groups of valid fields
          summarizing specified fields at each level
          
        """  
        #global currentnode
        currentnode={}
        for row in res:
            currentnode=self.get_groupeddata_row(row, groups, currentnode)
        
                
                
        return currentnode 
        
    def get_groupeddata_row(self,row,groups,currentnode,groupcount=0):
        """
          recursively get nested groups per row and feed back to get_groupeddata
          
        """   
        
        if groupcount==len(groups):
            currentnode=row
        else:    
            tmp_ident = ()
        
            for field in groups[groupcount]:
                assert field in row.keys(), field + " needs to be in row :" + str(row.keys())
                tmp_ident = tmp_ident + (row[field],)
                    
            if tmp_ident not in currentnode.keys():
                currentnode[tmp_ident] = {}
            currentnode[tmp_ident] = self.get_groupeddata_row(row, groups, currentnode[tmp_ident],groupcount+1)
                
        
        return currentnode
        
                
        
       
                
            
