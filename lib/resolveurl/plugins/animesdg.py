"""
    Plugin for ResolveURL
    Copyright (C) 2024

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

from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl.lib import helpers
import re
import json
from urllib import error as urllib_error, parse as urllib_parse, request as urllib_request


class AnimesDGResolver(ResolveUrl):
    name = 'AnimesDG'
    domains = ['animesdigital.org']
    pattern = r'(?://|\.)(animesdigital\.org)/([A-Za-z0-9+/=]+/\d+/bg\.mp4[^\s]*)'

    def __init__(self):
        self.headers = {'User-Agent': common.FF_USER_AGENT}

    def get_media_url(self, host, media_id):
        web_url     = self.get_url(host, media_id)
        blogger_url = self._extract_blogger_url(web_url)
        sources     = self._parse_blogger_batchexecute(blogger_url)

        if not sources:
            raise ResolverError('No video sources found')

        sources.sort(key=lambda x: self.__key(x), reverse=True)
        return helpers.pick_source(sources) + helpers.append_headers(self.headers)

    def __key(self, item):
        try:
            return int(re.search(r'(\d+)', item[0]).group(1))
        except:
            return 0

    def get_url(self, host, media_id):
        return 'https://%s/%s' % (host, media_id)

    def _extract_blogger_url(self, url):
        try:
            req  = urllib_request.Request(url, headers=self.headers)
            resp = urllib_request.urlopen(req)
            html = resp.read().decode('utf-8', errors='ignore')
        except urllib_error.HTTPError as e:
            raise ResolverError('Failed to fetch page (HTTP %s): %s' % (e.code, url))
        except Exception as e:
            raise ResolverError('Failed to fetch page: %s' % str(e))

        match = re.search(r'src=["\']?(https://www\.blogger\.com/video\.g\?token=[A-Za-z0-9_-]+[^"\'<>\s]*)', html)
        if not match:
            raise ResolverError('No Blogger iframe found in page: %s' % url)

        return match.group(1).replace('&amp;', '&')

    def _parse_blogger_batchexecute(self, blogger_url):
        token_match = re.search(r'token=([A-Za-z0-9_-]+)', blogger_url)
        if not token_match:
            raise ResolverError('Could not extract token from Blogger URL: %s' % blogger_url)
        token = token_match.group(1)

        try:
            req       = urllib_request.Request(blogger_url, headers=self.headers)
            resp      = urllib_request.urlopen(req)
            page_text = resp.read().decode('utf-8', errors='ignore')
        except urllib_error.HTTPError as e:
            raise ResolverError('Failed to load Blogger page (HTTP %s): %s' % (e.code, blogger_url))
        except Exception as e:
            raise ResolverError('Failed to load Blogger page: %s' % str(e))

        sid_match = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', page_text)
        bh_match  = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', page_text)
        at_match  = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', page_text)

        if not sid_match or not bh_match:
            raise ResolverError('Failed to extract session params (FdrFJe/cfb2h) from Blogger page')

        sid = sid_match.group(1)
        bh  = bh_match.group(1)
        at  = at_match.group(1) if at_match else ''

        inner     = json.dumps([token, '', 0], separators=(',', ':'))
        freq      = json.dumps([[['WcwnYd', inner, None, 'generic']]], separators=(',', ':'))
        post_body = 'f.req=' + urllib_parse.quote(freq)
        if at:
            post_body += '&at=' + urllib_parse.quote(at)

        batch_url = (
            'https://www.blogger.com/_/BloggerVideoPlayerUi/data/batchexecute'
            '?rpcids=WcwnYd&source-path=%2Fvideo.g'
            '&f.sid={sid}&bl={bh}&hl=en-US&_reqid=100001&rt=c'
        ).format(sid=urllib_parse.quote(sid), bh=urllib_parse.quote(bh))

        batch_headers = dict(self.headers)
        batch_headers.update({
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'X-Same-Domain': '1',
            'Origin': 'https://www.blogger.com',
            'Referer': blogger_url,
        })

        try:
            req2       = urllib_request.Request(batch_url, data=post_body.encode('utf-8'), headers=batch_headers)
            batch_resp = urllib_request.urlopen(req2)
            batch_body = batch_resp.read().decode('utf-8', errors='ignore')
        except urllib_error.HTTPError as e:
            raise ResolverError('batchexecute request failed (HTTP %s)' % e.code)
        except Exception as e:
            raise ResolverError('batchexecute request failed: %s' % str(e))

        video_url = self._parse_batchexecute_response(batch_body)
        if not video_url:
            raise ResolverError('No video URL found in Blogger batchexecute response')

        if 'itag=22' in video_url:
            quality = '720p'
        elif 'itag=18' in video_url:
            quality = '360p'
        else:
            quality = 'Unknown Quality'

        return [(quality, video_url)]

    def _parse_batchexecute_response(self, body):
        video_url = None

        for line in body.splitlines():
            if 'wrb.fr' not in line:
                continue
            try:
                outer = json.loads(line)
            except ValueError:
                continue

            for entry in outer:
                if not isinstance(entry, list) or len(entry) < 3:
                    continue
                if entry[0] != 'wrb.fr' or entry[1] != 'WcwnYd':
                    continue
                try:
                    data = json.loads(entry[2])
                except (ValueError, TypeError):
                    continue

                streams = None
                for elem in data:
                    if isinstance(elem, list) and elem and isinstance(elem[0], list):
                        streams = elem
                        break

                if not streams:
                    continue

                mp4_urls = []
                for stream in streams:
                    if not isinstance(stream, list) or not stream:
                        continue
                    url = stream[0]
                    if not isinstance(url, str):
                        continue
                    if 'mime=video%2Fmp4' in url or 'mime=video/mp4' in url:
                        mp4_urls.append(url)

                for u in mp4_urls:
                    if 'itag=22' in u:
                        video_url = u
                        break

                if not video_url:
                    for u in mp4_urls:
                        if 'itag=18' in u:
                            video_url = u
                            break

                if not video_url and mp4_urls:
                    video_url = mp4_urls[0]

                if not video_url and streams and isinstance(streams[0], list) and streams[0]:
                    candidate = streams[0][0]
                    if isinstance(candidate, str):
                        video_url = candidate

            if video_url:
                break

        if not video_url:
            gv_match = re.search(r'https://[^"\\]+\.googlevideo\.com/[^"\\]+', body)
            if gv_match:
                video_url = gv_match.group(0)

        return video_url