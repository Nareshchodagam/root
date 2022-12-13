alias cb="python /root/git/cptops_jenkins/scripts/case_builder.py"
if [ -d "/root/git/cptops_case_gen" ] ; then
  cd /root/git/cptops_case_gen 
else
  printf "/root/git/cptops_case_gen not found\ntrying running:\n  sh /tmp/setup.sh install\n"
fi
