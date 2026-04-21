# -*- coding: utf-8 -*-

import json
from resolveurl import common
from resolveurl.resolver import ResolveUrl
from resolveurl.lib import helpers


class AnimeYabuResolver(ResolveUrl):
    name = 'AnimeYabu'
    domains = ['r2.cloudflarestorage.com']
    priority = 100
    pattern = r'https?://[a-f0-9]{32}\.r2\.cloudflarestorage\.com/.+\.mp4'

    def get_host_and_id(self, url):
        return self.domains[0], url

    def get_media_url(self, host, media_id):
        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': 'https://www.animesup.info/',
            'Origin': 'https://www.animesup.info'
        }

        base_url = media_id.split('?')[0]
        ads_url = 'https://ads.animeyabu.net/?token=undefined&url=' + base_url

        try:
            res = self.net.http_GET(ads_url, headers=headers).content
            data = json.loads(res)
            assinatura = data[0].get('publicidade')
            if assinatura:
                return base_url + assinatura + helpers.append_headers(headers)
        except Exception:
            pass

        return base_url + helpers.append_headers(headers)

    def get_url(self, host, media_id):
        return media_id
