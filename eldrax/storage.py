import requests

from .base import ApiBase
from .utils import memoize


class Storage(ApiBase):
    
    def __init__(self, *args, **kwargs):
        self.internal = kwargs.pop("internal", False)
        super(Storage, self).__init__(*args, **kwargs)
    
    def _request_kwargs(self, path, **kwargs):
        cdn = kwargs.pop("cdn", False)
        kwargs.setdefault("headers", {})
        kwargs["headers"]["X-Auth-Token"] = self.attrs["auth-token"]
        if cdn:
            endpoint = self.attrs["endpoints"]["cloud-files-cdn"][self.attrs["region"]]
        else:
            endpoints = self.attrs["endpoints"]["cloud-files"][self.attrs["region"]]
            endpoint = endpoints["internal" if self.internal else "public"]
        kwargs["url"] = "{}/{}".format(endpoint, path)
        return kwargs
    
    @memoize
    def __getitem__(self, name):
        c = Container(self, name)
        if not c.exists:
            raise KeyError(name)
        return c


class Container(object):
    
    def __init__(self, storage, name):
        self.storage = storage
        self.name = name
    
    @property
    @memoize
    def attrs(self):
        ret = dict(cdn=False, exists=True)
        path = self.name
        response = requests.head(**self.storage._request_kwargs(path))
        if response.ok:
            ret.update({
                "bytes-used": int(response.headers["x-container-bytes-used"]),
            })
            response = requests.head(**self.storage._request_kwargs(path, cdn=True))
            if response.ok:
                ret.update({
                    "cdn": True,
                    "uri": response.headers["x-cdn-uri"],
                    "ssl-uri": response.headers["x-cdn-ssl-uri"],
                    "streaming-uri": response.headers["x-cdn-streaming-uri"],
                })
        elif response.status_code == requests.codes.not_found:
            ret["exists"] = False
        else:
            response.raise_for_status()
        return ret
    
    @property
    def exists(self):
        return self.attrs["exists"]
