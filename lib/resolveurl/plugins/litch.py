# -*- coding: utf-8 -*-

import re
from resolveurl.plugins.__resolve_generic__ import ResolveGeneric
from resolveurl.lib import helpers


class LitchAlibabaCDNResolver(ResolveGeneric):
    name = "LitchAlibabaCDN"
    domains = ["litch.alibabacdn.net"]
    
    pattern = r'(?://|\.)((?:litch\.alibabacdn\.net))/?(?:\?)?(.+)'

    def get_media_url(self, host, media_id):
        if media_id.startswith('?'):
            media_id = media_id[1:]
        
        embed_url = f'https://{host}/?{media_id}'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': 'https://litch.alibabacdn.net/',
            'Origin': 'https://litch.alibabacdn.net',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

        response = self.net.http_GET(embed_url, headers=headers)
        html = response.content
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='ignore')

        match = re.search(
            r'sources\s*:\s*\[\s*\{[^}]*["\']file["\']\s*:\s*["\']([^"\']+)["\']',
            html,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            raise Exception('Não localizado link de vídeo em sources/file')

        stream_url = match.group(1).strip()

        if not stream_url.startswith(('http://', 'https://')):
            from urlparse import urljoin
            stream_url = urljoin(embed_url, stream_url)

        return stream_url + helpers.append_headers(headers)