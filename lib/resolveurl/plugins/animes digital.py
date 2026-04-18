import re
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl.lib import helpers, jsunpack


class AnimesDigitalResolver(ResolveUrl):
    name = 'AnimesDigital'
    domains = ['animesdigital.org', 'api.anivideo.net']
    pattern = r'(?://|\.)(animesdigital\.org|api\.anivideo\.net)/(.*)'

    def get_media_url(self, host, media_id):
        headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': 'https://animesdigital.org/',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Connection': 'keep-alive',
        }

        web_url = 'https://%s/%s' % (host, media_id)

        try:
            response = self.net.http_GET(web_url, headers=headers)
            html = response.content
            if hasattr(response._response, 'code'):
                status = response._response.code
            elif hasattr(response._response, 'getcode'):
                status = response._response.getcode()
            else:
                status = 200
        except Exception:
            raise ResolverError('Falha ao acessar a página')

        if status != 200:
            raise ResolverError('Página não carregada corretamente')

        unpacked = ''
        for packed in re.finditer(r'eval\s*\(function\(p,a,c,k,e,[rd]\).*\)', html, re.DOTALL):
            js = packed.group(0)
            if jsunpack.detect(js):
                try:
                    unpacked += jsunpack.unpack(js)
                except:
                    pass

        content = html + unpacked

        streams = re.findall(r'(https?://[^\s<>"\']+googlevideo\.com/videoplayback[^\s<>"\']*)', content)
        if not streams:
            streams = re.findall(r'(https?://[^\s<>"\']+\.(?:m3u8|mp4)[^\s<>"\']*)', content)

        if not streams:
            raise ResolverError('Nenhum stream encontrado')

        stream_url = streams[0]
        if 'googlevideo.com' in stream_url:
            for s in streams:
                if 'itag=22' in s:
                    stream_url = s
                    break

        final_headers = {
            'User-Agent': common.FF_USER_AGENT,
            'Referer': web_url,
            'Range': 'bytes=0-',
        }

        return stream_url + helpers.append_headers(final_headers)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url, re.I)
        if r:
            return r.group(1), r.group(2)
        raise ValueError('URL não suportada')

    def get_url(self, host, media_id):
        return 'https://%s/%s' % (host, media_id)