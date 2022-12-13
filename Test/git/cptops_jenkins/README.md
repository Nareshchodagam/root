#Jenkins scripts.

_Adding to case_presets.json_

_JSON Format_

		"role_title":{
			"PROD|DR":{
						"PODGROUP": Hostlists file for pod_cases.py
						"TEMPLATEID":Template to use,
						"GROUPSIZE": Default group size,
						"TAGGROUPS":Default taggroups,
						"INFRA":Primary, Secondary or Supporting Infrastructure
						"ROLE": Application role. 
					#optional 
						"FILTER": Optional Filters
						"CASETYPE": Hostlist or coreappafw.
						"REGEX":"failoverstatus=Primary or Standby
						"LIST_FILTER": True or False. Used in conjuction with CASETYPE option. 
						
					}
			}
	
_Example_

			"search(21|22,41|42)_prod":{
				"PROD":{
					"PODGROUP":"pod.pri",
					"TEMPLATEID":"search",
					"GROUPSIZE":15,
					"TAGGROUPS":0,
					"FILTER":["search(21|22)-", "search(41|42)-"],
					"INFRA":"Primary",
					"ROLE":"search"
					}
			},
			

#CPTIAB - CASE_BUILDER

Case builder can be run within the CPTIAB docker image. Use the instruction below to create cases. 

		usage: case_builder.py [-h] [--dry-run] [-l] [-s SEARCH_ROLE]
                       [--roleclass ROLECLASS] [--podgroup PODGROUP]
                       [--groupsize GROUPSIZE] [--taggroups TAGGROUPS]
                       [--bundle BUNDLE] [--subject SUBJECT] [--dowork DOWORK]
                       [--clusstat CLUSTSTAT] [--hoststat HOSTSTAT] [-r REGEX]
                       [-f FILTER]

		Case Builder Program
		
		optional arguments:
		  -h, --help            show this help message and exit
		  --dry-run             Dry run of build no case will be generated.
		  -l, --list            List active role classes.
		  -s SEARCH_ROLE        Search for a role.
		  --roleclass ROLECLASS
		                        Role Class
		  --podgroup PODGROUP   Hostlist file for role.
		  --groupsize GROUPSIZE
		                        Groupsize.
		  --taggroups TAGGROUPS
		                        Taggroups.
		  --bundle BUNDLE       Patch Bundle.
		  --subject SUBJECT     Subject.
		  --dowork DOWORK       Task to perform
		  --clusstat CLUSTSTAT  Cluster Status.
		  --hoststat HOSTSTAT   Host Status.
		  -r REGEX              Regex Filter
		  -f FILTER             Filter
		  --host_validation     To check if remote hosts are already patched OR not accessible.
		  --nolinebacker        To skip linebacker in load balancer operations.
		  --delpatched          Command to remove already patched host of given bundle while case creation.
		  --csv                 Read given CSV file and create cases as per the status, --hostatus is optional comma separated statuses Default is DECOM, --role is optional default take all roles.
		  --role                provide a single or comma seperated role names, this option is optional with --csv. Default is ALL.                     

# Canary cass creation in a single go

    python case_builder.py --canary --bundle 2017.04 --dowork all_updates|centos_migration <--host_validation>

* `all_updates` - Centos_migration + Firmware Patching
 * `centos_migration` - Only Centos migration

    
#Search for available roles classes.

			# python case_builder.py -s search
			search(23|43)_prod
			search(21|22,41|42)_prod
			search_dr
			search_prod
			search(23|43)_dr
			search(21|22,41|42)_dr

#List all available role classes.

			# python case_builder.py -l 
			shared-apputil_prod
			siteproxy_canary_prod
			siteproxy_dr
			siteproxy_prod
			smarts_canary_prod
			smarts_prod
			spellchecker_prod
			stgpm_prod
			web.asg-sjl_prod
			web.chi_dr
			web.was_prod
			web_auth_prod
			web_stage_prod
			
			Total Roles: 117
			
#Create cases for a specified role.

If a role contains multiple filters or requires a custom subject line. You will be prompted for 
that information. 

			# python case_builder --dry-run --roleclass "search(23|43)_prod" --bundle 2016.09 --dowork centos_migration

#Create cases for a comma separated list of datacenters. 
    # python case_builder.py --roleclass sam_flowsnake_prod --bundle current --dowork all_updates -d frf,par
			
#Create cases from CSV file.
    # python case_builder.py  --bundle 2017.11 --dowork all_updates --auto_close_case --csv ~/Downloads/all_hosts_sec.csv --role search,ffx,samcompute --hoststat decom,hwprovisioning
    :: Note
        --role is optional, if not provided it will scan all the roles from CSV.
        --hoststat is optional, if not provided it will create cases for DECOM host/cluster only.
        
	
