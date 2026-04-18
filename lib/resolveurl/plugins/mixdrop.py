from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
import re

class MixDropResolver(ResolveUrl):
    name = 'MixDrop'
    domains = ['*']
    pattern = r'(?://|\.)([a-z0-9.-]+\.[a-z]{2,})/(?:e|f)/([a-z0-9]+)'

    def get_media_url(self, host, media_id):
        web_url = f"https://{host}/e/{media_id}"
        rurl = f"https://{host}/"

        headers = {
            'User-Agent': common.RAND_UA,
            'Origin': rurl.rstrip('/'),
            'Referer': rurl
        }

        try:
            html = self.net.http_GET(web_url, headers=headers).content

            r = re.search(r'location\s*=\s*["\']([^"\']+)', html)
            if r:
                web_url = f"https://{host}{r.group(1)}"
                html = self.net.http_GET(web_url, headers=headers).content

            if '(p,a,c,k,e,d)' in html:
                html = helpers.get_packed_data(html)

            r = re.search(r'(?:vsr|wurl|surl|src)[\s\w]*=\s*["\']([^"\']+)', html, re.I)
            if r:
                surl = r.group(1)
                if surl.startswith('//'):
                    surl = 'https:' + surl

                headers.pop('Origin', None)
                headers['Referer'] = web_url
                return surl + helpers.append_headers(headers)

        except Exception:
            pass

        raise ResolverError('Video not found')