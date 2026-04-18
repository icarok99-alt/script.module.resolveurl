# -*- coding: utf-8 -*-
from resolveurl.lib import helpers
import re
import json
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from urllib.parse import urlparse


class BRPlayerResolver(ResolveUrl):
    name = "BRPlayer"
    domains = ['brplayer.cc', 'brplayer.site', 'watch.brplayer.cc', 'watch.brplayer.site']
    pattern = r'(?://|\.)((?:watch\.)?brplayer\.(?:cc|site))/watch\?v=([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id):
        web_url = 'https://{}/watch?v={}'.format(host, media_id)

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
            raise ResolverError('BRPlayer: Falha ao carregar página → {}'.format(e))

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

            final_url = 'https://{}/m3u8/{}/{}/master.txt?s=1&id={}&cache={}'.format(
                host, uid, md5, video_id, cache
            )

            stream_headers = headers.copy()
            stream_headers.update({
                'Referer': web_url,
                'Origin': 'https://' + host,
            })

            return final_url + helpers.append_headers(stream_headers)

        except json.JSONDecodeError:
            raise ResolverError('BRPlayer: Erro ao ler JSON do player')
        except Exception as e:
            raise ResolverError('BRPlayer: Erro inesperado → {}'.format(e))

    def get_url(self, host, media_id):
        return 'https://{}/watch?v={}'.format(host, media_id)