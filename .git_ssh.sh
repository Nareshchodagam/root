#!/bin/sh
/usr/bin/ssh -i /keys/.ssh/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $*
