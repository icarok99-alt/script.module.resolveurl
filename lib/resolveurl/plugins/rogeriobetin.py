# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse, urljoin

from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl.lib import helpers


class RogerioBetinResolver(ResolveUrl):
    name = 'RogerioBetin'
    domains = ['rogeriobetin.com']
    # URL real (após limpeza do vod): https://rogeriobetin.com/noance/?id=FRVNWhFdSF9BFRZY
    pattern = r'(?://|\.)(rogeriobetin\.com)[^?]*\?(?:.*&)?id=([^&\s"\']+)'

    def get_media_url(self, host, media_id):
        # Suporta /noance/?id= e /aventura/blog/rb/?id=
        page_url = f'https://{host}/noance/?id={media_id}'

        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': 'https://doramasonline.org/',
            'Accept': '*/*',
        }

        html = self.net.http_GET(page_url, headers=headers).content
        if isinstance(html, bytes):
            html = html.decode('utf-8', 'ignore')

        # jwplayer().setup({ sources: [...] })
        m = re.search(
            r'jwplayer\([^)]*\)\.setup\(\s*\{.*?sources\s*:\s*\[(.*?)\]',
            html, re.DOTALL
        )
        if not m:
            m = re.search(r'sources\s*:\s*\[(.*?)\]', html, re.DOTALL)

        if m:
            fm = re.search(r'["\']file["\']\s*:\s*["\']([^"\']+)["\']', m.group(1))
            if fm:
                file_url = fm.group(1)
                if file_url.startswith('//'):
                    file_url = 'https:' + file_url
                elif not file_url.startswith('http'):
                    file_url = urljoin(page_url, file_url)
                return file_url + helpers.append_headers(headers)

        # Fallback: qualquer "file":"url" na página
        fm = re.search(r'["\']file["\']\s*:\s*["\']([^"\']+)["\']', html)
        if fm:
            file_url = fm.group(1)
            if file_url.startswith('//'):
                file_url = 'https:' + file_url
            elif not file_url.startswith('http'):
                file_url = urljoin(page_url, file_url)
            return file_url + helpers.append_headers(headers)

        raise ResolverError('RogerioBetin: sources não encontrados')