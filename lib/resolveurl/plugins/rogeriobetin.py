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
from urllib.parse import urlparse

from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl.lib import helpers

class RogerioBetinResolver(ResolveUrl):
    name = 'RogerioBetin'
    domains = ['rogeriobetin.com']
    # padrão que o ResolveURL usa para extrair host e media_id da URL original
    pattern = r'(?://|\.)(rogeriobetin\.com).*(?:[?&]id=)([^&]+)'

    def get_media_url(self, host, media_id):
        """
        Método exigido pelo ResolveURL: recebe host e media_id (capturados pela pattern).
        Retorna a URL final do media com headers anexados para o Kodi reproduzir.
        """
        # Reconstrói a página que contém o jwplayer.setup
        page_url = 'https://{host}/aventura/blog/rb/?id={media_id}'.format(host=host, media_id=media_id)

        headers = {'User-Agent': common.FF_USER_AGENT, 'Referer': page_url}
        html = self.net.http_GET(page_url, headers=headers).content
        # garantimos string
        if isinstance(html, bytes):
            html = html.decode('utf-8', 'ignore')

        # tenta encontrar jwplayer(...).setup({ ... sources: [ ... ] ... })
        m = re.search(r'jwplayer\([^)]*\)\.setup\(\s*\{.*?sources\s*:\s*\[(.*?)\].*?\}\s*\)', html, re.S)
        if not m:
            # fallback genérico
            m = re.search(r'sources\s*:\s*\[(.*?)\]', html, re.S)
        if not m:
            raise ResolverError('RogerioBetin: jwplayer sources não encontrados na página')

        src_block = m.group(1)

        # extrai "file":"...url..."
        fm = re.search(r'["\']file["\']\s*:\s*["\']([^"\']+)["\']', src_block)
        if not fm:
            raise ResolverError('RogerioBetin: campo "file" não encontrado nas sources')

        file_url = fm.group(1)

        # opcional: normalize (alguns hosts podem devolver //host/...)
        if file_url.startswith('//'):
            parsed_page = urlparse(page_url)
            file_url = parsed_page.scheme + ':' + file_url

        # Parse para host e media_id (úteis caso queira expô-los)
        parsed = urlparse(file_url)
        file_host = parsed.netloc
        file_media_id = parsed.path.lstrip('/')

        # Se quiser debug/log: self.logger.debug(('host', file_host, 'media_id', file_media_id))

        # Retorna a URL direta com headers (o helpers transforma dict em sufixo aceito pelo Kodi)
        return file_url + helpers.append_headers(headers)
