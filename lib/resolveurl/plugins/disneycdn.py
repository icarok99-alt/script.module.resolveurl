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

import re
import binascii
import json
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl import common
from six.moves import urllib_parse
from resolveurl.lib.pyaes import AESModeOfOperationCBC, Decrypter
from resolveurl.lib import stream_proxy

class DisneyCDNResolver(ResolveUrl):
    name = 'DisneyCDN'
    domains = ['disneycdn.net', 'png.strp2p.com', 'embedplayapiupn.upns.xyz']
    pattern = r'https?://(?:www\.)?((?:disneycdn\.net|png\.strp2p\.com|embedplayapiupn\.upns\.xyz))/#([A-Za-z0-9]+)'

    def get_media_url(self, host, media_id):

        api_url = f'https://{host}/api/v1/video?id={media_id}'

        referer = f'https://{host}/'
        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': referer,
            'Origin': referer
        }

        try:
            response = self.net.http_GET(api_url, headers=headers)
            enc_data = response.content
        except Exception as e:
            raise ResolverError(f'Erro ao fazer requisição: {e}')

        if isinstance(enc_data, bytes):
            enc_data = enc_data.decode('utf-8').strip()
        elif isinstance(enc_data, str):
            enc_data = enc_data.strip()
        else:
            raise ResolverError('Formato inesperado do conteúdo criptografado')

        if not enc_data:
            raise ResolverError('Conteúdo criptografado não encontrado')

        try:
            enc_bytes = binascii.unhexlify(enc_data)
        except Exception as e:
            raise ResolverError(f'Erro ao converter hex para bytes: {e}')

        try:
            key = b'kiemtienmua911ca'
            iv = b'1234567890oiuytr'
            decrypter = Decrypter(AESModeOfOperationCBC(key, iv))
            dec_data = decrypter.feed(enc_bytes) + decrypter.feed()
            dec_str = dec_data.decode('utf-8') if isinstance(dec_data, bytes) else dec_data
        except Exception as e:
            raise ResolverError(f'Erro na descriptografia: {e}')

        try:
            dec_json = json.loads(dec_str)
        except Exception as e:
            raise ResolverError(f'Erro ao interpretar JSON: {e}')

        stream_url = dec_json.get('cf') if isinstance(dec_json, dict) else None

        if not stream_url:
            stream_url = dec_json.get('source') if isinstance(dec_json, dict) else None

        if not stream_url:
            def find_urls_in_json(obj):
                urls = []
                if isinstance(obj, dict):
                    for v in obj.values():
                        urls.extend(find_urls_in_json(v))
                elif isinstance(obj, list):
                    for item in obj:
                        urls.extend(find_urls_in_json(item))
                elif isinstance(obj, str):
                    if 'http' in obj:
                        urls.append(obj)
                return urls

            urls_found = find_urls_in_json(dec_json)
            if not urls_found:
                raise ResolverError('Nenhum link de stream encontrado no JSON')
            stream_url = urls_found[0]

        headers.update({'Origin': referer})

        proxy = stream_proxy.get_proxy()
        if proxy:
            return proxy.get_proxy_url(stream_url + helpers.append_headers(headers))

        return stream_url + helpers.append_headers(headers)
