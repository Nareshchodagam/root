#!/usr/bin/python
###############################################################################
#
# Author:  mhealy
# Purpose: Generate host file for processing by build_plan.py.
#          Generate host & serial# file for serial_check.py 
#
###############################################################################

import argparse
import json

def get_host (input_file):
	
	decomm_file = open('decomm.txt', 'w')
	serial_file = open('serial_check.txt', 'w')

	#get json data
	with open(input_file) as json_file:
		try:
			json_data = json.load(json_file)
			json_file.close()
		except Exception as e:
			print('Problem loading json from file %s : %s' % (input_file,e))

	#save hostname from json data to decomm.txt for build_plan.py
	for host in json_data:
		decomm_file.write(host['Name'])
		decomm_file.write('\n')
	# save hostname and serial # for serial check during decomm
		serial_file.write(host['Name'] + ': ' + host['External_ID__c'])
		serial_file.write('\n')

###############################################################################
#                Main
###############################################################################

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="gen host list")
	parser.add_argument("-f", "--file", dest="filename",
		help="selectedhosts.txt json required as input", metavar="FILE")

	args = parser.parse_args()
	get_host(args.filename)


