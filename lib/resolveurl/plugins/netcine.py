"""
    Plugin for ResolveURL
    Copyright (C) icarok99 2026

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
from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin


class NetcineResolver(ResolveUrl):
    name = 'netcine'
    domains = ['*']
    pattern = r'(?://|\.)(netcine[a-z0-9 -]*\.[a-z]{2,10})(/[^\s"\'<>]*)'

    def get_url(self, host, media_id):
        host = host.replace(' ', '')
        if media_id.startswith('http'):
            return media_id
        if media_id.startswith('/'):
            return 'https://{0}{1}'.format(host, media_id)
        return 'https://{0}/{1}'.format(host, media_id)

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        p = urlparse(web_url)
        origin = '{0}://{1}'.format(p.scheme, p.netloc)

        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': origin + '/',
            'Origin': origin,
        }

        html = self.net.http_GET(web_url, headers=headers).content

        player_url = None

        m = re.search(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(?:[^<]|<(?!a\b))*?Assistir\s+Online',
            html, re.I | re.S
        )
        if m:
            player_url = m.group(1).strip()

        if not player_url:
            m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
            if m:
                player_url = m.group(1).strip()

        if not player_url:
            raise ResolverError('Link do player não encontrado')

        if player_url.startswith('/'):
            player_url = origin + player_url

        pp = urlparse(player_url)
        player_origin = '{0}://{1}'.format(pp.scheme, pp.netloc)

        player_headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': web_url,
            'Origin': player_origin,
        }

        player_html = self.net.http_GET(player_url, headers=player_headers).content

        m2 = re.search(
            r'<source[^>]+type=["\']application/x-mpegURL["\'][^>]+src=["\']([^"\']+)["\']',
            player_html, re.I
        )
        if not m2:
            m2 = re.search(
                r'<source[^>]+src=["\']([^"\']+)["\'][^>]+type=["\']application/x-mpegURL["\']',
                player_html, re.I
            )

        if m2:
            hls_url = m2.group(1).strip()
            if hls_url.startswith('/'):
                hls_url = player_origin + hls_url
            return hls_url + helpers.append_headers(player_headers)

        raise ResolverError('Video Link Not Found')
