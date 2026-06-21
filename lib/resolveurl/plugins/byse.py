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
from random import choice
from six.moves import urllib_parse
from resolveurl.lib import helpers
from resolveurl.lib.aesgcm import python_aesgcm
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

_PROFILES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib', 'byse_profiles.json')
try:
    with open(_PROFILES_PATH, 'r') as _f:
        _PROFILES = json.load(_f)
except Exception:
    _PROFILES = []


def _get_profile():
    return choice(_PROFILES) if _PROFILES else {}


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

        profile = _get_profile()
        client = profile.get('client', {})
        ua = profile.get('ua', 'Mozilla/5.0 (Linux; Android 13; SM-G780G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36')

        headers = {
            'User-Agent': ua,
            'Accept': 'application/json, text/plain, */*',
            'Origin': ref.rstrip('/'),
            'Referer': web_url,
            'X-Embed-Origin': urllib_parse.urlparse(web_url).netloc,
            'X-Embed-Referer': web_url,
            'X-Embed-Parent': web_url
        }

        chal_resp = self.net.http_POST(f'{ref}api/videos/access/challenge', headers=headers, form_data={})
        challenge = json.loads(chal_resp.content)

        attest_payload = self.wn(challenge, client)
        att_resp = self.net.http_POST(f'{ref}api/videos/access/attest', headers=headers, form_data=attest_payload, jdata=True)
        attest = json.loads(att_resp.content)

        fingerprint = {
            'token': attest.get('token'),
            'viewer_id': attest.get('viewer_id'),
            'device_id': attest.get('device_id'),
            'confidence': attest.get('confidence')
        }

        headers['Cookie'] = f"byse_viewer_id={fingerprint['viewer_id']}; byse_device_id={fingerprint['device_id']}"

        cap_resp = self.net.http_POST(f'{ref}api/videos/{media_id}/embed/captcha', 
                                     headers=headers, form_data={'fingerprint': fingerprint}, jdata=True)
        captcha = json.loads(cap_resp.content)

        solution = self.er(captcha.get('pow_nonce'), captcha.get('pow_difficulty'))
        if not solution:
            raise ResolverError('PoW timeout')

        verify_data = {
            'pow_token': captcha.get('pow_token'),
            'solution': solution,
            'fingerprint': fingerprint
        }
        ver_resp = self.net.http_POST(f'{ref}api/videos/{media_id}/embed/captcha/verify',
                                     headers=headers, form_data=verify_data, jdata=True)
        verify = json.loads(ver_resp.content)
        headers['X-Captcha-Token'] = verify.get('token')

        pb_resp = self.net.http_POST(f'{ref}api/videos/{media_id}/embed/playback',
                                    headers=headers, form_data={'fingerprint': fingerprint}, jdata=True)
        data = json.loads(pb_resp.content)

        if 'playback' in data:
            pd = data['playback']
            try:
                iv = self.ft(pd.get('iv'))
                key = self.xn(pd.get('key_parts'), pd.get('version'))
                payload = self.ft(pd.get('payload'))

                cipher = python_aesgcm.new(key)
                decrypted_bytes = cipher.open(iv, payload)
                sources_data = json.loads(decrypted_bytes.decode('utf-8'))

                sources = sources_data.get('sources', [])
                if sources:
                    sources_list = [(s.get('label'), s.get('url')) for s in sources]
                    uri = helpers.pick_source(helpers.sort_sources_list(sources_list))
                    if uri.startswith('/'):
                        uri = urllib_parse.urljoin(ref, uri)
                    return uri + helpers.append_headers(headers)
            except Exception:
                pass

        sources = data.get('sources')
        if sources:
            sources_list = [(x.get('label'), x.get('url')) for x in sources]
            uri = helpers.pick_source(helpers.sort_sources_list(sources_list))
            if uri.startswith('/'):
                uri = urllib_parse.urljoin(ref, uri)
            return uri + helpers.append_headers(headers)

        raise ResolverError('Video Link Not Found')

    def get_url(self, host, media_id):
        if host in ['boosteradx.online', 'byse.sx']:
            host = 'streamlyplayer.online'
        return self._default_get_url(host, media_id, 'https://{host}/e/{media_id}')

    @staticmethod
    def ft(e):
        if not e: return b''
        t = e.replace('-', '+').replace('_', '/')
        return helpers.b64decode(t, binary=True)

    def xn(self, e, v):
        if not e: return b''
        if v:
            v = int(v)
            e = [e[v-1], e[-1]]
        t = [self.ft(x) for x in e]
        return b''.join(t)

    @staticmethod
    def wn(ch, client_data):
        from resolveurl.lib.ecdsa import SigningKey, NIST256p
        sk = SigningKey.generate(curve=NIST256p)
        vk = sk.verifying_key
        nonce = ch.get('nonce', '')

        signature = sk.sign(nonce.encode('utf-8'), hashfunc=hashlib.sha256)
        pub_bytes = vk.to_string()

        pub = {
            "crv": "P-256",
            "ext": True,
            "key_ops": ["verify"],
            "kty": "EC",
            "x": base64.b64encode(pub_bytes[:32]).decode().replace('+','-').replace('/','_').replace('=',''),
            "y": base64.b64encode(pub_bytes[32:]).decode().replace('+','-').replace('/','_').replace('=','')
        }

        sig = base64.b64encode(signature).decode().replace('+','-').replace('/','_').replace('=','')

        return {
            "viewer_id": "",
            "device_id": "",
            "challenge_id": ch.get("challenge_id"),
            "nonce": nonce,
            "signature": sig,
            "public_key": pub,
            "client": client_data,
            "storage": {},
            "attributes": {"entropy": "high"}
        }

    def er(self, t, e, r=35.0):
        if e <= 0: return "0"
        prefix = t + ":"
        start = time.time()
        s = 0
        while True:
            for _ in range(8192):
                if _wr(_gr((prefix + str(s)).encode())) >= e:
                    return str(s)
                s += 1
            if time.time() - start > r:
                return None


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
    for i in t:
        e[0] = (e[0] + i) & m
        e[0] = _re(e[0], 7)
        _ye(e)
    for _ in range(8):
        _ye(e)
    r = [0] * 512
    for i in range(512):
        _ye(e)
        r[i] = (e[0] ^ e[2]) & m
    for _ in range(2):
        for s in range(512):
            a = r[s] & 511
            c = (r[s] + r[a]) & m
            c = _re(c, 13)
            c = (c ^ ((r[(s + 1) & 511] * 2654435761) & m)) & m
            r[s] = c
            e[0] = (e[0] ^ c) & m
            _ye(e)
    n = [0] * 8
    for i in range(8):
        _ye(e)
        s = e[0]
        for c in range(64):
            d = r[i*64 + c]
            s = (s + d) & m
            s = _re(s, 5)
            s = (s ^ ((d * 2246822519) & m)) & m
        n[i] = (s ^ e[2]) & m
    return n


def _wr(t):
    e = 0
    for r in t:
        n = int(r)
        if n == 0:
            e += 32
            continue
        return e + (32 - n.bit_length())
    return e
