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

class MyDoramasResolver(ResolveUrl):
    name = 'mydoramas'
    domains = ['ondemand.mylifekorea.shop', 'forks-doramas.mylifekorea.shop']
    
    pattern = r'(?://|\.)((?:ondemand|forks-doramas)\.mylifekorea\.shop)/(.+\.m3u8(?:\?.*)?)'

    def get_media_url(self, host, media_id):
        hls_url = f"https://{host}/{media_id}"

        if '.m3u8' not in hls_url.lower():
            raise ResolverError(f'URL inválida: {hls_url}')

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://www.mydoramas.net/',
            'Origin': 'https://www.mydoramas.net',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }

        try:
            return helpers.append_headers(hls_url) + helpers.append_headers('', headers).split('|')[-1]
        except:
            return f"{hls_url}|User-Agent={common.RAND_UA}&Referer=https://www.mydoramas.net/"

    def get_headers(self):
        return {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://www.mydoramas.net/'
        }
