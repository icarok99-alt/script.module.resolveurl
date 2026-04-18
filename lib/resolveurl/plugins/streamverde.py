# Arquivo: streamingverde_newjeans.py
# -*- coding: utf-8 -*-

from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl import common
import re


class StreamingVerdeNewJeansResolver(ResolveUrl):
    name = "StreamingVerde (NewJeans)"
    domains = ["streamingverde.com"]

    pattern = r'(?://|\.)(streamingverde\.com)/newjeans/\?id=([^&]+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        page_url = f"https://{host}/newjeans/?id={media_id}"

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': page_url,
        }

        html = self.net.http_GET(page_url, headers=headers).content

        match = re.search(
            r'["\']file["\']\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            html,
            re.IGNORECASE
        )

        if not match:
            raise ResolverError("StreamingVerde NewJeans: Não encontrou o arquivo .mp4")

        return match.group(1)