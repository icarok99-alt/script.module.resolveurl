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
import time
import hashlib
import base64
from random import choice
from six.moves import urllib_parse
from resolveurl.lib import helpers
from resolveurl.lib.aesgcm import python_aesgcm
from resolveurl.lib.ecdsa import SigningKey, NIST256p
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

_PROFILES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib', 'byse_profiles.json')
try:
    with open(_PROFILES_PATH, 'r') as _f:
        _PROFILES = json.load(_f)
except Exception:
    _PROFILES = []


def _get_profile():
    return choice(_PROFILES)


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
        embed_url = self.get_url(host, media_id)
        print('Byse: embed_url = {}'.format(embed_url))

        profile = _get_profile()
        client = profile.get('client', {})
        print('Byse: profile selecionado -> {} | {} {} | {}x{}'.format(
            client.get('platform', 'Unknown'),
            client.get('model', 'Desktop'),
            client.get('ua_full_version', ''),
            client.get('screen_width', ''),
            client.get('screen_height', '')
        ))
        ua = profile['ua']
        api_base = self._get_base(embed_url)
        headers = {
            'User-Agent': ua,
            'Accept': 'application/json, text/plain, */*'
        }

        api_headers = headers.copy()
        api_headers.update({
            'Origin': api_base,
            'Referer': embed_url,
            'X-Embed-Origin': urllib_parse.urlparse(embed_url).netloc,
            'X-Embed-Referer': embed_url,
            'X-Embed-Parent': embed_url,
        })

        challenge_url = '{}/api/videos/access/challenge'.format(api_base)
        try:
            resp = self.net.http_POST(challenge_url, form_data={}, headers=api_headers, jdata=True, timeout=10)
            challenge = json.loads(resp.content)
        except Exception as e:
            raise ResolverError('Erro no challenge: {}'.format(e))

        attest_data = self._make_attestation(challenge, profile['client'])
        attest_url = '{}/api/videos/access/attest'.format(api_base)
        try:
            resp = self.net.http_POST(attest_url, form_data=attest_data, headers=api_headers, jdata=True, timeout=10)
            attest = json.loads(resp.content)
        except Exception as e:
            raise ResolverError('Erro no attest: {}'.format(e))

        viewer_id = attest.get('viewer_id', '')
        device_id = attest.get('device_id', '')
        fingerprint = {
            'token': attest.get('token'),
            'viewer_id': viewer_id,
            'device_id': device_id,
            'confidence': attest.get('confidence')
        }

        api_headers['Cookie'] = 'byse_viewer_id={}; byse_device_id={}'.format(viewer_id, device_id)

        print('Byse: resolvendo PoW captcha...')
        captcha_url = '{}/api/videos/{}/embed/captcha'.format(api_base, media_id)
        try:
            resp = self.net.http_POST(captcha_url, form_data={'fingerprint': fingerprint}, headers=api_headers, jdata=True, timeout=10)
            pow_data = json.loads(resp.content)
        except Exception as e:
            raise ResolverError('Erro ao obter PoW: {}'.format(e))

        solution = self._solve_pow(pow_data.get('pow_nonce'), pow_data.get('pow_difficulty', 0), timeout_ms=30000)
        if solution is None:
            raise ResolverError('Timeout ao resolver PoW')

        verify_url = '{}/api/videos/{}/embed/captcha/verify'.format(api_base, media_id)
        verify_payload = {
            'pow_token': pow_data.get('pow_token'),
            'solution': solution,
            'fingerprint': fingerprint
        }
        try:
            resp = self.net.http_POST(verify_url, form_data=verify_payload, headers=api_headers, jdata=True, timeout=10)
            verify = json.loads(resp.content)
        except Exception as e:
            raise ResolverError('Erro na verificacao do captcha: {}'.format(e))

        if verify.get('status') != 'ok':
            raise ResolverError('Falha na verificacao do PoW')
        captcha_token = verify.get('token')

        playback_headers = api_headers.copy()
        playback_headers['X-Captcha-Token'] = captcha_token

        playback_url = '{}/api/videos/{}/embed/playback'.format(api_base, media_id)
        try:
            resp = self.net.http_POST(playback_url, form_data={'fingerprint': fingerprint}, headers=playback_headers, jdata=True, timeout=10)
            playback = json.loads(resp.content)
        except Exception as e:
            raise ResolverError('Erro no playback: {}'.format(e))

        sources = playback.get('sources')
        if sources:
            source_list = [(x.get('label'), x.get('url')) for x in sources]
            uri = helpers.pick_source(helpers.sort_sources_list(source_list))
            url = helpers.get_redirect_url(uri, headers=headers)
            return url + helpers.append_headers(headers)

        pd = playback.get('playback')
        if pd:
            iv = self.ft(pd.get('iv'))
            key = self.xn(pd.get('key_parts'), pd.get('version'))
            pl = self.ft(pd.get('payload'))
            cipher = python_aesgcm.new(key)
            ct = cipher.open(iv, pl)
            ct = json.loads(ct.decode('latin-1'))
            sources = ct.get('sources')
            if sources:
                source_list = [(x.get('label'), x.get('url')) for x in sources]
                uri = helpers.pick_source(helpers.sort_sources_list(source_list))
                return uri + helpers.append_headers(headers)

        raise ResolverError('Nenhuma fonte de video encontrada')

    def get_url(self, host, media_id):
        redirect_map = {
            'boosteradx.online': 'streamlyplayer.online',
            'byse.sx': 'streamlyplayer.online'
        }
        if host in redirect_map:
            host = redirect_map[host]
        return 'https://{}/e/{}'.format(host, media_id)

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
    def _get_base(url):
        p = urllib_parse.urlparse(url)
        return '{}://{}'.format(p.scheme, p.netloc)

    @staticmethod
    def _b64url_encode(data):
        return base64.b64encode(data).decode().replace('+', '-').replace('/', '_').replace('=', '')

    @staticmethod
    def _b64url_decode(s):
        s = s.replace('-', '+').replace('_', '/')
        padding = (4 - len(s) % 4) % 4
        return base64.b64decode(s + '=' * padding)

    _BE = 512
    _LT = _BE - 1
    _DR = 2
    _LR = 2654435761
    _HR = 2246822519

    @classmethod
    def _re(cls, t, e):
        return ((t << e) | (t >> (32 - e))) & 0xFFFFFFFF

    @classmethod
    def _ht(cls, t, e):
        return (t * e) & 0xFFFFFFFF

    @classmethod
    def _ye(cls, t):
        t[0] = (t[0] + t[1]) & 0xFFFFFFFF
        t[3] = cls._re(t[3] ^ t[0], 16)
        t[2] = (t[2] + t[3]) & 0xFFFFFFFF
        t[1] = cls._re(t[1] ^ t[2], 12)
        t[0] = (t[0] + t[1]) & 0xFFFFFFFF
        t[3] = cls._re(t[3] ^ t[0], 8)
        t[2] = (t[2] + t[3]) & 0xFFFFFFFF
        t[1] = cls._re(t[1] ^ t[2], 7)

    @classmethod
    def _hash(cls, data):
        M = 0xFFFFFFFF
        e0, e1, e2, e3 = 1779033703, 3144134277, 1013904242, 2773480762

        def ye():
            nonlocal e0, e1, e2, e3
            e0 = (e0 + e1) & M
            v = e3 ^ e0; e3 = ((v << 16) | (v >> 16)) & M
            e2 = (e2 + e3) & M
            v = e1 ^ e2; e1 = ((v << 12) | (v >> 20)) & M
            e0 = (e0 + e1) & M
            v = e3 ^ e0; e3 = ((v << 8) | (v >> 24)) & M
            e2 = (e2 + e3) & M
            v = e1 ^ e2; e1 = ((v << 7) | (v >> 25)) & M

        for b in data:
            e0 = (e0 + b) & M
            e0 = ((e0 << 7) | (e0 >> 25)) & M
            ye()
        for _ in range(8):
            ye()

        BE = 512
        LT = BE - 1
        r = [0] * BE
        for i in range(BE):
            ye()
            r[i] = (e0 ^ e2) & M

        LR = 2654435761
        HR = 2246822519
        for _ in range(2):
            for s in range(BE):
                a = r[s] & LT
                c = (r[s] + r[a]) & M
                c = ((c << 13) | (c >> 19)) & M
                c = (c ^ ((r[(s + 1) & LT] * LR) & M)) & M
                r[s] = c
                e0 = (e0 ^ c) & M
                ye()

        n = [0] * 8
        o = BE // 8
        for i in range(8):
            ye()
            s2 = e0
            a = i * o
            for c in range(o):
                d = r[a + c]
                s2 = (s2 + d) & M
                s2 = ((s2 << 5) | (s2 >> 27)) & M
                s2 = (s2 ^ ((d * HR) & M)) & M
            n[i] = (s2 ^ e2) & M
        return n

    @classmethod
    def _lzbits(cls, t):
        bits = 0
        for n in t:
            if n == 0:
                bits += 32
                continue
            return bits + (32 - n.bit_length())
        return bits

    @classmethod
    def _solve_pow(cls, nonce, difficulty, timeout_ms=30000):
        if difficulty <= 0:
            return "0"
        prefix = (nonce + ":").encode('utf-8')
        start = time.time()
        timeout_s = timeout_ms / 1000.0
        _hash = cls._hash
        _lzbits = cls._lzbits
        s = 0
        while True:
            for _ in range(4096):
                data = prefix + str(s).encode('utf-8')
                if _lzbits(_hash(data)) >= difficulty:
                    return str(s)
                s += 1
            if (time.time() - start) > timeout_s:
                return None

    def _make_attestation(self, challenge, client_data):
        sk = SigningKey.generate(curve=NIST256p)
        vk = sk.get_verifying_key()
        nonce_bytes = str(challenge.get("nonce", "")).encode('utf-8')
        signature = sk.sign(nonce_bytes, hashfunc=hashlib.sha256)
        pub_bytes = vk.to_string()
        x = self._b64url_encode(pub_bytes[:32])
        y = self._b64url_encode(pub_bytes[32:])

        return {
            "viewer_id": "",
            "device_id": "",
            "challenge_id": challenge.get("challenge_id"),
            "nonce": challenge.get("nonce"),
            "signature": self._b64url_encode(signature),
            "public_key": {
                "alg": "ES256",
                "crv": "P-256",
                "ext": True,
                "key_ops": ["verify"],
                "kty": "EC",
                "x": x,
                "y": y
            },
            "client": client_data,
            "storage": {},
            "attributes": {"entropy": "high"}
        }
