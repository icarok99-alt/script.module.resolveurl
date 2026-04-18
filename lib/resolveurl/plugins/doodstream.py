import re
import random
import string
import time
from six.moves import urllib_parse
from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError


class DoodStreamResolver(ResolveUrl):
    name = 'DoodStream'
    domains = [
        'dood.watch', 'doodstream.com', 'dood.to', 'dood.so', 'dood.cx', 'dood.la', 'dood.ws',
        'dood.sh', 'doodstream.co', 'dood.pm', 'dood.wf', 'dood.re', 'dood.yt', 'dooood.com',
        'dood.stream', 'ds2play.com', 'doods.pro', 'ds2video.com', 'd0o0d.com', 'do0od.com',
        'd0000d.com', 'd000d.com', 'dood.li', 'dood.work', 'dooodster.com', 'vidply.com',
        'all3do.com', 'do7go.com', 'doodcdn.io', 'doply.net', 'vide0.net', 'vvide0.com',
        'd-s.io', 'dsvplay.com', 'myvidplay.com', 'doodstream.live', 'doodstream.me',
        'doodstream.link', 'dood.video'
    ]
    pattern = r'(?://|\.)((?:do*0*o*0*ds?(?:tream|ter|cdn)?|ds[2v](?:play|video)|(?:my)?v*id(?:pla?y|e0)|all3do|d-s|do(?:7go|ply))\.' \
              r'(?:[cit]om?|watch|s[ho]|cx|l[ai]|w[sf]|pm|re|yt|stream|pro|work|net|live|me|link|video))/(?:d|e)/([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id, subs=False):
        if host not in ['doodstream.com', 'myvidplay.com']:
            host = 'myvidplay.com'
        web_url = self.get_url(host, media_id)
        headers = {'User-Agent': common.FF_USER_AGENT,
                   'Referer': 'https://{0}/'.format(host)}

        r = self.net.http_GET(web_url, headers=headers)
        if r.get_url() != web_url:
            host = re.findall(r'(?://|\.)([^/]+)', r.get_url())[0]
            web_url = self.get_url(host, media_id)
        headers.update({'Referer': web_url})
        html = r.content

        match = re.search(r'<iframe\s*src="([^"]+)', html)
        if match:
            url = urllib_parse.urljoin(web_url, match.group(1))
            html = self.net.http_GET(url, headers=headers).content
        else:
            url = web_url.replace('/d/', '/e/')
            html = self.net.http_GET(url, headers=headers).content

        if subs:
            subtitles = {}
            matches = re.findall(r"""dsplayer\.addRemoteTextTrack\({src:'([^']+)',\s*label:'([^']*)',kind:'captions'""", html)
            if matches:
                matches = [(src, label) for src, label in matches if len(label) > 1]
                for src, label in matches:
                    subtitles[label] = 'https:' + src if src.startswith('//') else src

        match = re.search(r'''dsplayer\.hotkeys[^']+'([^']+).+?function\s*makePlay.+?return[^?]+([^"]+)''', html, re.DOTALL)
        if match:
            token = match.group(2)
            url = urllib_parse.urljoin(web_url, match.group(1))
            html = self.net.http_GET(url, headers=headers).content
            if 'cloudflarestorage.' in html:
                vid_src = html.strip() + helpers.append_headers(headers)
            else:
                vid_src = self.dood_decode(html) + token + str(int(time.time() * 1000)) + helpers.append_headers(headers)
            if subs:
                return vid_src, subtitles
            return vid_src

        raise ResolverError('Video Link Not Found')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://{host}/d/{media_id}')

    def dood_decode(self, data):
        t = string.ascii_letters + string.digits
        return data + ''.join([random.choice(t) for _ in range(10)])