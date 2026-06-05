"""
    Plugin for ResolveURL
    Copyright (C) 2020 gujal

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
import random
import string
import time
from six.moves import urllib_parse
from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

import cloudscraper


class DoodStreamResolver(ResolveUrl):
    name = 'DoodStream'
    domains = [
        'dood.watch', 'doodstream.com', 'dood.to', 'dood.so', 'dood.cx', 'dood.la', 'dood.ws',
        'dood.sh', 'doodstream.co', 'dood.pm', 'dood.wf', 'dood.re', 'dood.yt', 'dooood.com',
        'dood.stream', 'ds2play.com', 'doods.pro', 'ds2video.com', 'd0o0d.com', 'do0od.com',
        'd0000d.com', 'd000d.com', 'dood.li', 'dood.work', 'dooodster.com', 'vidply.com',
        'all3do.com', 'do7go.com', 'doodcdn.io', 'doply.net', 'vide0.net', 'vvide0.com',
        'd-s.io', 'dsvplay.com', 'myvidplay.com', 'playmogo.com'
    ]
    pattern = (
        r'(?://|\.)((?:do*0*o*0*ds?(?:tream|ter|cdn)?|ds[2v](?:play|video)|(?:my)?v*id(?:pla?y|e0)|all3do|'
        r'd-s|do(?:7go|ply)|playmogo)\.'
        r'(?:[cit]om?|watch|s[ho]|cx|l[ai]|w[sf]|pm|re|yt|stream|pro|work|net))/(?:d|e)/([0-9a-zA-Z]+)'
    )

    def get_media_url(self, host, media_id, subs=False):
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
            delay=4
        )
        if host not in ['doodstream.com', 'myvidplay.com', 'playmogo.com']:
            host = 'playmogo.com'
        web_url = self.get_url(host, media_id)

        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': web_url
        }

        r = scraper.get(web_url, headers=headers, timeout=20)
        if r.url != web_url:
            web_url = r.url
            headers['Referer'] = web_url
        html = r.text

        if subs:
            subtitles = {}
            matches = re.findall(r"""dsplayer\.addRemoteTextTrack\({src:'([^']+)',\s*label:'([^']*)',kind:'captions'""", html)
            if matches:
                matches = [(src, label) for src, label in matches if len(label) > 1]
                for src, label in matches:
                    subtitles[label] = 'https:' + src if src.startswith('//') else src

        match = re.search(r'''dsplayer\.hotkeys[^']+'([^']+).+?function\s*makePlay.+?return[^?]+([^"]+)''', html, re.DOTALL)
        if match:
            token = match.group(2).strip()
            url = urllib_parse.urljoin(web_url, match.group(1))

            resp = scraper.get(url, headers=headers, timeout=20)
            str_url = resp.text.strip()

            if str_url:
                if 'cloudflarestorage.' in str_url:
                    vid_src = str_url + helpers.append_headers(headers)
                else:
                    vid_src = self.dood_decode(str_url) + token + str(int(time.time() * 1000)) + helpers.append_headers(headers)
                if subs:
                    return vid_src, subtitles
                return vid_src

        raise ResolverError('Video Link Not Found')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://{host}/e/{media_id}')

    def dood_decode(self, data):
        t = string.ascii_letters + string.digits
        return data + ''.join([random.choice(t) for _ in range(10)])
