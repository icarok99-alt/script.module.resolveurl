# -*- coding: utf-8 -*-

import re
from urllib.parse import urljoin
from resolveurl.plugins.__resolve_generic__ import ResolveGeneric
from resolveurl.lib import helpers
from resolveurl import common


class LitchAlibabaCDNResolver(ResolveGeneric):
    name = "LitchAlibabaCDN"
    domains = ["litch.alibabacdn.net"]
    # URL real: https://litch.alibabacdn.net/?id=1465&s=1&e=1&audio=dub
    # media_id captura tudo após '?' (sem img/poster que já foram limpos pelo vod)
    pattern = r'(?://|\.)(litch\.alibabacdn\.net)/?\?(.+)'

    def get_media_url(self, host, media_id):
        # media_id já é a query string completa: id=1465&s=1&e=1&audio=dub
        embed_url = f'https://{host}/?{media_id}'

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://doramasonline.org/',
            'Origin': f'https://{host}',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
        }

        html = self.net.http_GET(embed_url, headers=headers).content
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='ignore')

        match = re.search(
            r'sources\s*:\s*\[\s*\{[^}]*?["\']file["\']\s*:\s*["\']([^"\']+)["\']',
            html, re.IGNORECASE | re.DOTALL
        )
        if not match:
            match = re.search(r'["\']file["\']\s*:\s*["\']([^"\']+)["\']', html, re.IGNORECASE)

        if not match:
            raise Exception('LitchAlibabaCDN: stream não encontrado')

        stream_url = match.group(1).strip()
        if not stream_url.startswith(('http://', 'https://')):
            stream_url = urljoin(embed_url, stream_url)

        return stream_url + helpers.append_headers(headers)