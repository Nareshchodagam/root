#! /bin/bash

BUNDLE=$1
PATCHJSON=$2
PREAMBLE=$3 #eg "FEB and GLIBC Patch Bundle : "
SELECTORS=$4 # one of role function, or signoff team as defined in case statement :LOG_TRANSPORT LOG_ANALYTICS DATA_BROKER ARGUS ALERTING

OTHER="-T"
EXCLUDE='canaryhosts'
FILE_SPL_SWI_CRZ='../hostlists/file_spl_swi_crz'
FILE_SPL_WEB_CRZ='../hostlists/file_spl_web_crz'
FILE_SPL_API_CRZ='../hostlists/file_spl_api_crz'
FILE_SPL_DEP_CRZ='../hostlists/file_spl_dep_crz'
FILE_SPL_IDX_CRZ='../hostlists/file_spl_idx_crz'
FILE_SPL_IDX_CRZ_IDB='../hostlists/file_spl_idx_crz_idb'
FILE_DEPHI_GACK_ALL='../hostlists/file_delphi_gack_all'
FILE_SEYREN_SFZ='../hostlists/file_seyren_sfz'
FILE_DICE_SFZ='../hostlists/file_dice_sfz'

#collect canary host for exclusion
cat ../hostlists/dva*canary > canaryhosts

function create_case {

SUBJECT=$1
DC=$2
DCUP="$(echo $DC | awk '{print toupper($0)}')"

/usr/local/bin/python gus_cases.py -T change -f ../templates/$PATCHJSON -s "$SUBJECT" -k ../templates/6u6-plan.json -l ../output/summarylist.txt -D $DCUP -i ../output/plan_implementation.txt --infra "Supporting Infrastructure" 
}

function build_case {

DC=$1
ROLE=$2
PREAMBLE=$3
CTYPE=$4
STATUS=$5
GROUPSIZE=$6
GROUPING=$7
TEMPLATEID=$8
if [ -z "$TEMPLATEID" ]; then TEMPLATEID=$ROLE; fi

./build_plan.py -c 0000001 -C -G '{"clusterTypes" : "'$CTYPE'" ,"datacenter": "'$DC'", "roles": "'$ROLE'", "grouping": "'$GROUPING'", "templateid" : "'$TEMPLATEID'",  "maxgroupsize": '$GROUPSIZE', "ho_opstat" : "'$STATUS'" }'  $OTHER --exclude $EXCLUDE --bundle $BUNDLE || exit 1

SUBJECT="$PREAMBLE $DC $ROLE PROD"
create_case "$SUBJECT" $DC

}

function build_case_hostlist {

DC=$1
ROLE=$2
PREAMBLE=$3
HOSTLIST=$4
GROUPSIZE=$5
GROUPING=$6
TEMPLATEID=$7
if [ -z "$TEMPLATEID" ]; then TEMPLATEID=$ROLE; fi

./build_plan.py -l $HOSTLIST -x -M $GROUPING --gsize $GROUPSIZE --bundle $BUNDLE --exclude $EXCLUDE -t $TEMPLATEID $EXTRA || exit 1

SUBJECT="$PREAMBLE $DC $ROLE PROD"
create_case "$SUBJECT" $DC

}

function build_case_hostlist_idb {

DC=$1
ROLE=$2
PREAMBLE=$3
HOSTLIST=$4
GROUPSIZE=$5
GROUPING=$6
TEMPLATEID=$7
if [ -z "$TEMPLATEID" ]; then TEMPLATEID=$ROLE; fi


./build_plan.py -l $HOSTLIST -M $GROUPING --gsize $GROUPSIZE --bundle $BUNDLE --exclude $EXCLUDE -t $TEMPLATEID $EXTRA || exit 1


SUBJECT="$PREAMBLE $DC $ROLE PROD"
create_case "$SUBJECT" $DC
}

function build_case_fostat {

#this builds case dynamically looking up template and takes failoverstatus as well

DC=$1
ROLE=$2
PREAMBLE=$3
CTYPE=$4
FOSTAT=$5
DRSTAT=$6
GROUPSIZE=$7


if [ $DRSTAT == 'True' ]; then PRODSTAT=DR; else PRODSTAT=PROD; fi

DCUP="$(echo $DC | awk '{print toupper($0)}')"
MYSUBJECT=$(echo "$PREAMBLE $ROLE $DC $FOSTAT $PRODSTAT" |  tr 'a-z' 'A-Z')
echo "TITLE will be $MYSUBJECT"
./build_plan.py -c 0000002 -C -G '{"clusterTypes" : "'$CTYPE'" ,"datacenter": "'$DC'", "dr" : "'$DRSTAT'" ,"grouping": "role", "maxgroupsize": '$GROUPSIZE' , "regexfilter" : "failOverStatus='$FOSTAT'", "roles" : "'$ROLE'" }' --exclude $EXCLUDE --bundle $BUNDLE || exit 1

/usr/local/bin/python gus_cases.py -T change -f ../templates/$PATCHJSON -s "$MYSUBJECT" -k ../templates/6u6-plan.json -l ../output/summarylist.txt -D $DCUP -i ../output/plan_implementation.txt --infra "Supporting Infrastructure"

}

# LOG TRANSPORT
function log_hub {
  DC="asg,sjl,tyo,chi,was,lon,dfw,phx,frf"
  ROLE=log_hub
  CTYPE=HUB
  FOSTAT=PRIMARY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function log_hub_standby {
  DC="asg,sjl,tyo,chi,was,lon,dfw,phx,frf"
  ROLE=log_hub
  CTYPE=HUB
  FOSTAT=STANDBY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function lhub {
  DC="sfz"
  ROLE=lhub
  CTYPE=HUB
  FOSTAT=PRIMARY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function lhub_standby {
  DC="sfz"
  ROLE=lhub
  CTYPE=HUB
  FOSTAT=STANDBY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function logbus {
  DC=sfm
  ROLE=logbus
  CTYPE=LOGBUS
  STATUS=ACTIVE
  build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 2 role
}

# LOG ANALYTICS
function mandm-splunk-api {

  DC=crz
  ROLE=mandm-splunk-api
  build_case_hostlist $DC $ROLE "$PREAMBLE" $FILE_SPL_API_CRZ 1 role $ROLE

}

function mandm-splunk-deployer {

  DC=crz
  ROLE=mandm-splunk-deployer
  build_case_hostlist $DC $ROLE "$PREAMBLE" $FILE_SPL_DEP_CRZ 1 role $ROLE
}

function mandm-splunk-idxr {

  DC=crz
  ROLE=mandm-splunk-idxr
  build_case_hostlist $DC $ROLE "$PREAMBLE NON IDB" $FILE_SPL_IDX_CRZ 15 role $ROLE
  build_case_hostlist $DC $ROLE "$PREAMBLE IDB" $FILE_SPL_IDX_CRZ_IDB 15 role $ROLE
}

function mandm-splunk-web {

  DC=crz
  ROLE=mandm-splunk-web
  build_case_hostlist $DC $ROLE "$PREAMBLE" $FILE_SPL_WEB_CRZ 1 role $ROLE
	
}

function mandm-splunk-switch {

  CTYPE=SPLUNK-IDX
  ROLE=mandm-splunk-switch
  STATUS=ACTIVE
  for DC in asg sjl tyo chi was lon dfw phx frf
  do
	echo "$DC $ROLE $PREAMBLE $CTYPE"
   	build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 10 role
  done
}


#DATA BROKER
function mmmbus {

  CTYPE=AJNA
  ROLE=mmmbus
  STATUS=ACTIVE
  for DC in asg sjl tyo chi was lon dfw phx frf
  do
    build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset
  done
}
function mmmbus_SFZ {
  CTYPE=AJNA
  ROLE=mmmbus
  STATUS=ACTIVE
  DC="sfz"
  build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset mmmbus_SFZ
}

function mmdcs {
  CTYPE=AJNA
  ROLE=mmdcs
  STATUS=ACTIVE
  for DC in asg sjl tyo chi was lon dfw phx frf
  do
    echo "$DC $ROLE $PREAMBLE $CTYPE"
    build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset
  done
}

function mmrs {
  CTYPE=AJNA
  ROLE=mmrs
  STATUS=ACTIVE
  for DC in asg sjl tyo chi was lon dfw phx frf
  do
    echo "$DC $ROLE $PREAMBLE $CTYPE"
    build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset
  done
}


#SR / SR TOOLS
function mmxcvr {
  DC="sfz"
  ROLE=mmxcvr
  CTYPE=AJNA
  FOSTAT=PRIMARY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function mmxcvr_standby {
  DC="sfz"
  ROLE=mmxcvr
  CTYPE=AJNA
  FOSTAT=STANDBY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function mmpal {

  CTYPE=AJNA
  ROLE=mmpal
  STATUS=ACTIVE
  DC="sfz,chi,was"
  build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset
}

function mmrelay {

  CTYPE=AJNA
  ROLE=mmrelay
  STATUS=ACTIVE
  for DC in asg sjl tyo chi was lon dfw phx frf
  do
    echo "$DC $ROLE $PREAMBLE $CTYPE"
    build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset
  done
}

function mgmt_hub {
  ROLE=mgmt_hub
  for DC in chi was lon dfw phx frf asg sjl
  do
    build_case_fostat $DC $ROLE "$PREAMBLE" POD STANDBY False 15
    build_case_fostat $DC $ROLE "$PREAMBLE" POD PRIMARY False 15
    build_case_fostat $DC $ROLE "$PREAMBLE" POD STANDBY True 15
    build_case_fostat $DC $ROLE "$PREAMBLE" POD PRIMARY True 15
  done
  #no DR in TYO
  build_case_fostat tyo $ROLE "$PREAMBLE" POD STANDBY False 15
  build_case_fostat tyo $ROLE "$PREAMBLE" POD PRIMARY False 15
}

function dusty {
  DC="asg,sjl,tyo,chi,was,lon,dfw,phx,frf"
  ROLE=dusty
  CTYPE=DUSTYHUB
  FOSTAT=PRIMARY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

function dusty_standby {
  #standby for dustyhub  only in these dcs
  DC="tyo,lon,dfw,phx,frf"
  ROLE=dusty
  CTYPE=DUSTYHUB
  FOSTAT=STANDBY
  GSIZE=1
  build_case_fostat $DC $ROLE "$PREAMBLE" $CTYPE $FOSTAT False $GSIZE
}

#ALERTING
function smarts {
  CTYPE=SMARTS
  ROLE=smarts
  STATUS=ACTIVE,PRE_PRODUCTION,PROVISIONING
  for DC in asg sjl tyo chi was lon dfw phx frf
  do
    build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 majorset,minorset
  done
}

#CMS

function cms {

  DC="asg,sjl,tyo,chi,was,lon,dfw,phx,frf"
  ROLE=cms
  CTYPE=CMS
  STATUS=ACTIVE
  build_case $DC $ROLE "$PREAMBLE" $CTYPE $STATUS 1 role
}

function delphi {

  DC=sfz,sfm
  ROLE=delphi
  build_case_hostlist $DC $ROLE "$PREAMBLE" $FILE_DEPHI_GACK_ALL 1 role manage_apps-patch

}

function seyren {

  DC=sfz
  ROLE=seyren
  build_case_hostlist $DC $ROLE "$PREAMBLE" $FILE_SEYREN_SFZ 1 role seyren

}

function dice {

  DC=sfz
  ROLE=dice
  build_case_hostlist $DC $ROLE "$PREAMBLE" $FILE_DICE_SFZ 1 role dice-app

}

for SELECTOR in $(echo $SELECTORS | sed 's/,/ /g')
do
  case "$SELECTOR" in
	MONITOR)
	  smarts
   	;;
	SYNTHETICS)
	  dice
   	;;
	DELPHI)
	  delphi
   	;;
        CMS)
          cms 
        ;;
	LOG_TRANSPORT)
	  log_hub
	  log_hub_standby
	  lhub
	  lhub_standby
          logbus
	;;
	LOG_ANALYTICS)
    	  mandm-splunk-api
	  mandm-splunk-deployer
	  mandm-splunk-idxr
	  mandm-splunk-web
	  mandm-splunk-switch
	;;
	
	DATA_BROKER)
	  mmmbus_SFZ
	  mmmbus
	  mmdcs
	  mmrs 
    	;;
	SR_SR_TOOLS)
	  mmpal
	  mmrelay
	  mgmt_hub
	  mmxcvr
	  mmxcvr_standby
	  dusty
	  dusty_standby
        ;;
	ARGUS)
    	echo $SELECTOR
    	;;
	log_hub)
	  log_hub
         ;;
	log_hub_standby)
	  log_hub_standby
	;;
	lhub)
	  lhub
	;;
	lhub_standby)
	  lhub_standby
	;;
        logbus)
          logbus
	;;
    	mandm-splunk-api)
    	  mandm-splunk-api
	;;
	mandm-splunk-deployer)
	  mandm-splunk-deployer
	;;
	mandm-splunk-idxr)
	  mandm-splunk-idxr
	;;
	mandm-splunk-web)
	  mandm-splunk-web
	;;
	mandm-splunk-switch)
	  mandm-splunk-switch
	;;
	mmmbus_SFZ)
	  mmmbus_SFZ
	;;
	mmmbus)
	  mmmbus
	;;
	mmdcs)
	  mmdcs
	;;
	mmrs)
	  mmrs 
	;;
	mmxcvr)
	  mmxcvr
        ;;
	mmxcvr_standby)
	  mmxcvr_standby
        ;;
	mmpal)
	  mmpal
	;;
	mmrelay)
	  mmrelay
	;;
	mgmt_hub)
	  mgmt_hub
	;;
	dusty)
	  dusty
	;;
	dusty_standby)
	  dusty_standby
	;;
	dice)
	  dice
	;;
	delphi)
	  delphi
	;;
	seyren)
	  seyren
	;;
  esac
done

