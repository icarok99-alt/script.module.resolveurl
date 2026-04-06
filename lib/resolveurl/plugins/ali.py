# -*- coding: utf-8 -*-

import re
from urllib.parse import urljoin
from resolveurl.plugins.__resolve_generic__ import ResolveGeneric
from resolveurl.lib import helpers
from resolveurl import common


class SkApiAlibabaCDNResolver(ResolveGeneric):
    name = "SkApiAlibabaCDN"
    domains = ["sk-api.alibabacdn.net"]
    # URL real: https://sk-api.alibabacdn.net/?id=9rFrGnw7rmED1SS8tHrXy-Boyfriend-on-Demand/1
    pattern = r'(?://|\.)(sk-api\.alibabacdn\.net)/?\?(.+)'

    def get_media_url(self, host, media_id):
        embed_url = f'https://{host}/?{media_id}'

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://doramasonline.org/',
            'Origin': f'https://{host}',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
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
            raise Exception('SkApiAlibabaCDN: stream não encontrado')

        stream_url = match.group(1).strip()
        if not stream_url.startswith(('http://', 'https://')):
            stream_url = urljoin(embed_url, stream_url)

        return stream_url + helpers.append_headers(headers)