# -*- coding: utf-8 -*-
from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
import re

class AssistirBizSelectorResolver(ResolveUrl):
    name = 'assistir.biz (selector MP4)'
    domains = ['assistir.biz']
    pattern = r'(?://|\.)(assistir\.biz)/(?:selector)\?([^#]+)'

    def get_media_url(self, host, query):
        web_url = f"https://{host}/selector?{query}"

        headers = {'User-Agent': common.RAND_UA}

        try:
            redirect_url = helpers.get_redirect_url(web_url, headers=headers)
            if redirect_url and ('mv.astr.digital' in redirect_url or redirect_url.endswith('.mp4')):
                return redirect_url
        except:
            pass

        try:
            response = self.net.http_GET(web_url, headers=headers, redirect=True)
            html = response.content

            match = re.search(r'https?://mv\.astr\.digital/[^\s\'"]+', html)
            if not match:
                match = re.search(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', html)

            if match:
                return match.group(0)

            match_attr = re.search(r'"(https?://mv\.astr\.digital/[^\s\'"]+)"', html)
            if match_attr:
                return match_attr.group(1)

        except Exception as e:
            raise ResolverError(f'Erro ao resolver selector: {str(e)}')

        raise ResolverError(f'Nenhum link MP4 encontrado em {web_url}')