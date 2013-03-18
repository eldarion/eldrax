import time

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
    
    def containers(self):
        L = []
        response = requests.get(**self._request_kwargs(""))
        response.raise_for_status()
        for line in response.iter_lines():
            L.append(Container(self, line))
        return L


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
    
    def objects(self):
        objs, ret = [], []
        def _fetch_page(marker=None):
            path = self.name
            params = dict(format="json")
            if marker:
                params["marker"] = marker
            response = requests.get(**self.storage._request_kwargs(path, params=params))
            response.raise_for_status()
            return response.json()
        page = _fetch_page()
        while page:
            objs.extend(page)
            # if number of objects returned is less than maximum page length
            # don't bother asking for pages (let's hope Rackspace never lies!)
            if len(page) < 10000:
                break
            page = _fetch_page(marker=page[-1]["name"])
        for o in objs:
            attrs = dict(
                exists=True,
                bytes=o["bytes"],
                hash=o["hash"],
            )
            ret.append(Object(self, o["name"], attrs=attrs))
        return ret


class Object(object):
    
    def __init__(self, container, name, **kwargs):
        self.container = container
        self.name = name
        self.storage = self.container.storage
        if "attrs" in kwargs:
            self.__dict__.setdefault("memo", {})[("attrs", ())] = kwargs["attrs"]
    
    @property
    @memoize
    def attrs(self):
        ret = dict(exists=True)
        path = "{}/{}".format(self.container.name, self.name)
        response = requests.head(**self.storage._request_kwargs(path))
        if response.ok:
            ret.update({
                "bytes": int(response.headers["content-length"]),
                "hash": response.headers["etag"].decode("ascii"),
            })
        elif response.status_code == requests.codes.not_found:
            ret["exists"] = False
        else:
            response.raise_for_status()
        return ret
    
    def _get_file_response(self):
        path = "{}/{}".format(self.container.name, self.name)
        response = requests.get(**self.storage._request_kwargs(path))
        response.raise_for_status()
        return response
    
    def iter_content(self, *args, **kwargs):
        return self._get_file_response().iter_content(*args, **kwargs)
    
    @property
    def content(self):
        return self._get_file_response().content
    
    def save(self, data, delete_on=None):
        path = "{}/{}".format(self.container.name, self.name)
        headers = {}
        if delete_on is not None:
            headers["X-Delete-At"] = str(int(time.mktime(delete_on.timetuple())))
        response = requests.put(**self.storage._request_kwargs(path, headers=headers, data=data))
        response.raise_for_status()
    
    def delete(self):
        path = "{}/{}".format(self.container.name, self.name)
        response = requests.delete(**self.storage._request_kwargs(path))
        if not response.ok and response.status_code != requests.codes.not_found:
            reponse.raise_for_status()
