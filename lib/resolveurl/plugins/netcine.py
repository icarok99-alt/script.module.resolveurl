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
from html import unescape

try:
    from urllib.parse import urlparse, parse_qs, urljoin, unquote, quote, urlsplit, urlunsplit
except Exception:
    from urlparse import urlparse, parse_qs, urljoin
    from urllib import unquote, quote


class NetcineResolver(ResolveUrl):
    name = 'netcine'
    domains = ['*']
    pattern = r'(?://|\.)([a-z0-9-]{3,25}\.[a-z]{2,})(/?.*)'

    def __init__(self):
        self.net = common.Net()

    def _normalize_url(self, url):
        if not url:
            return url
        try:
            url = unescape(url).strip()
            parts = urlsplit(url)
            path = quote(unquote(parts.path), safe="/:%")
            query = quote(unquote(parts.query), safe="=&?/:+")
            return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))
        except Exception:
            return url

    def get_url(self, host, media_id):
        if media_id.startswith('http'):
            return media_id
        if media_id.startswith('/'):
            return 'https://{0}{1}'.format(host, media_id)
        if '/' in media_id or '?' in media_id or '=' in media_id:
            return 'https://{0}/{1}'.format(host, media_id)
        return 'https://{host}/embed-{media_id}.html'.format(host=host, media_id=media_id)

    def get_media_url(self, host, media_id):
        web_url = self._normalize_url(self.get_url(host, media_id))
        if not web_url:
            raise ResolverError('URL inválida')

        headers = {'User-Agent': common.FF_USER_AGENT}

        try:
            p = urlparse(web_url)
            headers['Referer'] = f"{p.scheme}://{p.netloc}/"
            headers['Origin'] = f"{p.scheme}://{p.netloc}"
        except Exception:
            headers['Referer'] = web_url

        try:
            html = self.net.http_GET(web_url, headers=headers).content
        except Exception:
            raise ResolverError('Falha ao obter a página')

        player_link = None

        m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*.*?Assistir Online', html, re.I | re.S)
        if m:
            player_link = m.group(1)

        if not player_link:
            iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
            if iframe:
                player_link = iframe.group(1)

        if not player_link:
            player_link = web_url

        if player_link.startswith('/'):
            p = urlparse(web_url)
            player_link = f"{p.scheme}://{p.netloc}{player_link}"

        player_link = self._normalize_url(player_link)

        player_headers = headers.copy()
        try:
            pp = urlparse(player_link)
            player_headers['Referer'] = f"{pp.scheme}://{pp.netloc}/"
            player_headers['Origin'] = f"{pp.scheme}://{pp.netloc}"
        except Exception:
            pass

        try:
            player_html = self.net.http_GET(player_link, headers=player_headers).content
        except Exception:
            raise ResolverError('Falha ao obter o player')

        hls_match = re.search(
            r'<source[^>]+type=["\']application/x-mpegURL["\'][^>]+src=["\']([^"\']+)["\']',
            player_html,
            re.I
        )

        if hls_match:
            hls_url = self._normalize_url(hls_match.group(1))
            return self._finalize_headers(hls_url, player_headers, player_link)

        sources = re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', player_html, re.I)
        if sources:
            chosen = self._normalize_url(sources[-1])
            return self._finalize_headers(chosen, player_headers, player_link)

        try:
            parsed_player = urlparse(player_link)
            query_params = parse_qs(parsed_player.query)
            n = query_params.get('n', [''])[0]
            p = query_params.get('p', [''])[0]
            if n and p:
                fallback_path = '/media-player/dist/playerhls.php'
                fallback_query = f'?n={n}&p={p}'
                fallback_url = f"{parsed_player.scheme}://{parsed_player.netloc}{fallback_path}{fallback_query}"
                fallback_url = self._normalize_url(fallback_url)
                try:
                    fallback_content = self.net.http_GET(fallback_url, headers=player_headers).content
                except Exception:
                    fallback_content = ''
                if isinstance(fallback_content, bytes):
                    text = fallback_content.decode('utf-8', errors='ignore')
                else:
                    text = str(fallback_content)
                if text.strip().startswith('#EXTM3U'):
                    return self._finalize_headers(fallback_url, player_headers, player_link)
                mp4 = re.findall(r'(https?://[^\s"\']+?\.mp4(?:\?[^\s"\']+)?)', text, re.I)
                if mp4:
                    return self._finalize_headers(mp4[-1], player_headers, player_link)
        except Exception:
            pass

        raise ResolverError('Video Link Not Found')

    def _cookiejar(self):
        try:
            return getattr(self.net, 'cookies', None) or \
                   getattr(self.net, '_cj', None) or \
                   getattr(self.net, 'cookiejar', None) or \
                   getattr(self.net.session, 'cookies', None)
        except Exception:
            return None

    def _cookie_header_for(self, url):
        jar = self._cookiejar()
        if not jar:
            return None
        pairs = []
        for c in jar:
            if getattr(c, 'name', None) and getattr(c, 'value', None):
                pairs.append('%s=%s' % (c.name, c.value))
        return '; '.join(pairs) if pairs else None

    def _finalize_headers(self, chosen, headers, player_link):
        chosen = self._normalize_url(chosen)
        final_headers = headers.copy()
        try:
            pp = urlparse(player_link)
            final_headers['Referer'] = f"{pp.scheme}://{pp.netloc}/"
            final_headers['Origin'] = f"{pp.scheme}://{pp.netloc}"
        except Exception:
            pass
        ck = self._cookie_header_for(chosen) or self._cookie_header_for(player_link)
        if ck:
            final_headers['Cookie'] = ck
        return chosen + helpers.append_headers(final_headers)
