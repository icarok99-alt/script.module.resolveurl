# -*- coding: utf-8 -*-
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError
import re


class HLSAstrDigitalResolver(ResolveUrl):
    name = 'hls.astr.digital'
    domains = ['hls.astr.digital']
    pattern = r'(?://|\.)(hls(?:\d+)?\.astr\.digital)/(hls/[A-Za-z0-9/_\-\.\?\=\&]+\.m3u8[^\s\'"]*)'

    def get_url(self, host, media_id):
        built_url = "https://{}/{}".format(host.strip(), media_id.strip())
        return built_url

    def get_media_url(self, host, media_id):
        hls_url = self.get_url(host, media_id)

        if ".m3u8" not in hls_url:
            raise ResolverError("Esta URL parece inválida (não contém .m3u8): {}".format(hls_url))

        headers = {'User-Agent': common.RAND_UA}
        resolved = hls_url + helpers.append_headers(headers)
        return resolved