"""
    Plugin for ResolveURL
    Copyright (C) 2025 gujal

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

import json
import os
import base64
import hashlib
import time
import random
from six.moves import urllib_parse
from resolveurl.lib import helpers
from resolveurl.lib.aesgcm import python_aesgcm
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

def _b64h(seed):
    return base64.b64encode(hashlib.sha256(str(seed).encode()).digest()).decode().replace('+', '-').replace('/', '_').replace('=', '')


_ANDROID_PROFILES = [
    {
        "user_agent": "Mozilla/5.0 (Linux; Android 11; X96 Max+) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "model": "X96 Max+",
        "platform_version": "11.0.0",
        "hardware_concurrency": 4,
        "device_memory": 2,
        "pixel_ratio": 1,
        "screen_width": 1280,
        "screen_height": 720,
        "webgl_vendor": "Google Inc. (ARM)",
        "webgl_renderer": "ANGLE (ARM, Mali-G31 MP2, OpenGL ES 3.2)",
        "touch_points": 1,
        "pointer_type": "coarse",
    },
    {
        "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-A037F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "model": "SM-A037F",
        "platform_version": "11.0.0",
        "hardware_concurrency": 4,
        "device_memory": 2,
        "pixel_ratio": 1.5,
        "screen_width": 720,
        "screen_height": 1600,
        "webgl_vendor": "Google Inc. (ARM)",
        "webgl_renderer": "ANGLE (ARM, Mali-G57 MP1, OpenGL ES 3.2)",
        "touch_points": 5,
        "pointer_type": "coarse,hover,touch",
    },
    {
        "user_agent": "Mozilla/5.0 (Linux; Android 10; TX6s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "model": "TX6s",
        "platform_version": "10.0.0",
        "hardware_concurrency": 4,
        "device_memory": 2,
        "pixel_ratio": 1,
        "screen_width": 1280,
        "screen_height": 720,
        "webgl_vendor": "Google Inc. (ARM)",
        "webgl_renderer": "ANGLE (ARM, Mali-G31 MP2, OpenGL ES 3.2)",
        "touch_points": 1,
        "pointer_type": "coarse",
    },
    {
        "user_agent": "Mozilla/5.0 (Linux; Android 10; Redmi 9A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "model": "Redmi 9A",
        "platform_version": "10.0.0",
        "hardware_concurrency": 4,
        "device_memory": 2,
        "pixel_ratio": 1.5,
        "screen_width": 720,
        "screen_height": 1600,
        "webgl_vendor": "Google Inc. (ARM)",
        "webgl_renderer": "ANGLE (ARM, Mali-G52 MC2, OpenGL ES 3.2)",
        "touch_points": 5,
        "pointer_type": "coarse,hover,touch",
    },
]


def generate_client():
    p = random.choice(_ANDROID_PROFILES)
    ua = p["user_agent"]
    r = random.random()
    return {
        "user_agent": ua,
        "architecture": "",
        "bitness": "",
        "platform": "Android",
        "platform_version": p["platform_version"],
        "model": p["model"],
        "ua_full_version": "137.0.7337.0",
        "brand_full_versions": [
            {"brand": "Chromium", "version": "137.0.7337.0"},
            {"brand": "Not/A)Brand", "version": "24.0.0.0"}
        ],
        "pixel_ratio": p["pixel_ratio"],
        "screen_width": p["screen_width"],
        "screen_height": p["screen_height"],
        "color_depth": 24,
        "languages": ["pt-BR"],
        "timezone": "America/Recife",
        "hardware_concurrency": p["hardware_concurrency"],
        "device_memory": p["device_memory"],
        "touch_points": p["touch_points"],
        "webgl_vendor": p["webgl_vendor"],
        "webgl_renderer": p["webgl_renderer"],
        "canvas_hash": _b64h(r),
        "audio_hash": _b64h(r + 1),
        "webgl_params_hash": _b64h(r + 2),
        "fonts_hash": _b64h(r + 3),
        "codecs_hash": _b64h(r + 4),
        "media_devices": "ai1ao1vi4",
        "pointer_type": p["pointer_type"],
        "extra": {
            "vendor": "Google Inc.",
            "appVersion": ua[len("Mozilla/"):]
        }
    }


def _re(t, e):
    return (t << e | t >> (32 - e)) & 0xFFFFFFFF


def _ye(t):
    m = 0xFFFFFFFF
    t[0] = (t[0] + t[1]) & m
    t[3] = _re(t[3] ^ t[0], 16)
    t[2] = (t[2] + t[3]) & m
    t[1] = _re(t[1] ^ t[2], 12)
    t[0] = (t[0] + t[1]) & m
    t[3] = _re(t[3] ^ t[0], 8)
    t[2] = (t[2] + t[3]) & m
    t[1] = _re(t[1] ^ t[2], 7)


def _gr(t):
    m = 0xFFFFFFFF
    e = [1779033703, 3144134277, 1013904242, 2773480762]
    be, lt, dr, lr, hr = 512, 511, 2, 2654435761, 2246822519
    for i in t:
        e[0] = (e[0] + i) & m
        e[0] = _re(e[0], 7)
        _ye(e)
    for _ in range(8):
        _ye(e)
    r = [0] * be
    for i in range(be):
        _ye(e)
        r[i] = (e[0] ^ e[2]) & m
    for i in range(dr):
        for s in range(be):
            a = r[s] & lt
            c = (r[s] + r[a]) & m
            c = _re(c, 13)
            c = (c ^ ((r[(s + 1) & lt] * lr) & m)) & m
            r[s] = c
            e[0] = (e[0] ^ c) & m
            _ye(e)
    n = [0] * 8
    o = int(be / 8)
    for i in range(8):
        _ye(e)
        s = e[0]
        a = i * o
        for c in range(o):
            d = r[a + c]
            s = (s + d) & m
            s = _re(s, 5)
            s = (s ^ ((d * hr) & m)) & m
        n[i] = (s ^ e[2]) & m
    return n


def _wr(t):
    e = 0
    for r in range(len(t)):
        n = int(t[r])
        if n == 0:
            e += 32
            continue
        return e + (32 - n.bit_length())
    return e


class ByseResolver(ResolveUrl):
    name = 'Byse'
    domains = [
        'f16px.com', 'bysesayeveum.com', 'bysetayico.com', 'bysevepoin.com', 'bysezejataos.com',
        'bysekoze.com', 'bysesukior.com', 'bysejikuar.com', 'bysefujedu.com', 'bysedikamoum.com',
        'bysebuho.com', "byse.sx", 'filemoon.sx', 'filemoon.to', 'filemoon.in', 'filemoon.link',
        'filemoon.wf', 'cinegrab.com', 'filemoon.eu', 'filemoon.art', 'moonmov.pro', '96ar.com',
        'kerapoxy.cc', 'furher.in', '1azayf9w.xyz', '81u6xl9d.xyz', 'smdfs40r.skin', 'c1z39.com',
        'bf0skv.org', 'z1ekv717.fun', 'l1afav.net', '222i8x.lol', '8mhlloqo.fun', 'f51rm.com',
        'xcoic.com', 'filemoon.nl', 'boosteradx.online', 'streamlyplayer.online', 'bysewihe.com',
        'byselapuix.com', 'embedplaybyse.top'
    ]
    pattern = (
        r'(?://|\.)((?:filemoon|cinegrab|moonmov|kerapoxy|furher|1azayf9w|81u6xl9d|f16px|embedplaybyse|'
        r'smdfs40r|bf0skv|z1ekv717|l1afav|222i8x|8mhlloqo|96ar|xcoic|f51rm|c1z39|boosteradx|vepoin|'
        r'byse(?:sayeveum|tayico|zejataos|koze|sukior|jikuar|fujedu|dikamoum|buho|wihe|lapuix)?)'
        r'\.(?:sx|top?|s?k?in|link|nl|wf|com|eu|art|pro|cc|xyz|org|fun|net|lol|online))'
        r'/(?:(?:e|d|download)/)?([0-9a-zA-Z]+)'
    )

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        ref = urllib_parse.urljoin(web_url, '/')

        client = generate_client()

        headers = {
            'User-Agent': client["user_agent"],
            'Accept': 'application/json, text/plain, */*',
            'Origin': ref[:-1],
            'Referer': web_url,
            'X-Embed-Origin': urllib_parse.urlparse(web_url).netloc,
            'X-Embed-Referer': web_url,
            'X-Embed-Parent': web_url
        }

        challenge_url = '{0}api/videos/access/challenge'.format(ref)
        resp = self.net.http_POST(challenge_url, headers=headers, form_data={})
        challenge = json.loads(resp.content)

        attest_url = '{0}api/videos/access/attest'.format(ref)
        resp = self.net.http_POST(attest_url, headers=headers, form_data=self.wn(challenge, client), jdata=True)
        attest = json.loads(resp.content)

        fingerprint = {
            'token': attest.get('token'),
            'viewer_id': attest.get('viewer_id'),
            'device_id': attest.get('device_id'),
            'confidence': attest.get('confidence')
        }

        headers['Cookie'] = 'byse_viewer_id={}; byse_device_id={}'.format(
            fingerprint['viewer_id'], fingerprint['device_id']
        )

        captcha_url = '{0}api/videos/{1}/embed/captcha'.format(ref, media_id)
        resp = self.net.http_POST(captcha_url, headers=headers, form_data={'fingerprint': fingerprint}, jdata=True)
        captcha = json.loads(resp.content)

        solution = self.er(captcha.get('pow_nonce'), captcha.get('pow_difficulty'))
        if solution is None:
            raise ResolverError('Unable to solve captcha')

        verify_url = '{0}api/videos/{1}/embed/captcha/verify'.format(ref, media_id)
        post_data = {'pow_token': captcha.get('pow_token'), 'solution': solution, 'fingerprint': fingerprint}
        resp = self.net.http_POST(verify_url, headers=headers, form_data=post_data, jdata=True)
        verify = json.loads(resp.content)
        headers.update({'X-Captcha-Token': verify.get('token')})

        playback_url = '{0}api/videos/{1}/embed/playback'.format(ref, media_id)
        resp = self.net.http_POST(playback_url, headers=headers, form_data={'fingerprint': fingerprint}, jdata=True)
        data = json.loads(resp.content)

        sources = data.get('sources')
        if sources:
            sources = [(x.get('label'), x.get('url')) for x in sources]
            uri = helpers.pick_source(helpers.sort_sources_list(sources))
            if uri.startswith('/'):
                uri = urllib_parse.urljoin(ref, uri)
            url = helpers.get_redirect_url(uri, headers=headers)
            return url + helpers.append_headers(headers)

        pd = data.get('playback')
        if pd:
            iv = self.ft(pd.get('iv'))
            key = self.xn(pd.get('key_parts'), pd.get('version'))
            pl = self.ft(pd.get('payload'))
            cipher = python_aesgcm.new(key)
            ct = cipher.open(iv, pl)
            ct = json.loads(ct.decode('latin-1'))
            sources = ct.get('sources')
            if sources:
                sources = [(x.get('label'), x.get('url')) for x in sources]
                uri = helpers.pick_source(helpers.sort_sources_list(sources))
                headers.pop('X-Embed-Parent', None)
                if 'X-Captcha-Token' in headers:
                    headers.pop('X-Captcha-Token')
                return uri + helpers.append_headers(headers)

        raise ResolverError('Video Link Not Found')

    def get_url(self, host, media_id):
        redirect_domains = ['boosteradx.online', 'byse.sx']
        if host in redirect_domains:
            host = 'streamlyplayer.online'
        return self._default_get_url(host, media_id, 'https://{host}/e/{media_id}')

    @staticmethod
    def ft(e):
        t = e.replace('-', '+').replace('_', '/')
        return helpers.b64decode(t, binary=True)

    def xn(self, e, v):
        if v:
            v = int(v)
            e = [e[v - 1], e[len(e) - v]]
        t = list(map(self.ft, e))
        return b''.join(t)

    @staticmethod
    def wn(ch, client_data=None):
        from resolveurl.lib.ecdsa import SigningKey, NIST256p
        sk = SigningKey.generate(curve=NIST256p)
        vk = sk.verifying_key
        nonce = ch.get('nonce', '')

        signature = sk.sign(nonce.encode('utf-8'), hashfunc=hashlib.sha256)
        pub_bytes = vk.to_string()

        pub = {
            'crv': 'P-256', 'ext': True, 'key_ops': ['verify'], 'kty': 'EC',
            'x': base64.b64encode(pub_bytes[:32]).decode().replace('+', '-').replace('/', '_').replace('=', ''),
            'y': base64.b64encode(pub_bytes[32:]).decode().replace('+', '-').replace('/', '_').replace('=', '')
        }
        sig = base64.b64encode(signature).decode().replace('+', '-').replace('/', '_').replace('=', '')

        return {
            'viewer_id': '',
            'device_id': '',
            'challenge_id': ch.get('challenge_id'),
            'nonce': nonce,
            'signature': sig,
            'public_key': pub,
            'client': client_data or {},
            'storage': {},
            'attributes': {'entropy': 'high'}
        }

    def er(self, t, e, r=30.0):
        if e <= 0:
            return '0'
        prefix = t + ':'
        start = time.time()
        s = 0
        while True:
            for _ in range(8192):
                if _wr(_gr((prefix + str(s)).encode())) >= e:
                    return str(s)
                s += 1
            if time.time() - start > r:
                return None
