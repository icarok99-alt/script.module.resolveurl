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

from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

class HLSAstrDigitalResolver(ResolveUrl):
    name = 'hls.astr.digital'
    domains = ['hls.astr.digital']
    pattern = r'(?://|\.)(hls(?:\d+)?\.astr\.digital)/(hls/[A-Za-z0-9/_\-\.\?\=\&]+\.m3u8[^\s\'"]*)'

    def get_media_url(self, host, media_id):
        hls_url = f"https://{host}/{media_id}"

        if ".m3u8" not in hls_url:
            raise ResolverError(f"URL inválida (sem .m3u8): {hls_url}")

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://assistir.biz/',
            'Origin': 'https://assistir.biz',
            'Accept': '*/*'
        }

        return hls_url + helpers.append_headers(headers)
