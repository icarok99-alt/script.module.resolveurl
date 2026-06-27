"""
    Plugin for ResolveURL
    Copyright (C) icarok99 2026

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from resolveurl import common
from resolveurl.resolver import ResolveUrl


class MegaEmbedResolver(ResolveUrl):
    name = 'megaembed'
    domains = ['w2.playerscdn.xyz', 'cdn.playerscdn.xyz', 'ultracine.blog', 'cinediversao.site', '72yrci50ppqp71.com', 'cineveo.site']

    pattern = (
        r'(?://)'
        r'([\w.-]+\.(?:playerscdn\.xyz|ultracine\.blog|cinediversao\.site|72yrci50ppqp71\.com|cineveo\.site)'
        r'|ultracine\.blog|cinediversao\.site)'
        r'(/[^\s"\'<>]*)'
    )

    REFERER = 'https://d1muf25xa06so8hp27v.mgeb.top/'
    ORIGIN = 'https://d1muf25xa06so8hp27v.mgeb.top'

    def get_media_url(self, host, media_id):
        media_url = 'https://{}{}'.format(host, media_id)

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': self.REFERER,
            'Origin': self.ORIGIN,
            'Accept': '*/*',
        }

        return self._with_headers(media_url, headers)

    @staticmethod
    def _with_headers(url, headers):
        hdr_str = '&'.join('{}={}'.format(k, v) for k, v in headers.items())
        return '{}|{}'.format(url, hdr_str)

    def get_headers(self):
        return {
            'User-Agent': common.RAND_UA,
            'Referer': self.REFERER,
            'Origin': self.ORIGIN,
        }
