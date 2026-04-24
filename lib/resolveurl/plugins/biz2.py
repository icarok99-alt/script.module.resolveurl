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

from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
import re

class AssistirBizSelectorResolver(ResolveUrl):
    name = 'assistir.biz (selector MP4)'
    domains = ['assistir.biz']
    pattern = r'(?://|\.)(assistir\.biz)/(?:selector)\?([^#]+)'

    def get_media_url(self, host, query):
        web_url = f"https://{host}/selector?{query}"

        headers = {'User-Agent': common.RAND_UA}

        try:
            redirect_url = helpers.get_redirect_url(web_url, headers=headers)
            if redirect_url and ('mv.astr.digital' in redirect_url or redirect_url.endswith('.mp4')):
                return redirect_url
        except:
            pass

        try:
            response = self.net.http_GET(web_url, headers=headers, redirect=True)
            html = response.content

            match = re.search(r'https?://mv\.astr\.digital/[^\s\'"]+', html)
            if not match:
                match = re.search(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', html)

            if match:
                return match.group(0)

            match_attr = re.search(r'"(https?://mv\.astr\.digital/[^\s\'"]+)"', html)
            if match_attr:
                return match_attr.group(1)

        except Exception as e:
            raise ResolverError(f'Erro ao resolver selector: {str(e)}')

        raise ResolverError(f'Nenhum link MP4 encontrado em {web_url}')
