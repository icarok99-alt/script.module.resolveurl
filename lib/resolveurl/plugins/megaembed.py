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

import re
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class MegaEmbedResolver(ResolveUrl):
    name = 'megaembed'
    domains = ['w2.playerscdn.xyz', 'cdn.playerscdn.xyz', 'ultracine.blog', 'cinediversao.site', '72yrci50ppqp71.com']

    pattern = (
        r'(?://)'
        r'([\w.-]+\.(?:playerscdn\.xyz|ultracine\.blog|cinediversao\.site|72yrci50ppqp71\.com)'
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

        if 'hls.php' in media_url or '.m3u8' in media_url:
            try:
                best_url = self._resolve_hls(media_url, headers)
                if best_url:
                    return self._with_headers(best_url, headers)
            except Exception:
                pass

        return self._with_headers(media_url, headers)

    def _resolve_hls(self, url, headers):
        try:
            content = helpers.get_html(url, headers=headers)
        except Exception:
            return url

        if '#EXTM3U' not in content:
            return url

        if '#EXT-X-STREAM-INF' in content:
            best = self._pick_best_stream(url, content)
            return best if best else url

        return url

    def _pick_best_stream(self, base_url, m3u8_content):
        streams = []
        lines = m3u8_content.splitlines()

        for i, line in enumerate(lines):
            line = line.strip()
            if not line.startswith('#EXT-X-STREAM-INF'):
                continue

            bw_match = re.search(r'BANDWIDTH=(\d+)', line)
            res_match = re.search(r'RESOLUTION=([\dx]+)', line)
            bandwidth = int(bw_match.group(1)) if bw_match else 0
            resolution = res_match.group(1) if res_match else '?x?'

            for j in range(i + 1, len(lines)):
                uri = lines[j].strip()
                if uri and not uri.startswith('#'):
                    if not uri.startswith('http'):
                        base = re.sub(r'[?#].*$', '', base_url).rsplit('/', 1)[0]
                        uri = '{}/{}'.format(base, uri)
                    streams.append((bandwidth, resolution, uri))
                    break

        if not streams:
            return None

        streams.sort(key=lambda x: x[0], reverse=True)
        return streams[0][2]

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
