# -*- coding: utf-8 -*-

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