## Build Plan Examples.

 _Build plan with all na21 ACS servers one by one by majorset-minorset_

	./build_plan.py -c 0000001 -C -G '{"clusters" : "na21" ,"datacenter": "wax" , "roles": "acs", "grouping" : "majorset,minorset", "templateid": "generic_test" }'


 _Build plan with  all na21 acs app and cbatch one by one by majorset minorset_

	./build_plan.py -c 0000001 -C -G '{"clusters" : "na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch", "grouping" : "majorset,minorset", "templateid": "generic_test" }'

 _Build plan with  all na21 acs app and cbatch one by one by majorset minorset applying parallel groups of no more than 12 where possible_

	./build_plan.py -c 0000001 -C -G '{"clusters" : "na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch", "grouping" : "majorset,minorset", "templateid": "generic_test", "maxgroupsize" : 12 }'

 _Build plan with  all na21,cs32,cs33 acs app and cbatch one by one by majorset minorset applying parallel groups of no more than 12 where possible_

	/build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch", "grouping" : "majorset,minorset", "templateid": "generic_test", "maxgroupsize" : 12 }'

 _Build plan with all na21,cs32,cs33 acs app and cbatch one by one by majorset applying parallel groups of no more than 12 where possible (then by role then by cluster)_

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch", "grouping" : "majorset", "templateid": "generic_test", "maxgroupsize" : 12 }'
	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch", "grouping" : "role,majorset", "templateid": "generic_test", "maxgroupsize" : 12 }'
	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch", "grouping" : "cluster,role,majorset", "templateid": "generic_test", "maxgroupsize" : 12 }'

 _Build plan using  host filter regex example:_

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "app,acs,cbatch", "grouping" : "majorset", "templateid": "generic_test", "maxgroupsize" : 12, "hostfilter": 	"^.*1-1" }'

	# get all the 5-* hosts for insights
	./build_plan.py -c 00100209 -C -G '{"clusters" : "INSIGHTS-TYO", "datacenter": "tyo", "roles": "insights_iworker,insights_redis", "grouping" : "majorset", "templateid" : "insights", "maxgroupsize" : 2, "hostfilter": ".*[a-zA-Z]5-*"}'

	newer syntax

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "mgmt_hub", "grouping" : "majorset", "templateid": "pod-hub_standby", "maxgroupsize" : 12, "regexfilter": 	"failOverStatus=STANDBY" }'

 _Generating plans from a file list of hosts (no IDB)_

	./build_plan.py -l ~/prd_mmxcvrlist  -t mmxcvr_standby -s NONE -c 00092225 -i NONE -r mmxcvr -d prd -a

_Generating plans for a list of host (not a file)_
	
	./build_plan.py -l "ops-monitor1-1-sfm,ops-monitor2-1-sfm" -t monitor -r monitor --dowork system_update --bundle 2017.01

 _Other build_plan examples._

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "search,ffx", "grouping" : "majorset,minorset", "templateid" : "generic_test" }'


	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "search", "grouping" : "majorset,minorset" }'

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "search", "grouping" : "majorset,minorset", "maxgroupsize": 5  }'

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "ffx", "grouping" : "majorset,minorset", "maxgroupsize" : 2 }'

	./build_plan.py -c 0000001 -C -G '{"clusters" : "cs32,cs33,na21" ,"datacenter": "wax" , "roles": "acs,app,cbatch,search,ffx", "grouping" : "majorset", "maxgroupsize": 50, "templateid" : "generic_test"  }'

 _Also supports non pod hosts with different interpretations of idb metadata_

	./build_plan.py -c 0000001 -C -G '{"clusters" : "WEBX,WEBAUTH-WAS,WEBSTAGE-WAS" ,"datacenter": "was" , "roles": "web,web_auth,web_stage", "grouping" : "majorset", "maxgroupsize": 50, "templateid" : "web.chi-was.linux"  }'

	./build_plan.py -c 0000001 -C -G '{"clusters" : "AJNA-WAS-SP1,AJNA-WAS-SP2,AJNA-WAS-SP3,AJNA-WAS-SP1" ,"datacenter": "was" , "roles": "mmdcs,mmrelay,mmxcvr,mmmbus,mmrs", "templateid": "ajna_all", "grouping": "cluster,role,majorset", "maxgroupsize": 10}'


_Generating based on clusterType this makes it easier to use as you dont have to select individual clusters UMPS eg below_

	./build_plan.py -c 0000001 -C -G '{"clusterTypes" : "SPLUNK-IDX" ,"datacenter": "sjl" , "templateid" : "mandm-splunk-switch", "grouping": "majorset", "maxgroupsize": 10 }'

_multiple datacenters now supported (originally for UMPS) to allow you to create a plan for all datacenters, -T flag should also be used to add katzmeow GROUP and DC tags_

	./build_plan.py -c 0000001 -C -G '{"clusterTypes" : "CHATTER" ,"datacenter": "sjl,asg,was,chi,tyo,dfw" , "templateid" : "umps.linux", "grouping": "majorset", "maxgroupsize": 20 }' -T
	

_host operationalstatus and cluster operationalstsatus should be used to include hosts which are inactive or clusters which are inactive not active eg graphite_
	
	./build_plan.py -c 0000001 -C -G '{"datacenter": "sfz", "clusterTypes" : "AJNA,GRAPHITE-STORAGE", "roles" : "mmapp,mmcnsmr,graphite_consumer", "cl_opstat" : "ACTIVE,PRE_PRODUCTION,PROVISIONING", "ho_opstat" : "ACTIVE,PRE_PRODUCTION", "maxgroupsize": 40, "templateid" : "graphite", "hostfilter" : "^.*mmcnsmr|^.*mmapp", "grouping" : "superpod" }'
	
_Implicit template selection: if you leave out the templateid parameter it will select and build a plan with templates matching the idb deviceRole, dr status and standby status eg _
		
		./build_plan.py -c 0000001 -C -G '{"clusterType" : "POD","datacenter": "chi,was" , "dr" : "True,False", "roles": "mgmt_hub", "grouping" : "superpod", "maxgroupsize" : 40}' -T
	
	Sample output: (see it processing the templates corresponding to deviceRole_dr_standby
	Template: mgmt_hub_dr_standby
	.....
	Consolidating output into ../output/plan_implementation.txt
	Role :mgmt_hub
	Template: mgmt_hub_dr
	.....
	Generating: ../output/4_plan_implementation.txt
	Consolidating output into ../output/plan_implementation.txt
	Role :mgmt_hub
	Template: mgmt_hub_standby


	Consolidating output into ../output/plan_implementation.txt
	Role :mgmt_hub
	Template: mgmt_hub
	
_build plan from a file: there are 2 basic options: 1) file of idb hosts 2) file of non idb hosts (simply add -x to your command). Please note that while the syntax is a little different than the -G option for specifiying the template ( -t specifies the template, -M specifies the groups and --gsize specifies maxgroupsize). the same grouping and implicit template lookup rules apply whether the hosts are in idb or not_


	1 (a) IDB hosts, implicit lookup no grouping no maxgroupsize	: 	 	eg ./build_plan.py -l ~/host_list
	  (b) IDB hosts, specifying template, group by superpod,cluster, groupsize 5 :		eg ./build_plan.py -l ~/host_list -t dusty -M superpod,cluster --gsize 5
	  
	2 (a) skip idb, no grouping, no maxgroupsize, implicit lookup : eg ./build_plan.py -l ~/host_list -x
	  (b)(i) skip idb, specifying template, groupsize 3 group by role:  eg ./build_plan.py -l ~/host_list -t dusty --gsize 3 -M role -x
	  also: (b)(ii) utilizing both majorset grouping and groupsize on a list of splunk hsts
	 ./build_plan.py -l <(grep 'logsearch.*crz' ~/allddi_08022016 | awk '{print $1}') -M majorset --gsize 4 -x -t ../templates/mandm-splunk-idxr --taggroups 20
	  
other command switches:
==================
_--excludelist. list of hosts to exclude from plan being generated works from list as well as with -G option_

	./build_plan.py -l ~/dhub_stragglers.txt -t dusty -x --exclude ~/excludelist
	
_-T option. adds katzmeow DC tags and group tags add to any command_

	./build_plan.py -l ~/dhub_stragglers.txt -t dusty -x --exclude ~/excludelist -T
	with -T option plan is called then specifying the --dc flag as follows from the release host example : katzmeow.pl --case 0000001 --dc chx

_--bundle <bundlename> will populate the v_BUNDLE variable with <bunldename>_

	./build_plan.py -l ~/dhub_stragglers.txt -t dusty -x --exclude ~/excludelist --bundle 2016.01



	

setup:
==================
On some machines (particularly macs for some reason) you will need to install the corresponding java cryptography extension (JCE)

_Download JCE 6 7 or 8 depending on the version of java you are running_

	http://www.oracle.com/technetwork/java/javase/downloads/jce8-download-2133166.html

_Find the security directory for the jre that you are using eg on mac it will be here as you are forced to use jdk for command line:_

	/Library/Java/JavaVirtualMachines/jdk1.8.0_45.jdk/Contents/Home/jre/lib/security/

_replace the following files in this directory with those from the JCE download_
