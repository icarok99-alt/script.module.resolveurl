# -*- coding: utf-8 -*-
"""
EmbedPlayer resolver para ResolveURL
Suporte para embedplayer1.xyz e llanfairpwllgwyngyll.com
Agora simulando o iframe igual ao api_vod.py
"""

import json
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl.lib import helpers


class EmbedPlayerResolver(ResolveUrl):
    name = "EmbedPlayer"
    domains = ["embedplayer1.xyz", "llanfairpwllgwyngyll.com"]
    pattern = r'https?://(?:www\.)?(embedplayer1\.xyz|llanfairpwllgwyngyll\.com)/video/([A-Za-z0-9]+)'

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0"
        )

    def get_media_url(self, host, media_id):
        try:
            base_url = f"https://{host}"
            video_url = f"{base_url}/video/{media_id}"
            print(f"[EmbedPlayer] Base URL: {base_url}")
            print(f"[EmbedPlayer] Video URL: {video_url}")

            # 1. GET no vídeo simulando iframe → captura cookies
            r = self.net.http_GET(
                video_url,
                headers={'User-Agent': self.user_agent, 'sec-fetch-dest': 'iframe'}
            )
            print(f"[EmbedPlayer] GET {video_url} -> OK")
            cookies_dict = self.net.get_cookies(base_url)
            print(f"[EmbedPlayer] Cookies capturados: {cookies_dict}")
            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

            # 2. POST para player/index.php
            api_url = f"{base_url}/player/index.php?data={media_id}&do=getVideo"
            headers = {
                'User-Agent': self.user_agent,
                'Origin': base_url,
                'Referer': video_url,
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            if cookie_string:
                headers['Cookie'] = cookie_string

            print(f"[EmbedPlayer] POST {api_url} headers: {headers}")
            response = self.net.http_POST(
                api_url,
                form_data={'hash': media_id, 'r': base_url},
                headers=headers
            ).content

            if not response or not response.strip().startswith("{"):
                print(f"[EmbedPlayer] Resposta inválida recebida: {response[:200]}")
                raise ResolverError("Resposta inválida recebida do servidor EmbedPlayer")

            data_json = json.loads(response)
            print(f"[EmbedPlayer] JSON recebido: {data_json}")

            # securedLink (direto)
            if 'securedLink' in data_json and data_json['securedLink']:
                link = data_json['securedLink'] + helpers.append_headers({'User-Agent': self.user_agent})
                print(f"[EmbedPlayer] securedLink encontrado: {link}")
                return link

            # videoSource (m3u8)
            if 'videoSource' in data_json and data_json['videoSource']:
                link = data_json['videoSource'] + helpers.append_headers({'User-Agent': self.user_agent})
                print(f"[EmbedPlayer] videoSource encontrado: {link}")
                return link

            raise ResolverError(f"Nenhum link válido retornado do EmbedPlayer. JSON: {data_json}")

        except Exception as e:
            print(f"[EmbedPlayer] Erro: {str(e)}")
            raise ResolverError(f"Erro no resolver EmbedPlayer: {e}")

    def get_url(self, host, media_id):
        return f"https://{host}/video/{media_id}"
