"""
    Plugin for ResolveURL
    Copyright (C) 2025

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
from urllib.parse import urljoin
from resolveurl.plugins.__resolve_generic__ import ResolveGeneric
from resolveurl.lib import helpers
from resolveurl import common


class AlibabaCDNResolver(ResolveGeneric):
    name = "AlibabaCDN"
    domains = [
        "litch.alibabacdn.net",
        "sk-dofix.alibabacdn.net",
        "sk-api.alibabacdn.net"
    ]

    pattern = r'(?://|\.)((?:litch|sk-dofix|sk-api)\.alibabacdn\.net)/?\??(.+)'

    def get_media_url(self, host, media_id):
        if media_id.startswith('?'):
            media_id = media_id[1:]

        embed_url = f'https://{host}/?{media_id}'

        if host == "litch.alibabacdn.net":
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Referer': 'https://litch.alibabacdn.net/',
                'Origin': 'https://litch.alibabacdn.net',
                'Accept': '*/*',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
        else:
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
            r'sources\s*:\s*\[\s*\{[^}]*["\']file["\']\s*:\s*["\']([^"\']+)["\']',
            html, re.IGNORECASE | re.DOTALL
        )

        if not match:
            match = re.search(
                r'["\']file["\']\s*:\s*["\']([^"\']+)["\']',
                html, re.IGNORECASE
            )

        if not match:
            raise Exception(f'AlibabaCDN ({host}): stream não encontrado')

        stream_url = match.group(1).strip()

        if not stream_url.startswith(('http://', 'https://')):
            stream_url = urljoin(embed_url, stream_url)

        return stream_url + helpers.append_headers(headers)
