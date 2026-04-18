# -*- coding: utf-8 -*-

from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
import re

class AssistirBizResolver(ResolveUrl):
    name = 'assistir.biz'
    domains = ['assistir.biz']

    pattern = r'(?://|\.)(assistir\.biz)/(.+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        web_url = 'https://%s/%s' % (host, media_id)

        headers = {'User-Agent': common.FF_USER_AGENT}

        try:
            redirect_url = helpers.get_redirect_url(web_url, headers=headers)
            if redirect_url and 'mediafire.com' in redirect_url.lower():
                return redirect_url

            response = self.net.http_GET(web_url, headers=headers, redirect=False)
            if response.getcode() not in [200, 301, 302]:
                raise ResolverError('Página retornou status %s' % response.getcode())

            html = response.content

            patterns = [
                r'(https?://(?:www\.)?mediafire\.com/(?:file|download)/[^\'"\s<>\)]+?/[^\'"\s<>\)]+\.mp4(?:\?.*?)?)',
                r'(https?://download\d+\.mediafire\.com/[^\'"\s<>\)]+\.mp4(?:\?.*?)?)',
                r'(https?://[^\s\'"]+\.mediafire\.com/[^\s\'"]+\.mp4(?:\?.*?)?)'
            ]

            for pat in patterns:
                match = re.search(pat, html, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1)

        except Exception as e:
            raise ResolverError('Falha ao resolver %s: %s' % (web_url, str(e)))

        raise ResolverError('Nenhum link MediaFire encontrado em %s' % web_url)
