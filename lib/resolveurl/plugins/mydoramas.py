# -*- coding: utf-8 -*-
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class MyDoramasResolver(ResolveUrl):
    name = 'mydoramas'
    domains = ['ondemand.mylifekorea.shop', 'forks-doramas.mylifekorea.shop']
    pattern = r'(?://|\.)((?:ondemand|forks-doramas)\.mylifekorea\.shop)/([A-Za-z0-9/_\-\.]+\.m3u8[^\s\'"]*)'

    def get_url(self, host, media_id):
        return f"https://{host.strip()}/{media_id.strip()}"

    def get_media_url(self, host, media_id):
        hls_url = self.get_url(host, media_id)
        if '.m3u8' not in hls_url:
            raise ResolverError(f'URL inválida (sem .m3u8): {hls_url}')
        return hls_url + helpers.append_headers({'User-Agent': common.RAND_UA})