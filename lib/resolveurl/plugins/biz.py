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

class AssistirBizResolver(ResolveUrl):
    name = 'assistir.biz'
    domains = ['assistir.biz']

    pattern = r'(?://|\.)(assistir\.biz)/(.+)'

    def get_media_url(self, host, media_id):
        web_url = f"https://{host}/{media_id}"

        headers = {'User-Agent': common.FF_USER_AGENT}

        try:
            redirect_url = helpers.get_redirect_url(web_url, headers=headers)
            if redirect_url and 'mediafire.com' in redirect_url.lower():
                return redirect_url

            response = self.net.http_GET(web_url, headers=headers, redirect=False)
            if response.getcode() not in [200, 301, 302]:
                raise ResolverError(f'Página retornou status {response.getcode()}')

            html = response.content

            patterns = [
                r'(https?://(?:www\.)?mediafire\.com/(?:file|download)/[^\'"\s<>\)]+?/[^\'"\s<>\)]+\.mp4(?:\?.*?)?)',
                r'(https?://download\d+\.mediafire\.com/[^\'"\s<>\)]+\.mp4(?:\?.*?)?)',
                r'(https?://[^\s\'"]+\.mediafire\.com/[^\s\'"]+\.mp4(?:\?.*?)?)'
            ]

            for pat in patterns:
                match = re.search(pat, html, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1)

        except Exception as e:
            raise ResolverError(f'Falha ao resolver {web_url}: {str(e)}')

        raise ResolverError(f'Nenhum link MediaFire encontrado em {web_url}')
