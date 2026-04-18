# -*- coding: utf-8 -*-
"""
Resolver para assistir.biz/selector (retorno de vídeo MP4 direto)
Compatível com ResolveURL (Kodi)
"""

from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
import re

class AssistirBizSelectorResolver(ResolveUrl):
    name = 'assistir.biz (selector MP4)'
    domains = ['assistir.biz']
    pattern = r'(?://|\.)(assistir\.biz)/(?:selector)\?([^#]+)'

    def get_url(self, host, query):
        # Monta a URL completa para o endpoint selector
        built_url = f"https://{host}/selector?{query}"
        print(f"[AssistirBizSelector] URL construída: {built_url}")
        return built_url

    def get_media_url(self, host, query):
        print(f"[AssistirBizSelector] Iniciando resolução de URL selector...")
        web_url = self.get_url(host, query)
        headers = {'User-Agent': common.RAND_UA}

        # 1️⃣ Tenta redirecionamento direto (ex: para mv.astr.digital)
        try:
            print(f"[AssistirBizSelector] Tentando helpers.get_redirect_url...")
            redirect_url = helpers.get_redirect_url(web_url, headers)
            if redirect_url and ('mv.astr.digital' in redirect_url or redirect_url.endswith('.mp4')):
                print(f"[AssistirBizSelector] Redirecionamento direto identificado: {redirect_url}")
                return redirect_url
        except Exception as e:
            print(f"[AssistirBizSelector] Falha ao obter redirecionamento: {e}")

        # 2️⃣ Caso não tenha redirecionamento HTTP, analisar HTML
        try:
            response = self.net.http_GET(web_url, headers=headers, redirect=True)
            html = response.content

            # Procurar links típicos de MP4 (mv.astr.digital ou .mp4)
            match = re.search(r'https?://mv\.astr\.digital/[^\s\'"]+', html)
            if not match:
                match = re.search(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', html)
            if match:
                video_url = match.group(0)
                print(f"[AssistirBizSelector] Link MP4 encontrado no HTML: {video_url}")
                return video_url

            # Às vezes o link vem dentro de um atributo "src" em JSON
            match_attr = re.search(r'"(https?://mv\.astr\.digital/[^\s\'"]+)"', html)
            if match_attr:
                video_url = match_attr.group(1)
                print(f"[AssistirBizSelector] Link MP4 encontrado em JSON/atributo: {video_url}")
                return video_url

            print(f"[AssistirBizSelector] Nenhum link MP4 encontrado na resposta.")
            raise ResolverError(f"Nenhum link direto MP4 encontrado em {web_url}")

        except Exception as e:
            print(f"[AssistirBizSelector] Erro durante requisição: {e}")
            raise ResolverError(f"Erro ao resolver {web_url}: {str(e)}")