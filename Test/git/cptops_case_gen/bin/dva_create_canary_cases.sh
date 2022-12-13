#! /bin/bash

BUNDLE=$1
PATCHJSON=$2
PREAMBLE=$3 #eg "FEB and GLIBC Patch Bundle : "
OTHER="-T"
PLAN=$4
EXCLUDE='canaryhosts'
FILE_SPL_SWI_CRZ='../hostlists/file_spl_swi_crz'
FILE_SPL_WEB_CRZ='../hostlists/file_spl_web_crz'
FILE_SPL_API_CRZ='../hostlists/file_spl_api_crz'
FILE_SPL_DEP_CRZ='../hostlists/file_spl_dep_crz'


cat ../hostlists/dva*canary > canaryhosts

function create_case {

SUBJECT=$1
DC=$2
DCUP="$(echo $DC | awk '{print toupper($0)}')"
PLAN=$3
echo "python gus_cases.py -T change -f ../templates/$PATCHJSON -s \"$SUBJECT\" -k ../templates/$PLAN -l ../output/summarylist.txt -D $DCUP -i ../output/plan_implementation.txt --infra \"Supporting Infrastructure\"" 
python gus_cases.py -T change -f ../templates/$PATCHJSON -s "$SUBJECT" -k ../templates/$PLAN -l ../output/summarylist.txt -D $DCUP -i ../output/plan_implementation.txt --infra "Supporting Infrastructure" 
}

function build_case_hostlist {

DC=$1
ROLE=$2
PREAMBLE=$3
HOSTLIST=$4
GROUPSIZE=$5
GROUPING=$6
PLAN=$7
TEMPLATEID=$8
if [ -z "$TEMPLATEID" ]; then TEMPLATEID=$ROLE; fi

echo "./build_plan.py -l $HOSTLIST -M $GROUPING --gsize $GROUPSIZE --bundle $BUNDLE $OTHER"
./build_plan.py -l $HOSTLIST -x -M $GROUPING --gsize $GROUPSIZE --bundle $BUNDLE -t $TEMPLATEID $OTHER || exit 1

SUBJECT="$PREAMBLE $DC $ROLE PROD"
create_case "$SUBJECT" $DC $PLAN

}

function build_case_hostlist_idb {

DC=$1
ROLE=$2
PREAMBLE=$3
HOSTLIST=$4
GROUPSIZE=$5
GROUPING=$6
PLAN=$7
./build_plan.py -l $HOSTLIST -M $GROUPING --gsize $GROUPSIZE --bundle $BUNDLE $OTHER || exit 1


SUBJECT="$PREAMBLE $DC $ROLE PROD"
create_case "$SUBJECT" $DC $PLAN
}

function build_case_extra {

#this builds case dynamically looking up template and takes failoverstatus as well

DC=$1
ROLE=$2
PREAMBLE=$3
FOSTAT=$4
DRSTAT=$5


if [ $DRSTAT == 'True' ]; then PRODSTAT=DR; else PRODSTAT=PROD; fi

DCUP="$(echo $DC | awk '{print toupper($0)}')"
MYSUBJECT=$(echo "$PREAMBLE $ROLE $DC $FOSTAT $PRODSTAT" |  tr 'a-z' 'A-Z')
echo "TITLE will be $MYSUBJECT"
./build_plan.py -c 0000002 -C -G '{"clusterTypes" : "POD" ,"datacenter": "'$DC'", "dr" : "'$DRSTAT'" ,"grouping": "role", "maxgroupsize": 8 , "regexfilter" : "failOverStatus='$FOSTAT'", "roles" : "'$ROLE'" }' --exclude /Users/dsheehan/dva_canary --bundle $BUNDLE || exit 1

python gus_cases.py -T change -f ../templates/$PATCHJSON -s "$MYSUBJECT" -k ../templates/6u6-plan.json -l ../output/summarylist.txt -D $DCUP -i ../output/plan_implementation.txt --infra "Supporting Infrastructure"

}


build_case_hostlist_idb sfm CANARY "$3 SMARTS " ../hostlists/dva_smarts.canary 1 role $PLAN
build_case_hostlist_idb asg,crz CANARY "$3 LOGANALYTICS " ../hostlists/dva_loganalytics.canary 1 role $PLAN
build_case_hostlist_idb sfz CANARY "$3 LOGTRANSPORT LHUB" ../hostlists/dva_lhub.canary 1 role lhub-plan.json
build_case_hostlist_idb asg,sfm CANARY "$3 LOGTRANSPORT" ../hostlists/dva_log_transport.canary 1 role $PLAN
build_case_hostlist_idb asg CANARY "$3 DATABROKER " ../hostlists/dva_databroker.canary 1 role $PLAN
build_case_hostlist_idb sjl,sfz,chi,asg CANARY "$3 SR TOOLS " ../hostlists/dva_sr_sr_tools.canary 1 role $PLAN
build_case_hostlist_idb crd CANARY  "$3 CMS " ../hostlists/cms.canary 1 role $PLAN
build_case_hostlist sfm CANARY  "$3 DELPHI GACKPARSER " ../hostlists/dva_delphi.canary 1 role $PLAN manage_apps-patch
build_case_hostlist sfm CANARY  "$3 DICE " ../hostlists/dva_dice.canary 1 role $PLAN dice-app
build_case_hostlist sfm CANARY  "$3 SEYREN " ../hostlists/dva_seyren.canary 1 role $PLAN seyren
build_case_hostlist prd CANARY "$3 ARGUS " ../hostlists/dva_argus.canary 1 role $PLAN manage_apps-patch
build_case_hostlist_idb sfz CANARY  "$3 MMXCVR " ../hostlists/dva_ops_mm.canary 1 role $PLAN
