from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from six.moves import urllib_error
import re

class StreamTapeResolver(ResolveUrl):
    name = 'StreamTape'
    domains = [
        'streamtape.com', 'strtape.cloud', 'streamtape.net', 'streamta.pe', 'streamtape.site',
        'strcloud.link', 'strcloud.club', 'strtpe.link', 'streamtape.cc', 'scloud.online', 'stape.fun',
        'streamadblockplus.com', 'shavetape.cash', 'streamtape.to', 'streamta.site',
        'streamadblocker.xyz', 'tapewithadblock.org', 'adblocktape.wiki', 'antiadtape.com',
        'streamtape.xyz', 'tapeblocker.com', 'streamnoads.com', 'tapeadvertisement.com',
        'tapeadsenjoyer.com', 'watchadsontape.com'
    ]
    pattern = r'(?://|\.)([a-z0-9.-]+\.[a-z]{2,})/(?:e|v)/([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id, subs=False):
        web_url = self.get_url(host, media_id)
        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': f'https://{host}/'
        }
        try:
            r = self.net.http_GET(web_url, headers=headers).content
        except urllib_error.HTTPError as e:
            if e.code == 503:
                raise ResolverError('Site using Cloudflare DDOS protection')
            else:
                raise ResolverError('Video deleted or removed.')
            return

        src = re.findall(r'''ById\('.+?=\s*(["']//[^;<]+)''', r)
        if src:
            src_url = ''
            parts = src[-1].replace("'", '"').split('+')
            for part in parts:
                p1 = re.findall(r'"([^"]*)', part)[0]
                p2 = 0
                if 'substring' in part:
                    subst = re.findall(r'substring\((\d+)', part)
                    for sub in subst:
                        p2 += int(sub)
                src_url += p1[p2:]
            src_url += '&stream=1'
            src_url = 'https:' + src_url if src_url.startswith('//') else src_url
            src_url = helpers.get_redirect_url(src_url, headers) + helpers.append_headers(headers)

            if subs:
                subtitles = {}
                s = re.findall(r'<track\s*label="([^"]+)"\s*src="([^"]+)"\s*kind="captions"', r)
                if s:
                    subtitles = {lang: surl for lang, surl in s}
                return src_url, subtitles
            return src_url

        raise ResolverError('Video cannot be located.')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://{host}/e/{media_id}')