# -*- coding: utf-8 -*-
"""
    ResolveURL Resolver - BRPlayer (2025 - Versão FINAL para URL crua)
    Aceita URL completa → https://watch.brplayer.cc/watch?v=052XEYBD
    Envia Referer e User-Agent corretamente
"""

from resolveurl.lib import helpers
import re
import json
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from urllib.parse import urlparse


class BRPlayerResolver(ResolveUrl):
    name = "BRPlayer"
    domains = ['brplayer.cc', 'brplayer.site', 'watch.brplayer.cc', 'watch.brplayer.site']

    # Aceita URLs completas do tipo watch?v=XXXXX
    pattern = r'(?://|\.)((?:watch\.)?brplayer\.(?:cc|site))/watch\?v=([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id):
        # Monta a URL completa que veio do seu add-on
        web_url = f'https://{host}/watch?v={media_id}'

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': web_url,
            'Origin': 'https://' + host,
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        try:
            html = self.net.http_GET(web_url, headers=headers).content
        except Exception as e:
            raise ResolverError(f'BRPlayer: Falha ao carregar página → {e}')

        # === MÉTODO ATUAL 2025: var video = {...} ===
        match = re.search(r'var\s+video\s*=\s*(\{.+?\});', html, re.DOTALL)
        if not match:
            raise ResolverError('BRPlayer: Bloco "var video =" não encontrado')

        try:
            video_data = json.loads(match.group(1))

            uid = video_data.get('uid')
            md5 = video_data.get('md5')
            video_id = video_data.get('id')
            cache = video_data.get('status', '1')

            if not all([uid, md5, video_id]):
                raise ResolverError('BRPlayer: Dados faltando (uid/md5/id)')

            final_url = (
                f'https://{host}/m3u8/{uid}/{md5}/master.txt'
                f'?s=1&id={video_id}&cache={cache}'
            )

            # Headers finais para o master.txt (muito importante para bypass)
            stream_headers = headers.copy()
            stream_headers.update({
                'Referer': web_url,
                'Origin': 'https://' + host,
            })

            return final_url + helpers.append_headers(stream_headers)

        except json.JSONDecodeError:
            raise ResolverError('BRPlayer: Erro ao ler JSON do player')
        except Exception as e:
            raise ResolverError(f'BRPlayer: Erro inesperado → {e}')

    def get_url(self, host, media_id):
        return f'https://{host}/watch?v={media_id}'

    # === ESSA É A MAGIA: aceita URL completa direto do seu add-on ===
    def valid_url(self, url, host):
        if url:
            parsed = urlparse(url)
            return (re.match(self.pattern, url, re.I) or
                    parsed.hostname and parsed.hostname in self.domains)
        return False