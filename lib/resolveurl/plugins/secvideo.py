"""
    Plugin for ResolveURL
    Copyright (C) 2023 gujal
    Updated to handle URLs from doramasonline.org /aviso/ wrapper.
"""

import re
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl import common


class SecVideoResolver(ResolveUrl):
    name = 'SecVideo'
    domains = ['www.secvideo1.online', 'secvideo1.online', 'csst.online']
    # URL real: https://csst.online/embed/977136  ou  https://csst.online/embed/799756/
    pattern = r'(?://|\.)((?:(?:www\.)?secvideo1|csst)\.online)/(?:videos|embed)/([A-Za-z0-9]+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': f'https://{host}/',
            'Accept': '*/*',
        }
        html = self.net.http_GET(web_url, headers=headers).content
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='ignore')

        # Playerjs com múltiplas qualidades: [720p]url,[480p]url,...
        srcs = re.search(r'Playerjs.+?file\s*:\s*["\']([^"\']+)', html, re.DOTALL)
        if srcs:
            file_val = srcs.group(1)
            if '[' in file_val:
                parts = file_val.split(',')
                quality_list = []
                for part in parts:
                    part = part.strip()
                    lm = re.match(r'\[([^\]]+)\](.+)', part)
                    if lm:
                        quality_list.append((lm.group(1), lm.group(2)))
                if quality_list:
                    return helpers.pick_source(helpers.sort_sources_list(quality_list)) + helpers.append_headers(headers)
            else:
                return file_val + helpers.append_headers(headers)

        # Fallback: sources/file (JWPlayer)
        match = re.search(
            r'sources\s*:\s*\[\s*\{[^}]*?["\']file["\']\s*:\s*["\']([^"\']+)["\']',
            html, re.IGNORECASE | re.DOTALL
        )
        if match:
            return match.group(1).strip() + helpers.append_headers(headers)

        raise ResolverError('SecVideo: nenhum vídeo encontrado.')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://{host}/embed/{media_id}/')