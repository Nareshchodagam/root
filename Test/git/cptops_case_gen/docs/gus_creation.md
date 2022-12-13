
# GUS creation examples

# Script usage:

	Usage:

    This script provides a few different functions:
    - create a new change case
    - attach a file to a case
    - update case comments
    - create a new incident record

    Creating a new change case:
    gus_cases.py -T change -f file with change details -i implan -s "subject to add" -k json for the change

    Example:
    gus_cases.py -T change -f templates/oracle-patch.json -i output/plan_implementation.txt
            -s "CHI Oracle : shared-nfs SP3 shared-nfs3{2|3}-{1|2}"
            -k templates/shared-nfs-planer.json -l shared-nfs-sp3.txt


	Options:
	  -h, --help            show this help message and exit
	  -c CASEID, --case=CASEID
	                        The caseId of the case to attach the file
	  -f FILENAME, --filename=FILENAME
	                        The name of the file to attach
	  -l HOSTLIST, --hostlist=HOSTLIST
	                        The hostlist for the change
	  -L, --logicalHost     Create Logical host connectors
	  -V VPLAN, --vplan=VPLAN
	                        The verification plan for the change
	  -i IPLAN, --iplan=IPLAN
	                        The implementation plan for the change
	  -k IMPLANNER, --implanner=IMPLANNER
	                        The implementation planner json for the change
	  -p FILEPATH, --filepath=FILEPATH
	                        The path to the file to attach
	  -s SUBJECT, --subject=SUBJECT
	                        The subject of the case
	  -r ROLE, --role=ROLE  The host role of the case
	  -d DESC, --description=DESC
	                        The description of the case
	  -T CASETYPE, --casetype=CASETYPE
	                        The type of the case
	  -S STATUS, --status=STATUS
	                        The status of the case
	  -D DC, --datacenter=DC
	                        The data center of the case
	  -P PRIORITY, --priority=PRIORITY
	                        The priority of the case : Sev[1..4]
	  -C CATEGORY, --category=CATEGORY
	                        The category of the case
	  -b SUBCATEGORY, --subcategory=SUBCATEGORY
	                        The subcategory of the case
	  -A, --submit          Submit the case for approval
	  --inst=INST           List of comma separated instances
	  --infra=INFRA         Infrastructure type
	  -n, --new             Create a new case. Required args :
	                        Category, SubCategory, Subject, Description, DC,
	                        Status and Prioriry.
	                        -n -C Systems -b SubCategory Hardware -s Subject 'DNS
	                        issue 3' -d 'Mail is foobar'd, DSET Attached.' -D ASG
	                        -S New -P Sev3
	  -a, --attach          Attach a file to a case
	  -t COMMENT, --comment=COMMENT
	                        text to add to a case comment
	  -y, --yaml            patch details via yaml file
	  -u, --update          Required if you want to update a case
	  -v                    verbosity

# Required files. 

_Example of two files used with gus_cases.py.

[details.json](../Examples/details_example.json). Example file used to create the GUS case filling in necessary information.

[plan.json](../Examples/implementation_example.json). Example file used for comments when creating implementation steps. 

# Command Examples

# Create a simple case. 

	python gus_cases.py -T change  -f <GUS.json>  -s "May Patch Bundle : Sites Proxies CHI $1 DR" -k <GUS implementation json> \
	 -l <host list> -D chi -i <file to attach> --inst na5,na19,na20 --infra Primary

# Create a case for multiple DC's

	python gus_cases.py -T change  -f  <GUS.json>  -s "May Patch Bundle : Sites Proxies CHI $1 DR" -k <GUS implementation json> \
	 -l  <host list>  -D '{"chi": "na5,na19,na20", "tyo": "ap0,ap1}' -i  <file to attach> --infra Primary
	
	python gus_cases.py -T change  -f  <GUS.json>  -s "May Patch Bundle : Sites Proxies CHI $1 DR" -k <GUS implementation json> \
	 -l  <host list>  -D chi,tyo -i  <file to attach> --infra Primary

# Attach a file to an existing case. 

	python gus_cases.py -c <case #> -a -f <file_name> -u 
	
# Make a comment to an existing case.

	python gus_cases.py -c <case #> -u -t "This is a test comment"

# Add Logical host records to an existing cases. 

	Create hostlist file.
	Option -L uses hostlist to add the records. 
	 
	python gus_cases.py -T change  -f <GUS.json>  -s "May Patch Bundle : Sites Proxies CHI $1 DR" -k <GUS implementation json> \
	 -l <host list> -D chi -i <file to attach> --inst na5,na19,na20 --infra Primary -L 

# How to create a implementation plan and create the case. 

	python build_plan.py -c 0000001 -C -G '{"clusters" : "'$1'" ,"datacenter": "chi" , "roles": "proxy", "grouping" : "majorset,minorset", \
	"maxgroupsize": 5, "templateid" : "siteproxy_standby.linux", "dr": "True"  }' -v
	
	python gus_cases.py -T change  -f ../templates/sites-proxy-rh6u6-patch.json  -s "May Patch Bundle : Sites Proxies CHI $1 DR" \
	-k ../templates/6u6-plan.json  -l ../output/summarylist.txt -D chi -i ../output/plan_implementation.txt



