#!/usr/bin/python
#
'''
    Jenkins job to rebuild docker image and publish to private
    registry on the CPTOPS server. 
'''
import os
import sys
import subprocess
import logging

def build():
    docker_file = "/home/jenkins/Docker/case_builder/Dockerfile"
    docker_build = "docker build --force-rm=true -t cptops/case_builder ."
    docker_tag = "docker tag -f cptops/case_builder cptops:5000/case_builder"
    docker_pub = "docker push cptops:5000/case_builder"
    if not os.path.isfile(docker_file):
        logging.debug('Dockerfile not found.')
        sys.exit(1)
    logging.debug('Starting build of Docker image.')
    subprocess.call(docker_build.split())
    retcode = subprocess.call(docker_tag.split())
    if retcode != 0:
        logging.debug("Docker tagging failed.")
        sys.exit(1)
    retcode = subprocess.call(docker_pub.split())
    if retcode != 0:
        logging.debug("Docker publish failed.")
        sys.exit(1)

if __name__ == "__main__":
    os.chdir('/home/jenkins/Docker/case_builder')
    build()

