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


class DoflixResolver(ResolveGeneric):
    name = "Doflix"
    domains = ["doflix.net"]
    
    pattern = r'(?://|\.)((?:doflix\.net))/do/\?id=([^&]+)'

    def get_media_url(self, host, media_id):
        embed_url = f'https://{host}/do/?id={media_id}'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': 'https://doflix.net/',
            'Origin': 'https://doflix.net',
        }

        response = self.net.http_GET(embed_url, headers=headers)
        html = response.content
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='ignore')

        match = re.search(
            r'sources\s*:\s*\[\s*\{[^}]*?["\']file["\']\s*:\s*["\']([^"\']+)["\']',
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
