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
from resolveurl.plugins.__resolve_generic__ import ResolveGeneric
from resolveurl.lib import helpers
from resolveurl import common

class DoramasOnlineResolver(ResolveGeneric):
    name = "DoramasOnline"
    domains = ["doramasonline.org"]
    pattern = r'(?://|\.)((?:doramasonline\.org))(/cdn9/(?:odacdn/v2|dc)/\?id=[^&\'"]+)'

    def get_media_url(self, host, media_id):
        embed_url = f'https://{host}{media_id}'

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://doramasonline.org/',
            'Origin': 'https://doramasonline.org'
        }

        response = self.net.http_GET(embed_url, headers=headers)
        html = response.content

        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='ignore')

        candidates = re.findall(
            r'["\']file["\']\s*:\s*["\']([^"\']+(?:\.m3u8|\.mp4)[^"\']*)["\']',
            html
        )

        if not candidates:
            raise Exception('DoramasOnline: nenhuma fonte de vídeo encontrada no HTML')

        stream_url = next((u for u in candidates if '.m3u8' in u), candidates[0])

        return stream_url + helpers.append_headers(headers)
