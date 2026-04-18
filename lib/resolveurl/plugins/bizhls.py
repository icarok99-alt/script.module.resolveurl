# -*- coding: utf-8 -*-
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

class HLSAstrDigitalResolver(ResolveUrl):
    name = 'hls.astr.digital'
    domains = ['hls.astr.digital']
    pattern = r'(?://|\.)(hls(?:\d+)?\.astr\.digital)/(hls/[A-Za-z0-9/_\-\.\?\=\&]+\.m3u8[^\s\'"]*)'

    def get_media_url(self, host, media_id):
        hls_url = f"https://{host}/{media_id}"

        if ".m3u8" not in hls_url:
            raise ResolverError(f"URL inválida (sem .m3u8): {hls_url}")

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://assistir.biz/',
            'Origin': 'https://assistir.biz',
            'Accept': '*/*'
        }

        return hls_url + helpers.append_headers(headers)