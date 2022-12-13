#!/bin/bash

HOME=$1
HOME_TMP=${HOME}_e
LABEL=$2

MDH=$(lsblk -i -o NAME,MOUNTPOINT | grep "/$HOME$" | head -n 1 |  perl -nle 'm/(md[0-9]+)/; print $1')
echo $MDH

MDH_STATUS=$(cat /proc/mdstat | grep $MDH)
echo $MDH_STATUS

MDH_NOT_READY=$(cat /proc/mdstat | grep $MDH -A 1| grep '_')
echo $MDH_NOT_READY

if ! [ -z "$MDH_NOT_READY" ]
then
  echo "raid for $HOME $MDH is not ready"
  exit
fi
echo "$HOME is ready to be encrypted."

MDH_RAID=$(echo $MDH_STATUS | awk '{print $4}')
echo $MDH_RAID

if [ $MDH_RAID != "raid1" ]
then
  echo "raid for $HOME $MDH is expected to be 'raid1' and found '$MDH_RAID'"
  exit
fi
echo "found raid type $MDH_RAID for $HOME"

MDH_RAID_STATE=$(echo $MDH_STATUS | awk '{print $3}')
echo $MDH_RAID_STATE

if [ $MDH_RAID_STATE != "active" ]
then
  echo "raid for state $HOME $MDH is expected to be 'active' and found '$MDH_RAID_STATE'"
  exit
fi
echo "found raid state $MDH_RAID_STATE for $HOME"

MDH_TARGET_DISK=$(mdadm --detail /dev/$MDH | tail -1 | awk '{print(substr($7,6))}')
MDH_SRC_DISK=$(mdadm --detail /dev/$MDH | tail -2 | head -1 | awk '{print(substr($7,6))}')


echo $MDH_SRC_DISK > /etc/flux/.${HOME}_src_disk_plain
echo $MDH_TARGET_DISK > /etc/flux/.${HOME}_target_disk_plain

echo "Targeting Encryption on $MDH_TARGET_DISK of $MDH"
echo "Source Unencrypted $MDH_SRC_DISK of $MDH"

mdadm --fail /dev/$MDH /dev/$MDH_TARGET_DISK
mdadm --remove /dev/$MDH /dev/$MDH_TARGET_DISK

yes | mdadm --create /dev/md/$HOME_TMP --level=1 --raid-devices=2 /dev/$MDH_TARGET_DISK missing

NEW_MDH_STATUS=$(cat /proc/mdstat | grep $MDH_TARGET_DISK)

NEW_MDH=$(echo $NEW_MDH_STATUS | awk '{print $1}')
echo "New raid $NEW_MDH created with $MDH_TARGET_DISK"

echo "Encrypting $NEW_MDH"
flux-provision -device /dev/$NEW_MDH
MDH_LUKS_UUID=$(cryptsetup luksUUID /dev/$NEW_MDH)
echo "Encrypting $NEW_MDH with luksUUID: $MDH_LUKS_UUID"

mkfs -t xfs -n ftype=1 -f -L $LABEL /dev/mapper/luks-$MDH_LUKS_UUID

mkdir -p /$HOME_TMP

cp /etc/fstab /etc/fstab.original

echo "/dev/mapper/luks-${MDH_LUKS_UUID}        /${HOME_TMP}     xfs     defaults,noatime,_netdev,x-systemd.automount       0 0" >> /etc/fstab

systemctl daemon-reload
systemctl start $HOME_TMP.automount
systemctl start $HOME_TMP.mount
chmod -R 1755 /$HOME_TMP

xfsdump - /$HOME | xfsrestore - /$HOME_TMP
if [ $? -ne 0 ]; then
  echo "Copying failed!!!! panic"
  exit
fi
