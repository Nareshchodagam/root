#!/bin/bash

SITE=`hostname| cut -d'.' -f1 | awk -F- '{print $NF}'`


function check_ntp
{
        /sbin/service ntpd status | grep running > /dev/null 2>&1
        if [ $? -ne 0 ];then
                echo "ntpd not running. Exiting"
                exit 1
        fi
}

function check_leap 
{
# Version 8.2
# 16 Apr 2015
#
# For each RHEL 4/5/6/7 there are appropriate tzdata packages that should be installed.
# 4: tzdata-2015a-1.el4
# 5: tzdata-2015a-1.el5
# 6: tzdata-2015a-1.el6
# 7: tzdata-2015a-1.el7
#
# Since the correct version is the same for all major releases, check that the 
# installed tzdata rpm is from 2015 (as the 2015a-1 is the first tzdata release of 2015)
#
# If there are outdated tzdata packages, check to see if the localtime file indicates
# that the tzdata package needs to be or may need to be updated for the Leap Second.
#
# Check for the proper kernel versions as well - Red Hat Enterprise Linux 4/5/6 may have 
# potential issues depending on the installed kernel.
#
# For ntp, potential issues with -x or 'slew time' may not work as expected:
# RHEL 7: All NTP Packages are currently affected.
# RHEL 6: Affected are ntp-4.2.6p5-1 and ntp-4.2.6p5-2
# RHEL 5: None affected
#
# -------------------------

echo -n "Installed kernel version: "

kernelVulnerable=0
tzVulnerable=0
ntpAlert=0
strongTZalert=0
potentialTZalert=0

for uname_info in $( uname -r ); do 

    echo $uname_info

    # find tzdata version
    for tzdata in $( rpm -qa | grep tzdata-2); do
        echo "Installed tzdata version: "$tzdata
        # parse out the year of the installed package release and compare to 2015
        if [ ${tzdata:7:4} -lt 2015 ]; then
            tzVulnerable=1
        fi
    done
    
    # if tzdata hasn't been patched to 2015, 
    # examine the localtime setup to determine level of warning needed
    if [ $tzVulnerable -eq '1' ]; then
        localTime_md5=$( md5sum /etc/localtime | awk '{print $1}' )
        for f in $(find '/usr/share/zoneinfo/right' -type f); do
            if [ $strongTZalert -eq '0' ]; then 
                compare_md5=$( md5sum $f | awk '{print $1}' )
                if [[ "$localTime_md5" == "$compare_md5" ]]; then
                    strongTZalert=1
                fi
            fi
        done
    fi
    
    if [ $tzVulnerable -eq '1' ] && [ $strongTZalert -eq '0' ]; then
        potentialTZalert=1
    fi

    # if clock slewing usage found, check ntp package version and warn if needed

    ntpPresent=0
    for ntpVersion in $( rpm -qa | egrep 'ntp-'); do
        if [ -n "$ntpVersion" ]; then
            ntpPresent=1
            echo "Installed ntp version: "$ntpVersion
        fi
    done

    if [ $ntpPresent -eq '1' ]; then
        ntpCheck=0
        for matchingNTPConfig in $( grep '\-x' /etc/sysconfig/ntpd ); do
            ntpCheck=1
        done

        if [ $( grep -aE 'ntpd.*-x' /proc/[0-9]*/cmdline -q; echo $? ) -eq '0' ]; then
            ntpCheck=1
        fi

        for matchingNTPConfig in $( grep 'tinker.*step' /etc/ntp.conf ); do
            ntpCheck=1
        done

        if [ $ntpCheck -eq '1' ]; then
            for matchingOS in $( echo $uname_info | egrep 'el7'); do
                ntpAlert=1
            done
            for matchingOS in $( echo $uname_info | egrep 'el6'); do
                for ntpVersion in $( echo $ntpVersion | egrep 'ntp-4.2.6p5-1|ntp-4.2.6p5-2'); do
                    ntpAlert=1
                done
            done
        fi
    fi

    # do kernel comparisons
    # needed versions indicated below

    uname_maj=$( echo "$uname_info" | awk -F- '{ print $1 }')
    uname_min=$( echo "$uname_info" | awk -F- '{ print $2 }')

    IFS=. minor=($uname_min)

    # Ensure proper padding for comparison to kernel versions
    
    if [ "${#minor[@]}" -eq "2" ]; then
        compareString=${minor[0]}'.0.0'
    elif [ "${#minor[@]}" -eq "3" ]; then
        compareString=${minor[0]}'.0.0'
    elif [ "${#minor[@]}" -eq "4" ]; then
        compareString=${minor[0]}'.'${minor[1]}'.0'
    elif [ "${#minor[@]}" -eq "5" ]; then
        compareString=${minor[0]}'.'${minor[1]}'.'${minor[2]}
    fi
    
    compareVersionsArray=($compareString)

    case ${uname_maj} in
        "2.6.9") 
            # RHEL 4 needs to be after -89
            if [ "${compareVersionsArray[0]}" -lt '89' ]; then
                kernelVulnerable=1
            fi
            ;;
        "2.6.18") 
            # RHEL 5 needs to be after -164
            if [ "${compareVersionsArray[0]}" -lt '164' ]; then
                kernelVulnerable=1
            fi
            ;;
        "2.6.32")
            # RHEL 6 Affected Versions
            # 6 GA: All Versions
            # 6.1: Versions before -131.30.2
            # 6.2: Versions before -220.25.1
            # 6.3: Versions before -279.5.2

            case ${compareVersionsArray[0]} in
                71) kernelVulnerable=1
                    ;;
                131) 
                    if [ "${compareVersionsArray[1]}" -lt '30' ]; then
                        kernelVulnerable=1
                    elif [ "${compareVersionsArray[1]}" -eq '30' ]; then
                        if [ "${compareVersionsArray[2]}" -lt '2' ]; then
                            kernelVulnerable=1
                        fi
                    fi
                    ;;
                220) 
                    if [ "${compareVersionsArray[1]}" -lt '25' ]; then
                        kernelVulnerable=1
                    elif [ "${compareVersionsArray[1]}" -eq '25' ]; then
                        if [ "${compareVersionsArray[2]}" -lt '1' ]; then
                            kernelVulnerable=1
                        fi
                    fi
                    ;;
                279) 
                    if [ "${compareVersionsArray[1]}" -lt '5' ]; then
                        kernelVulnerable=1
                    elif [ "${compareVersionsArray[1]}" -eq '5' ]; then
                        if [ "${compareVersionsArray[2]}" -lt '2' ]; then
                            kernelVulnerable=1
                        fi
                    fi
                    ;;
            esac
            ;;
    esac


    if [ $tzVulnerable -eq 0 ] && [ $kernelVulnerable -eq 0 ] && [ $ntpAlert -eq 0 ]; then
        echo "Not vulnerable"
    else 
        echo ""
        echo "[SUGGESTIONS]"
        if [ $tzVulnerable -ne 0 ]; then
            if [ $strongTZalert -ne 0 ]; then
                echo 'The installed tzdata package needs to be updated before the Leap Second Insertion of June 30, 2015. '
            elif [ $potentialTZalert -ne 0 ]; then
                echo 'The installed tzdata package may need to be updated before the Leap Second Insertion of June 30, 2015. '
            fi
        fi
        if [ $kernelVulnerable -ne 0 ]; then
            echo 'The running kernel is vulnerable to a performance degradation after the Leap Second Insertion of June 30, 2015.'
        fi
        if [ $kernelVulnerable -ne 0 ] || [ $tzVulnerable -ne 0 ]; then
            echo 'Please refer to <https://access.redhat.com/articles/15145> for remediation steps.'
        fi
        if [ $ntpAlert -ne 0 ]; then
          echo 'The installed ntp version may not work as expected for slewing time across the leap second.'
          echo 'Please refer to <https://access.redhat.com/articles/199563> for additional information.'
        fi
        exit 1
    fi

done

}


if [ -r /etc/oracle-release ]; then
        echo "oracle oel host"
cat << EOF > /etc/yum.repos.d/tzdata.repo
[tzdata]
name=Oracle Linux 6 Latest Patches
baseurl=http://ops-inst1-1-$SITE.ops.sfdc.net/media/oel6-patches/latest/x86_64
enabled=0
gpgcheck=0
EOF

        yum update -y --disablerepo=* --enablerepo=tzdata tzdata-2015c-2.el6 ntp tzdata-java-2015c-2.el6
        rm /etc/yum.repos.d/tzdata.repo
        check_ntp
        check_leap

        elif [ -r /etc/redhat-release ]; then
            RH_VER=`cat /etc/redhat-release |awk '{print $7}'`
            RH_VER_MAJOR=`cat /etc/redhat-release |awk '{print $7}'|awk -F"." '{print $1}'`
            RH_VER_MINOR=`cat /etc/redhat-release |awk '{print $7}'|awk -F"." '{print $2}'`

        if [ $RH_VER_MAJOR == '6' ];then
cat << EOF > /etc/yum.repos.d/tzdata.repo
[tzdata]
name=Red Hat Enterprise Linux
baseurl=http://ops-inst1-1-$SITE.ops.sfdc.net/rhel_updates/rhel60u6_x86-64_yum
enabled=0
gpgcheck=0
EOF

            yum update -y --disablerepo=* --enablerepo=tzdata "tzdata*"
            rm /etc/yum.repos.d/tzdata.repo
        fi
        if [ $RH_VER_MAJOR == '5' ];then
cat << EOF > /etc/yum.repos.d/tzdata.repo
[tzdata]
name=Red Hat Enterprise Linux
baseurl=http://ops-inst1-1-$SITE.ops.sfdc.net/rhel_updates/rhel50u10_x86-64_yum
enabled=0
gpgcheck=0
EOF

        yum update -y --disablerepo=* --enablerepo=tzdata "tzdata*"
        rm /etc/yum.repos.d/tzdata.repo
        fi
        check_ntp
        check_leap
fi



exit 0