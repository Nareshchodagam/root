# CPT's Vault Client
# Can read from and write secrets to HashiCorp Vault

# Worked in: python-requests/2.19.1 and higher, Did not work in: python-requests/2.18.4
# make sure to have the latest requests module, if it throws an invalid cert error even when a valid cert is used.
# Needs slight modifications to work in Python3 (ConfigParser syntax is different in Python3)

##### How to use?
# create a vault instance
# vault = Vault() # no config file specified, reads configs from constants defined below
# or, even a config file can be specified to override constants, ex: vault = Vault("/home/root/.cptops/config/vaultcreds.config")
# call methods to read or write secrets.
# ex: vault.get_secret_by_key("key1", "some/path")

import requests
import os
import sys
import json
import ConfigParser
import logging
from socket import gethostname
import re

CERT = os.environ["HOME"] + "/.cptops/auth/vaultcert.pem"
KEY = os.environ["HOME"] + "/.cptops/auth/vaultkey.pem"
CACERT = os.environ["HOME"] + "/.cptops/auth/Salesforce_Internal_Root_CA_3.pem"
VAULTADDR = "https://api.vault.secrets.SITE.data.sfdc.net:443"
CONFIGADDR = "https://api.vault-config.secrets.SITE.data.sfdc.net:443"
ROOTPATH = "kv/hardening"


logging.basicConfig(level=logging.WARNING,
                    format='%(levelname)-4s [file:%(filename)s,line:%(lineno)d] %(message)s')


class Vault:
    def __init__(self, params_file=None):
        self.vault_params, err = self._set_params(params_file)
        if err:
            logging.critical("Unable to set vault parameters. Exiting.")
            sys.exit(1)

    def login_readonly(self):
        payload = {"name": self.vault_params["rootpath"].replace("/", "_") + "-ro"}
        return self.login(payload)

    def login_readwrite(self):
        payload = {"name": self.vault_params["rootpath"].replace("/", "_") + "-rw"}
        return self.login(payload)

    def login(self, payload):
        payload = payload
        try:
            response = requests.post(self.vault_params["vault_address"] + "/v1/auth/cert/login",
                                     cert=(self.vault_params["cert"], self.vault_params["key"]),
                                     verify=self.vault_params["cacert"],
                                     data=json.dumps(payload)
                                     )
            if not response.status_code == 200:
                raise Exception
            return response.json()["auth"]["client_token"]
        except Exception:
            logging.error("Vault login failed. Verify certificate/connection and try again.")

    def get_secret_by_key(self, secretname, subpath=""):
        token = self.login_readonly()
        print(token)
        if not token:
            logging.critical("Unable to get vault token. Exiting.")
            sys.exit(1)
        logging.debug("Received token. Querying vault for secrets.")
        secret_key_value_pairs = self.read_all_secrets_from_path(token, subpath)
        try:
            if secret_key_value_pairs.get(secretname, False):
                return secret_key_value_pairs[secretname]
            else:
                raise Exception("Unable to find secret {0} at {1}".format(
                    secretname, self.vault_params["rootpath"] + "/" + subpath))
        except Exception as e:
            logging.critical(e)
            sys.exit(1)

    def add_secret_to_path(self, secret_kv={}, subpath=None):
        try:
            token = self.login_readwrite()
            if not token:
                raise Exception("Unable to get vault token. Exiting.")
            if not subpath:
                raise Exception(
                    "Adding to root path is not allowed. Specify a subpath. Use add_subpath() to create one. Exiting.")
            if not secret_kv:
                raise Exception("secret_kv arg cannot be empty. Provide a dict of secrets as key-value pairs. Exiting")
            headers = {"X-Vault-Token": token}
            url = self.vault_params["vault_address"] \
                + "/v1/" \
                + self.vault_params["rootpath"].split("/")[0] + "/data/" \
                + self.vault_params["rootpath"].split("/")[1] + "/" + subpath
            logging.debug("Adding secrets under {0}".format(self.vault_params["rootpath"] + "/" + subpath))
            data = '{0}"data":{1}{2}'.format("{", json.dumps(secret_kv), "}")
            response = requests.put(url, headers=headers,
                                    verify=self.vault_params["cacert"],
                                    data=data)
            if not response.status_code == 200:
                raise Exception("Could not add secrets. Details: {0}".format(response.text))
        except Exception as e:
            logging.critical(e)
            sys.exit(1)

    def add_subpath(self, subpathname=None, destination=None, readers=["self"], writers=["self"]):
        try:
            if not subpathname:
                raise Exception("subpathname arg is missing. Exiting.")
            payload = {"vaultPath": self.vault_params["rootpath"]}
            if destination:
                payload["vaultPath"] = payload["vaultPath"] + "/" + destination
            logging.debug("Creating subpath under {0}".format(payload["vaultPath"]))
            response = requests.post(self.vault_params["config_address"] + "/api/v1/policy/addKVAccess",
                                     cert=(self.vault_params["cert"], self.vault_params["key"]),
                                     verify=self.vault_params["cacert"],
                                     data=json.dumps(payload)
                                     )
            logging.debug("Path {0} created".format(payload["vaultPath"] + "/" + subpathname))
        except Exception as e:
            logging.critical(e)
            sys.exit(1)

    def read_all_secrets_from_path(self, token, subpath=""):
        #import pdb;pdb.set_trace()
        headers = {"X-Vault-Token": token}
        url = self.vault_params["vault_address"] \
            + "/v1/" \
            + self.vault_params["rootpath"].split("/")[0] + "/data/" + self.vault_params["rootpath"].split("/")[1]
        if subpath:
            url += "/{0}".format(subpath)
        try:
            response = requests.get(url, headers=headers, verify=self.vault_params["cacert"])
            if not response.status_code == 200:
                raise Exception("Unable to read from path {0}".format(url))
            return response.json()["data"]["data"]
        except Exception as e:
            logging.error(e)
            logging.critical("Failed to read secret from Vault. "
                             + "Make sure you are trying a valid path and you have read access "
                             + "on the path you are trying.")
            sys.exit(1)

    def _set_params(self, params_file):
        vault_params = {}
        error = True
        if params_file:
            logging.debug("Reading vault parameters from config file {0}".format(params_file))
            config_parser = ConfigParser.ConfigParser()
            # in python3, replace this with configparser.ConfigParser()
            try:
                with open(params_file, "r") as pf:
                    config_parser.readfp(pf)
                site = self._get_site()
                vault_params["cert"] = config_parser.get("HASHICORPVAULT", "cert")
                vault_params["key"] = config_parser.get("HASHICORPVAULT", "key")
                vault_params["cacert"] = config_parser.get("HASHICORPVAULT", "cacert")
                vault_params["vault_address"] = config_parser.get("HASHICORPVAULT", "vaultaddr").replace("SITE", site)
                vault_params["rootpath"] = config_parser.get("HASHICORPVAULT", "rootpath")
                vault_params["config_address"] = config_parser.get("HASHICORPVAULT", "configaddr").replace("SITE", site)
                error = False
            except IOError:
                logging.error("File {0} not found".format(params_file))
            except ConfigParser.NoSectionError:
                logging.error("File {0} not in the expected format. Missing HASHICORPVAULT section".format(params_file))
            except ConfigParser.NoOptionError:
                logging.error(
                    "File {0} not in the expected format. Missing options in HASHICORPVAULT section".format(
                        params_file))
            finally:
                return vault_params, error
        else:
            logging.debug("Config file not specified for vault parameters. Using defaults.")
            if not all([os.path.exists(file) for file in [CERT, KEY, CACERT]]):
                logging.error("Unable to find some of these files: {0}".format(", ".join([CERT, KEY, CACERT])))
            else:
                site = self._get_site()
                vault_params["cert"] = CERT
                vault_params["key"] = KEY
                vault_params["cacert"] = CACERT
                vault_params["vault_address"] = VAULTADDR.replace("SITE", site)
                vault_params["rootpath"] = ROOTPATH
                vault_params["config_address"] = CONFIGADDR.replace("SITE", site)
                error = False
            return vault_params, error

    def _get_site(self):
        hostname = gethostname()
        logging.debug("Parsing site from: {0}".format(hostname))
        if re.search(r'internal.salesforce.com', hostname) or not re.search(r'(sfdc.net|salesforce.com)', hostname):
            site = 'prd'
        else:
            site = hostname.split('-')[-1]
            site = site.replace(".ops.sfdc.net", "")
            site = site.replace(".eng.sfdc.net", "")
        logging.debug("Using site: {0}".format(site))
        return site
