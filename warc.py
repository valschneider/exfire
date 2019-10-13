import requests
import gzip
import json

from urllib.parse import urlparse

from bs4 import BeautifulSoup

def warc_url(url):
    """
    Search the WARC archived version of the URL

    :returns: The WARC URL if found, else None
    """
    query = "http://archive.org/wayback/available?url={}".format(url)

    response = requests.get(query)

    if not response:
        raise RuntimeError()

    data = json.loads(response.text)
    snapshots = data["archived_snapshots"]

    if not snapshots:
        return None

    return snapshots["closest"]["url"]

class WarcDescriptor:
    """
    Web archive content descriptor
    """
    # There's also some more stuff behind, dunno what it is
    def __init__(self, date, url, kind, code, key):
        self.date = date
        self.url = url
        self.kind = kind
        self.code = code
        self.key = key

    @classmethod
    def from_string(cls, string):
        """
        Example expected string: com,xfire,crash)/video/1042c0 20150621140344 http://crash.xfire.com/video/1042c0/ text/html 200 AYEIWSNQ6QKWFXM7S4FZZJIZYSHSDMMW - - 8074 15935484941
        """
        string = string.split()

        # XXX: Do something with the rest?
        _, date, url, kind, code, key, _, _, _, _, _ = string
        return WarcDescriptor(date, url, kind, code, key)

    @classmethod
    def iter_from_url(cls, url):
        response = requests.get(url)

        if not response:
            raise RuntimeError()

        # TODO: check headers for file info?
        data = gzip.decompress(response.content).decode()

        # Dunno what the first line is for, skip it
        for line in data.splitlines()[1:]:
            yield cls.from_string(line)

class WarcHost:
    def __init__(self, url):
        self.url = url

        parse = urlparse(url)
        self.host = "{}://{}".format(parse.scheme, parse.netloc)

    def iter_archive_pages(self):
        """
        Yield the URL for the page of each archive
        """
        response = requests.get(self.url)

        if not response:
            raise RuntimeError()

        dom = BeautifulSoup(response.text, features="html.parser")
        divs = dom.findAll("div", class_="item-ttl")
        for div in divs:
            yield self.host + div.a['href']

    def get_archive_descriptor(self, url):
        """
        :param url: The URL to the archive page
        :type url: str
        """
        response = requests.get(url)

        if not response:
            raise RuntimeError()

        # Look for an archive URL
        dom = BeautifulSoup(response.text, features="html.parser")
        section = dom.find("section", class_="item-download-options")

        # XXX: Might want to search for right format rather than hardcode index
        options = section.findAll("a", class_="format-summary")
        option = options[5]

        return self.host + option['href']

    def iter_descriptors(self):
        for archive_url in self.iter_archive_pages():
            for desc in WarcDescriptor.iter_from_url(self.get_archive_descriptor(archive_url)):
                yield desc
