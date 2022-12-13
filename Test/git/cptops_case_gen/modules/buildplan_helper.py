#!/usr/bin/python
#
#
from modules.common import Common
import json
import sys
import os
import logging
import re
from idbhost import Idbhost
import sys
reload(sys)

common = Common()

def tryint(s):
    """
        convert key to string for ordering using humanreadable_key
    """  
    try:
        return int(s)
    except:
        return s

def humanreadable_key(s):
    """
        function for sorting lists of values to make them readable from left to right
    """  
    s = str(s)

    return [ tryint(c) for c in re.split('([0-9]+)', s) ]

class Groups(dict):
    """
      Input: [l-r]: 
      -rows: list of dicts with identical names, 
      -groupkey: list of field lists. each field list corresponds to a grouping key eg [['datacenter'],['cluster','row']['hostname']]
      -gsize: maximum size of the fields(s) corresponding to the last group specified (hostname in the above example)
      -sortkey: function determining sort order of all fields returned    
      Output:
       result is a nested dict as follows:  mydict[('<dc>',)][('<cluster>',)][(1..n,)]['role|cluster|hostname.. etc']
       which summarizes the values for each field in the row ( in our eg : by dc, cluster and groups of gsize of hostnames) 
       number of values in the field(s) corresponding to the last group ( ['hostname'] )  will be <= gsize
    """

    def _apply_maxgroup(self,tlist, n):
        """
       split a list of tuples into lists of size n for maxgroupsize functionality             
        """  
        l=[tup for tup in tlist]
        n = max(1, n)
        return [tuple(l[i:i + n]) for i in range(0, len(l), n)]

    def _summarize_last(self,currentnode,depth,gsize,level=0):
        """
       1)Drill down to the last group key. ( e.g in groups [ ['datacenter'],['cluster']['hostname'] ] last group key key is [hostname]e)
           2)divide the values in the the last group key inot lists of max size gsize
           3)summarize the row values for each list of size <= gsize and roll the result up to the next group ( [cluster] in example above)
           
           result is a nested dict as follows:  mydict[('<dc>',)][('<cluster>',)][(1..n,)]['role|cluster|hostname.. etc']
           summarizing the values for each field in the row by dc, cluster and hostnames in list < gsize
        """  
        summarynode={}
        if level==depth:
            gsizecount=0
            for key in currentnode:
                summarynode[key] = {}
                for groupednodes in self._apply_maxgroup(sorted(currentnode[key].keys(),key=self.sortkey),gsize):
                    gsizecount+=1
                    summarynode[key][(gsizecount,)] ={} 
                    for field in self.fields:
                        summarynode[key][(gsizecount,)][field]=sorted(list(set([currentnode[key][node][field] for node in groupednodes])),key=self.sortkey)
        else:
            for key in currentnode.keys():
                 summarynode[key]=self._summarize_last(currentnode[key],depth,gsize,level+1)
        
        return summarynode
   
    def __init__(self,rows,groupkey,gsize,sortkey):
        """
           constructor see class documentation
        """
        self.fields = self._precheck(rows,groupkey)
        self.rawgroups=self._get_groupeddata(rows,groupkey)
        self.sortkey = sortkey
        groups = self._summarize_last(self.rawgroups,len(groupkey)-2,gsize) 
        self.update(groups)
    
    def _precheck(self,rows,groupkey):
        """
           prechecks:
       1) rows are present
           2) set of field names are the same for each row (note not checking for field type)
           3) 2 or more groups are specified
           4) group values in rows are unique
        """

        if len(rows)==0:
            raise Exception("No Fields to process")
        if len(groupkey) < 2:   
            raise Exception("2 or more groups must supplied to make up unique groupkey: eg : ['datacenter']['hostname']")
        fields=rows[0].keys() # get field names from first row
        checkkeys={}
        fullkey=[key for keypart in groupkey for key in keypart]
        print fullkey
        for row in rows:
            assert row.keys() == fields, "fieldnames must be identical in each row"
            assert tuple([row[keyval] for keyval in fullkey]) not in checkkeys.keys(), "keys must be unique"
            checkkeys[tuple([row[keyval] for keyval in fullkey])]=None
            
        return fields      
        
    def _get_groupeddata(self,res,groups):
        """
          group hosts into hierarchical dict based on arbitrary groups of valid fields
          summarizing grouping successively by specified fields
          
        """  
        currentnode={}
        for row in res:
            currentnode=self._get_groupeddata_row(row, groups, currentnode)
        
        return currentnode 
        
    def _get_groupeddata_row(self,row,groups,currentnode,groupcount=0):
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
            currentnode[tmp_ident] = self._get_groupeddata_row(row, groups, currentnode[tmp_ident],groupcount+1)
        
        return currentnode
        

class LookupFields(list):
    """
      Input: [l-r]:
       rows: list of dicts with identical keys
      Output:
       above rows are returned with extra fields eg : product_rrcmd and ignored_process names which are populated by looking up the mapping in the dict and applyting the corresponding values
       fields are returned empty save where the lookup value eg role and product_rrcmd correspond to what is in the lists eg app, sfdc-base
      Note: fields should be added to _newfield lookup in reverse order of depenancy : product_rrcmd before ignored_process_names for example below
    """
    def __init__(self,rows):
        self._newfield_lookup = {
              'product_rrcmd' :
          {  'role' :
            {
                   'chatterbox' : ['sshare','prsn'],
                   'chatternow' : ['chan','dstore','msg','prsn'],
                   'mandm-hub' : ['mgmt_hub'],
                   'caas' : ['app'],
                   'lightcycle-snapshot' : ['app'],
                   'mandm-agent' : ['app'],
                   'mq-broker' : ['mq'],
                   'acs' : [ 'acs' ],
                   'searchserver' : [ 'search' ],
                   'sfdc-base' : ['ffx','cbatch','app','dapp'],
                    'insights-redis': ['insights_redis', 'insights_iworker'],
                    'insights-edgeservices': ['insights_redis' ,'insights_iworker'],
                    'waveagent': ['insights_redis', 'insights_iworker'],
                    'wave-connector-agent': ['insights_redis', 'insights_iworker'],
                    'wave-cassandra': ['insights_redis', 'insights_iworker']
            }
          },
              'ignored_process_names_' : 
          {  'product_rrcmd' :
            {
             'redis-server' : ['sfdc-base'],
                         'memcached' : [ 'sfdc-base']
                        } 
              }       
        }
           
        for row in rows:
            self._lookup_newfields(row)    
        self.extend(rows)
    
    def _lookup_newfields(self,row):
        """
          add lookup field to row, defaults to 0 len string
          populate it if any lookups matches any corredponding list value
          we process it as a list so it can catch interpedendencies
        """
        newfields=[]
        for newfield in self._newfield_lookup:
            newvals=[]
            for lookupkey in self._newfield_lookup[newfield]:
                lookups = row[lookupkey] if type(row[lookupkey]) is list else [row[lookupkey]]
                for newval in self._newfield_lookup[newfield][lookupkey]:
                    idlist =  self._newfield_lookup[newfield][lookupkey][newval]
                    for lookup in lookups: 
                       if lookup in idlist:
                            newvals.append( newval )
            row[newfield] =  newvals
            newfields.append(newfield)
        for newfield in newfields:
            row[newfield]=','.join(row[newfield])
        
         

class DerivedFields(list):
    """
       Input: list of dicts with identical keys
       Output: lookus up the value in self.fields and uses it along with custom code in _derive_field method to populate a new field in each row named for the key in self.fields
    """
    def __init__(self,rows):
        self.extend(rows)
        self.fields = {
             'sitelocation' : 'dr',
             'drnostart_rrcmd' : 'dr',
         'ignored_process_names' : 'ignored_process_names_' 
        }
        self._extend()
    
    def _derive_field(self, row, derivedfield):
        """
          see class description
        """
        retval=False
        tempfield = row[self.fields[derivedfield]]
        if derivedfield == 'ignored_process_names':
            row[derivedfield] =  "-" + tempfield + " " + ",".join(row['ignored_process_names_']) + " "
        if derivedfield  == 'sitelocation':
           row[derivedfield] =  U'Secondary' if tempfield else U'Primary'
        if derivedfield  == 'drnostart_rrcmd':
           row[derivedfield] =  U'-drnostart ' if tempfield else ""
 
    def _extend(self):
        for row in list(self):
                for field in self.fields:
                    self._derive_field(row,field)
 

class Buildplan_helper:
    
    def __init__(self,dcs,idbresource,supportedfields,idbfilters,usehostlist=False, hostlist=None ):
        """
           Input: 
        supported fields: dict matching labels (keys) to idb fields (values) allows us to process everything as a list of dicts
        idbresource: any valid idb resource: usually allhosts but can take anything provided you provide appropriate supportedfields
        idbfilters: dict containing keys : valid idb fields values: list of filters, the list allows us to process groups of requests and combine the results
        usehostlist: set this to True if you are passing in a dict structure with hosts: eg : { 'name' : [host1,host2,host3] }
        hostlist: only to be used if there is no interaction with idb (dcs=[], idbresource='', idbfilters={}, still need supportedfields as we use the hostname field)
        """
        self.fields = supportedfields
        self.fieldcheck = self.fields.keys() + ['majorset','minorset','all','datacenter']
        self.usehostlist=usehostlist
        if idbresource != None:
            self.cidblocal = True 
            self.idbhost = Idbhost()
            self.cache={}
            self.idb_resource = idbresource
            self._get_hosts_from_idbquery(dcs,idbfilters)
        elif hostlist != None:
            self.rows = self._get_hostdict(hostlist)
        self.rows = self._set_default_fields(self.rows)
        self.rows = LookupFields(self.rows)
        self.rows = DerivedFields(self.rows)
        self.rows = self._depupe_(self.rows)
        self.unfiltered_rows=self.rows
        self._suffixlist = ['_dr_standby','_dr','_standby','']
        self._templatesuffix= {
                 
                    (True, 'STANDBY') : self._suffixlist[0],
                    (True, 'PRIMARY') : self._suffixlist[1],
                    (False, 'STANDBY') : self._suffixlist[2],
                    (False, 'PRIMARY') : self._suffixlist[3]
                            
                }
     
        
    def _depupe_(self,rows):
        """
      idb can hand us back dupelicate rows and as the format is flexible (lists of dicts) we must protect against it
        """
        # protection against duplicate rows
        return [dict(unique) for unique in set([tuple(undupe.items()) for undupe in rows])]
     
    def _cacher(self,current_obj, arglist):
        """
      looking up and caching @Jacksonids from idb
        """
    # loop through fields from left to right caching ibased on JacksonId if they point to a json object returning if they are cached
        for arg in arglist:
            if type(current_obj[arg]) is unicode:
                current_obj = self.cache[current_obj[arg]]
            else:
                current_obj = current_obj[arg]
            self.cache[current_obj['@' + arg + 'JacksonId']] = current_obj
        
        return current_obj
        
    def _check_cache(self,current_obj,argstring):
        """
            cache and return parent values or return current row values
        """
  
        arglist=argstring.split('.')

        try:
            if len(arglist) > 1:
                return self._cacher(current_obj,arglist[:-1])[arglist[-1]]
            else:    
                return current_obj[arglist[-1]]
        except:
            logging.debug (  "Field" + argstring + ' does not exist in row: ' + str(current_obj) )
            raise
        
        
    def _row_test_regex(self,row,regexfilters):
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
    
    def remove_regexfilters(self):
        """
           turn off regexfilter by restoring unfitlered rows
        """
        self.rows=self.unfiltered_rows


    def apply_regexfilters(self,regexfilters):
        """
        regexfilters : dict of key value pairs containing regexes to be applied to each of the fields.values()  
        """
        results = []
        unfilteredlist=self.rows
        for key in regexfilters:
            logging.debug( "regexfilter: " + key + ", supportedfields: " + ','.join(self.fields.keys()) )
            assert key in self.fields.keys(), "regexfilter  is not a supported field "
            
        for row in unfilteredlist:
            if self._row_test_regex(row,regexfilters):
                results.append( row )
        self.rows = results    
        return results
        
    def _get_field_list(self):
        """
        get the values out of supportedfields to be passed to idbhost.idbquery
        """       
        results=[]
        for val in self.fields.values():
            if type(val) is list:
                results.append( val[0] )
            else:
                results.append( val )
        return results

    def _get_configs_fields(self, jsonresult, configdetails ):
        """
       for processing hostconfigs and clusterconfigs from the cache and pullting them in our list of dict format (rows)
        """
        configlookup = configdetails[1]
        assert len(configlookup) == 1
        allconfigs = self._check_cache(jsonresult,configdetails[0])
        retval = None
        for mykey in configlookup:
            myvalue = configlookup[mykey]
        for config in allconfigs:
            if config[mykey] == myvalue:
                retval = config['value']
        assert not retval is None
        return retval

    def _get_hosts_from_idbquery(self,datacenters,idbfilters):
        """
           datacenters: tuple of 3 character datacenter ids eg : was,chi,tyo ..
           idbfilters : dict of key = valid target fieldname, value = tuple of values

        """
        results = []
        myfields = self._get_field_list()
        json_by_reststring = self.idbhost.idbquery(datacenters,self.idb_resource,myfields,idbfilters,self.usehostlist)
        for dc, json_result in json_by_reststring.items():
            for jsonresult in json_result:
                row = {}
                row['datacenter'] = dc
                for key in self.fields:
                    if not type(self.fields[key]) is list:
                        row[key] = self._check_cache(jsonresult,self.fields[key])
                    else:
                        row[key] = self._get_configs_fields(jsonresult,self.fields[key])
                results.append(row)
        self.rows = results
        if len(self.rows) == 0:
            raise Exception('No records qualify check your query filters')
 
    def _set_default_fields(self,res):
        """
         apply grouping defaults majorset, minorset, datacenter, superpod, rolename taken from hostname
         this allows up to do majorset minorset grouping and can be applied to hosts where we have no idbdata
         
        """
        newres=[]
        for row in res:
            # minorset never present so put it i
            row['minorset'] = row['hostname'].split('-')[2]
            row['majorset'] = ''.join([s for s in row['hostname'].split('-')[1] if s.isdigit()])
            row['all'] = '100'
        
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
    
    
                               
    def _get_hostdict(self,hostlist): 
        """
           get host dict when processing lists of host names
        """ 
        hostnames=[]
        for host in hostlist:
            hostnames.append( { 'hostname' : host })
            
        return hostnames
         
      
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
     
       

    def apply_groups(self, groups, templateid,gsize):
        """
        this is the function that communicates back to buildplan with the information to be processed into implementation plans
        it takes the group input from buildplan and applies the group defaults, then after it has the grouped hosts checks what template to use it to wrap the data structure
        returns the data structure to be processed by bp 
        """
        groups = [['datacenter'],['superpod'] + groups,['hostname']]
        for field_list in groups:
            for item in field_list:
                assert item in self.fieldcheck, "grouping field must be a supported field"
        
        if templateid.lower()=='AUTO'.lower():
            #if AUTO group by idb template values
                groups[:0]=[['role','dr','failoverstatus']]

        mygroups = Groups(self.rows,groups,gsize,humanreadable_key)
        writeplan = self._apply_templates(mygroups,templateid)
        return writeplan
