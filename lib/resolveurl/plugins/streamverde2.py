# Arquivo: streamingverde_old.py  (ou mantenha como streamingverde.py)
# -*- coding: utf-8 -*-

from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl import common
import re


class StreamingVerdeOldResolver(ResolveUrl):
    name = "StreamingVerde (Old/PHP)"
    domains = ["streamingverde.com"]

    pattern = r'(?://|\.)(streamingverde\.com)/p\.php/?.*?[?&]id=([#0-9a-zA-Z_-]+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        media_id = media_id.replace('#', '')
        page_url = f"https://{host}/p.php?id={media_id}"

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': page_url,
        }

        html = self.net.http_GET(page_url, headers=headers).content

        match = re.search(r'videoSource\s*=\s*[\'"]([^\'"]+)', html, re.I)
        if not match:
            raise ResolverError("StreamingVerde Old: videoSource não encontrado")

        stream_url = match.group(1)
        if not stream_url.startswith("http"):
            stream_url = f"https://{host}/" + stream_url.lstrip("/")

        return stream_url