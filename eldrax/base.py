import json

import requests

from .utils import memoize


class ApiBase(object):
    
    IDENTITY_URLS = {
        "ORD": "https://identity.api.rackspacecloud.com/v2.0/tokens",
        "DFW": "https://identity.api.rackspacecloud.com/v2.0/tokens",
        "IAD": "https://identity.api.rackspacecloud.com/v2.0/tokens",
        "SYD": "https://identity.api.rackspacecloud.com/v2.0/tokens",
        "LON": "https://lon.identity.api.rackspacecloud.com/v2.0/tokens",
    }
    
    def __init__(self, username, api_key, region=None):
        self.username = username
        self.api_key = api_key
        if region is not None and region not in self.IDENTITY_URLS:
            raise Exception("invalid Rackspace region")
        self.region = region
    
    @property
    @memoize
    def attrs(self):
        headers = {"Content-Type": "application/json"}
        payload = {
            "auth": {
                "RAX-KSKEY:apiKeyCredentials": {
                    "username": self.username,
                    "apiKey": self.api_key
                }
            }
        }
        url = self.IDENTITY_URLS[self.region]
        data = json.dumps(payload)
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        data = response.json()
        ret = {
            "auth-token": data["access"]["token"]["id"],
            "region": self.region if self.region is not None else data["access"]["user"]["RAX-AUTH:defaultRegion"],
            "endpoints": {},
        }
        for entry in data["access"]["serviceCatalog"]:
            if entry["name"] == "cloudFiles":
                for endpoint in entry["endpoints"]:
                    regions = ret["endpoints"].setdefault("cloud-files", {})
                    regions[endpoint["region"]] = {
                        "internal": endpoint["internalURL"],
                        "public": endpoint["publicURL"],
                    }
            if entry["name"] == "cloudFilesCDN":
                for endpoint in entry["endpoints"]:
                    regions = ret["endpoints"].setdefault("cloud-files-cdn", {})
                    regions[endpoint["region"]] = endpoint["publicURL"]
            if entry["name"] == "cloudServersOpenStack":
                for endpoint in entry["endpoints"]:
                    regions = ret["endpoints"].setdefault("servers", {}).setdefault("opencloud", {})
                    regions[endpoint["region"]] = endpoint["publicURL"]
            if entry["name"] == "cloudServers":
                ret["endpoints"].setdefault("servers", {})["legacy"] = entry["endpoints"][0]["publicURL"]
        return ret
