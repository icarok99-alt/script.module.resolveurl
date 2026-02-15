# -*- coding: utf-8 -*-
from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
import re

try:
    from urllib.parse import urlparse, parse_qs, urljoin
except Exception:
    from urlparse import urlparse, parse_qs, urljoin


class NetcineResolver(ResolveUrl):
    name = 'netcine'
    domains = ['*']
    pattern = r'(?://|\.)([a-z0-9-]{3,25}\.[a-z]{2,})(/?.*)'

    def __init__(self):
        self.net = common.Net()

    def get_url(self, host, media_id):
        if media_id.startswith('http://') or media_id.startswith('https://'):
            return media_id
        if media_id.startswith('/'):
            return 'https://{0}{1}'.format(host, media_id)
        if '/' in media_id or '?' in media_id or '=' in media_id:
            return 'https://{0}/{1}'.format(host, media_id)
        return 'https://{host}/embed-{media_id}.html'.format(host=host, media_id=media_id)

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        if not web_url:
            raise ResolverError('URL inválida')

        headers = {'User-Agent': common.FF_USER_AGENT}
        try:
            p = urlparse(web_url)
            headers['Referer'] = '{0}://{1}/'.format(p.scheme, p.netloc)
            headers['Origin'] = '{0}://{1}'.format(p.scheme, p.netloc)
        except Exception:
            headers['Referer'] = web_url

        try:
            html = self.net.http_GET(web_url, headers=headers).content
        except Exception:
            raise ResolverError('Falha ao obter a página')

        player_link = None

        m = re.search(r'<div[^>]*class=["\']btn-container["\'][^>]*>.*?<a[^>]+href=["\']([^"\']+)["\']', html, re.DOTALL | re.IGNORECASE)
        if m:
            player_link = m.group(1)
            if player_link.startswith('/'):
                try:
                    p = urlparse(web_url)
                    player_link = p.scheme + '://' + p.netloc + player_link
                except Exception:
                    pass

        if not player_link:
            m2 = re.search(r'<div[^>]*id=["\']content["\'][^>]*>.*?<a[^>]+href=["\']([^"\']+)["\']', html, re.DOTALL | re.IGNORECASE)
            if m2:
                player_link = m2.group(1)
                if player_link.startswith('/'):
                    try:
                        p = urlparse(web_url)
                        player_link = p.scheme + '://' + p.netloc + player_link
                    except Exception:
                        pass

        if not player_link:
            m3 = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if m3:
                player_link = m3.group(1)
                if player_link.startswith('/'):
                    try:
                        p = urlparse(web_url)
                        player_link = p.scheme + '://' + p.netloc + player_link
                    except Exception:
                        pass

        if not player_link:
            player_link = web_url

        try:
            player_headers = headers.copy()
            try:
                pp = urlparse(player_link)
                player_headers['Referer'] = f"{pp.scheme}://{pp.netloc}/"
                player_headers['Origin'] = f"{pp.scheme}://{pp.netloc}"
            except Exception:
                pass

            player_html = self.net.http_GET(player_link, headers=player_headers).content
        except Exception:
            raise ResolverError('Falha ao obter o player')

        try:
            b64 = re.search(r'base64,([^"\']+)', player_html)
            if b64:
                decoded = helpers.b64decode(b64.group(1))
                srcs = helpers.scrape_sources(decoded)
                if srcs:
                    chosen = helpers.pick_source(helpers.sort_sources_list(srcs))
                    return self._finalize_headers(chosen, player_headers, player_link)
        except Exception:
            pass

        try:
            srcs = helpers.scrape_sources(player_html)
            if srcs:
                chosen = helpers.pick_source(helpers.sort_sources_list(srcs))
                return self._finalize_headers(chosen, player_headers, player_link)
        except Exception:
            pass

        try:
            sources = re.findall(r'<source[^>]*\s+src=["\']([^"\']+)["\']', player_html, re.IGNORECASE)
            if sources:
                src_list = [{'file': s} for s in sources]
                chosen = helpers.pick_source(helpers.sort_sources_list(src_list))
                return self._finalize_headers(chosen, player_headers, player_link)
        except Exception:
            pass

        try:
            js_files = re.findall(r'file\s*:\s*["\']([^"\']+)["\']', player_html, re.IGNORECASE)
            if js_files:
                last_file = js_files[-1]
                return self._finalize_headers(last_file, player_headers, player_link)
        except Exception:
            pass

        try:
            parsed_player = urlparse(player_link)
            query_params = parse_qs(parsed_player.query)
            n = query_params.get('n', [''])[0]
            p = query_params.get('p', [''])[0]
            if n and p:
                fallback_path = '/media-player/dist/playerhls-fallback.php'
                fallback_query = f'?n={n}&p={p}'
                fallback_url = f"{parsed_player.scheme}://{parsed_player.netloc}{fallback_path}{fallback_query}"
                
                try:
                    fallback_content = self.net.http_GET(fallback_url, headers=player_headers).content
                except Exception:
                    fallback_content = ''

                mp4_matches = re.findall(r'(https?://[^\s"\']+?\.mp4(?:\?[^\s"\']+)?)', fallback_content, re.IGNORECASE)
                if mp4_matches:
                    chosen = mp4_matches[-1]
                    return self._finalize_headers(chosen, player_headers, player_link)
                
                try:
                    if isinstance(fallback_content, bytes):
                        starts = fallback_content.decode('utf-8', errors='ignore').lstrip()
                    else:
                        starts = str(fallback_content).lstrip()
                    if starts.startswith('#EXTM3U'):
                        return self._finalize_headers(fallback_url, player_headers, player_link)
                except Exception:
                    pass
        except Exception:
            pass

        raise ResolverError('Video Link Not Found')

    def _cookiejar(self):
        cj = None
        try:
            if hasattr(self.net, 'cookies') and self.net.cookies:
                cj = self.net.cookies
            elif hasattr(self.net, '_cj') and self.net._cj:
                cj = self.net._cj
            elif hasattr(self.net, 'cookiejar') and self.net.cookiejar:
                cj = self.net.cookiejar
            elif hasattr(self.net, 'session') and hasattr(self.net.session, 'cookies'):
                cj = self.net.session.cookies
        except Exception:
            cj = None
        return cj

    def _cookie_header_for(self, url):
        try:
            p = urlparse(url)
            host = p.netloc.lower()
        except Exception:
            return None

        jar = self._cookiejar()
        if not jar:
            return None

        def _match(domain, host):
            if not domain:
                return False
            d = domain.lstrip('.').lower()
            h = host.lower()
            return h == d or h.endswith('.' + d)

        pairs = []
        try:
            for c in jar:
                if not getattr(c, 'name', None) or getattr(c, 'value', None) in (None, ''):
                    continue
                cdomain = getattr(c, 'domain', '') or host
                if _match(cdomain, host):
                    pairs.append('%s=%s' % (c.name, c.value))
        except Exception:
            pass

        return '; '.join(pairs) if pairs else None

    def _finalize_headers(self, chosen, headers, player_link):
        final_headers = headers.copy()
        
        try:
            pp = urlparse(player_link)
            final_headers['Referer'] = f"{pp.scheme}://{pp.netloc}/"
            final_headers['Origin']  = f"{pp.scheme}://{pp.netloc}"
        except Exception:
            pass

        ck = self._cookie_header_for(chosen)
        if not ck:
            ck = self._cookie_header_for(player_link)
        if ck:
            final_headers['Cookie'] = ck
        elif 'Cookie' in final_headers:
            final_headers.pop('Cookie', None)

        return chosen + helpers.append_headers(final_headers)
