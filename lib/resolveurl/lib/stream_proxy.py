# -*- coding: utf-8 -*-
"""
stream_proxy.py — HTTP proxy local para streams de vídeo (Kodi)
"""

import logging
import os
import re
import signal
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote, urljoin

import requests

log = logging.getLogger(__name__)

# ── Configuração central ──────────────────────────────────────────────────────
DEFAULT_PORT    = 8899
CONNECT_TIMEOUT = 10          # segundos para estabelecer conexão upstream
READ_TIMEOUT    = 30          # segundos esperando dados do upstream
CHUNK_SIZE      = 32 * 1024   # 32 KB — chunks de streaming
M3U8_CHUNK_SIZE = 256 * 1024  # chunks maiores ao bufferizar playlists
MAX_WORKERS     = 20          # teto de threads no pool
ACCEPT_TIMEOUT  = 1.0         # timeout do accept() no socket servidor
MAX_HEADER_SIZE = 65_536      # limite de tamanho de header (guard flood)
UPSTREAM_RETRIES = 2          # tentativas em caso de falha de conexão

# Assinaturas de lixo que podem preceder o payload de vídeo
GARBAGE_SIGNATURES = (
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"GIF87a",              # GIF87
    b"GIF89a",              # GIF89
    b"\xff\xd8\xff",        # JPEG
    b"RIFF",                # RIFF/WEBP/AVI
    b"\x1aE\xdf\xa3",      # MKV / WebM
    b"BM",                  # BMP
)

# Atoms válidos do início de um arquivo MP4/MOV
MP4_ATOMS = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"pnot", b"uuid"}
# ─────────────────────────────────────────────────────────────────────────────


# ── Utilitários de porta ──────────────────────────────────────────────────────

def _kill_process_on_port(port: int) -> bool:
    """Mata o processo escutando em *port*. Retorna True se conseguiu."""
    candidates: list[int] = []

    for cmd in (["lsof", f"-ti:{port}"], ["fuser", f"{port}/tcp"]):
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
            for tok in out.split():
                try:
                    candidates.append(int(tok))
                except ValueError:
                    pass
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    killed = False
    for pid in set(candidates):
        if pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            killed = True
        except (ProcessLookupError, PermissionError):
            pass

    if killed:
        time.sleep(0.4)
    return killed


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _is_port_responding(port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except Exception:
            return False


# ── Proxy principal ───────────────────────────────────────────────────────────

class StreamProxy:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port     = port
        self._server  = None
        self._running = False
        self._lock    = threading.Lock()
        self._pool    = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix="sp-worker",
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True

            if not _is_port_free(self.port):
                if _is_port_responding(self.port):
                    log.info("Porta %d já respondendo — reutilizando.", self.port)
                    self._running = True
                    return True
                log.warning("Porta %d em uso mas sem resposta; tentando liberar.", self.port)
                _kill_process_on_port(self.port)
                if not _is_port_free(self.port):
                    log.error("Não foi possível liberar a porta %d.", self.port)
                    return False

            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except (AttributeError, OSError):
                    pass
                srv.bind(("127.0.0.1", self.port))
                srv.listen(32)
                srv.settimeout(ACCEPT_TIMEOUT)
                self._server  = srv
                self._running = True
                t = threading.Thread(target=self._accept_loop, daemon=True, name="sp-accept")
                t.start()
                log.info("StreamProxy ouvindo na porta %d.", self.port)
                return True
            except Exception:
                log.exception("Falha ao iniciar StreamProxy.")
                try:
                    srv.close()
                except Exception:
                    pass
                return False

    def stop(self):
        with self._lock:
            self._running = False
        try:
            self._server.close()
        except Exception:
            pass
        self._pool.shutdown(wait=False)
        log.info("StreamProxy encerrado.")

    @property
    def running(self) -> bool:
        return self._running

    # ── Loop de aceite ────────────────────────────────────────────────────────

    def _accept_loop(self):
        while self._running:
            try:
                client, _ = self._server.accept()
                self._pool.submit(self._handle, client)
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as exc:
                log.debug("Erro no accept: %s", exc)

    # ── Manipulação de requisição ─────────────────────────────────────────────

    def _handle(self, client: socket.socket):
        client.settimeout(READ_TIMEOUT)
        try:
            # Lê o header HTTP completo (pode exigir vários recv)
            raw = b""
            while b"\r\n\r\n" not in raw:
                chunk = client.recv(4096)
                if not chunk:
                    return
                raw += chunk
                if len(raw) > MAX_HEADER_SIZE:
                    self._send_error(client, 431)
                    return

            req   = raw.decode("utf-8", errors="ignore")
            lines = req.splitlines()
            if not lines:
                return

            parts  = lines[0].split()
            method = parts[0].upper() if parts else ""
            path   = parts[1] if len(parts) > 1 else ""

            if method not in ("GET", "HEAD"):
                self._send_error(client, 405)
                return

            if "/proxy?url=" not in path:
                self._send_error(client, 400)
                return

            # Extrai headers do request
            req_headers: dict[str, str] = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    req_headers[k.strip().lower()] = v.strip()

            range_header = req_headers.get("range")
            encoded = path.split("/proxy?url=", 1)[1].split(" HTTP/")[0]
            url, extra_headers = self._parse_url_headers(unquote(encoded))

            self._process_request(
                client, url, extra_headers, range_header,
                head_only=(method == "HEAD"),
            )

        except Exception as exc:
            log.debug("Erro ao processar request: %s", exc)
        finally:
            try:
                client.close()
            except Exception:
                pass

    # ── Parsing de URL + headers inline ──────────────────────────────────────

    @staticmethod
    def _parse_url_headers(value: str) -> tuple:
        """Separa 'url|Key=Value&Key2=Value2' em (url, {headers})."""
        if "|" not in value:
            return value, {}
        url, h = value.split("|", 1)
        headers = {}
        for part in h.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                headers[k] = unquote(v.replace("+", " "))
        return url, headers

    # ── Detecção de conteúdo ──────────────────────────────────────────────────

    @staticmethod
    def _is_valid_mp4_start(data: bytes) -> bool:
        """Verifica se *data* começa com um atom MP4/MOV válido."""
        if len(data) < 8:
            return False
        # Posição canônica: bytes 4-7
        if data[4:8] in MP4_ATOMS:
            return True
        # Varre uma janela pequena (alguns streams têm offset)
        for i in range(min(32, len(data) - 7)):
            if data[i + 4: i + 8] in MP4_ATOMS:
                return True
        return False

    @staticmethod
    def _has_garbage_prefix(data: bytes) -> bool:
        return any(data.startswith(sig) for sig in GARBAGE_SIGNATURES)

    @staticmethod
    def _strip_garbage(data: bytes) -> bytes:
        """Remove prefixo de formato de arquivo inválido do início dos dados."""
        for sig in GARBAGE_SIGNATURES:
            if data.startswith(sig):
                return data[len(sig):]
        return data

    # ── Processador central de requests ──────────────────────────────────────

    def _process_request(
        self,
        client: socket.socket,
        url: str,
        headers: dict,
        range_header: str | None = None,
        head_only: bool = False,
    ):
        upstream_headers = {
            "User-Agent":      headers.get("User-Agent", "Mozilla/5.0 (compatible; Kodi)"),
            "Accept":          "*/*",
            "Accept-Encoding": "identity",
        }
        # Propaga headers sensíveis quando presentes
        for key in ("Referer", "Origin", "Cookie", "Authorization"):
            if key in headers:
                upstream_headers[key] = headers[key]
        if range_header:
            upstream_headers["Range"] = range_header

        # Tentativas de conexão upstream
        resp = None
        for attempt in range(UPSTREAM_RETRIES):
            try:
                resp = requests.get(
                    url,
                    headers=upstream_headers,
                    stream=True,
                    allow_redirects=True,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                )
                break
            except requests.exceptions.ConnectionError:
                if attempt < UPSTREAM_RETRIES - 1:
                    time.sleep(1)
            except Exception:
                break

        if resp is None:
            self._send_error(client, 502)
            return

        ct          = resp.headers.get("Content-Type", "").lower()
        is_m3u8_ct  = "m3u8" in ct or "mpegurl" in ct
        is_m3u8_url = ".m3u8" in url.lower() or "cdn_stream.m3u8" in url.lower()

        first_chunk  = next(resp.iter_content(CHUNK_SIZE), b"")
        is_m3u8_body = first_chunk.lstrip().startswith(b"#EXTM3U")
        is_playlist  = is_m3u8_ct or is_m3u8_url or is_m3u8_body

        if is_playlist:
            self._handle_m3u8(client, resp, first_chunk, url, headers, head_only)
        else:
            has_garbage = self._has_garbage_prefix(first_chunk)
            is_clean    = self._is_valid_mp4_start(first_chunk)
            if has_garbage or (not is_clean and not range_header):
                self._stream_cleaned(client, resp, first_chunk, head_only)
            else:
                self._stream_direct(client, resp, first_chunk, range_header, head_only)

    # ── Playlist M3U8 ─────────────────────────────────────────────────────────

    def _handle_m3u8(self, client, response, first_chunk, url, headers, head_only):
        try:
            chunks = [first_chunk]
            for chunk in response.iter_content(M3U8_CHUNK_SIZE):
                if chunk:
                    chunks.append(chunk)
            raw_text = b"".join(chunks).decode("utf-8", errors="replace")
        except Exception as exc:
            log.debug("Erro ao ler M3U8: %s", exc)
            self._send_error(client, 502)
            return

        base      = url.rsplit("/", 1)[0] + "/"
        rewritten = self._rewrite_m3u8(raw_text, base, headers)
        body      = rewritten.encode("utf-8")

        try:
            resp_header = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/vnd.apple.mpegurl\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
            )
            client.sendall(resp_header)
            if not head_only:
                client.sendall(body)
        except Exception as exc:
            log.debug("Erro ao enviar M3U8: %s", exc)

    # ── Stream direto ─────────────────────────────────────────────────────────

    def _stream_direct(self, client, response, first_chunk, range_header, head_only):
        try:
            code = response.status_code
            if code == 206:
                hdr = b"HTTP/1.1 206 Partial Content\r\n"
                if cr := response.headers.get("Content-Range"):
                    hdr += f"Content-Range: {cr}\r\n".encode()
            else:
                hdr = b"HTTP/1.1 200 OK\r\n"

            if cl := response.headers.get("Content-Length"):
                hdr += f"Content-Length: {cl}\r\n".encode()

            ct = response.headers.get("Content-Type", "video/mp4")
            hdr += f"Content-Type: {ct}\r\n".encode()
            hdr += (
                b"Accept-Ranges: bytes\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Connection: close\r\n\r\n"
            )
            client.sendall(hdr)
        except Exception:
            return

        if head_only:
            return

        try:
            client.sendall(first_chunk)
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:
                    client.sendall(chunk)
        except Exception:
            pass

    # ── Stream com limpeza de prefixo ─────────────────────────────────────────

    def _stream_cleaned(self, client, response, first_chunk, head_only):
        try:
            client.sendall(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: video/mp4\r\n"
                b"Accept-Ranges: none\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Connection: close\r\n\r\n"
            )
        except Exception:
            return

        if head_only:
            return

        buffer = self._strip_garbage(first_chunk)
        sent   = False

        def _flush(buf: bytes) -> tuple:
            """Tenta localizar o atom ftyp e enviar a partir dele."""
            idx = buf.find(b"ftyp")
            if idx != -1:
                client.sendall(buf[max(0, idx - 4):])
                return b"", True
            if len(buf) > 65_536:
                client.sendall(buf)
                return b"", True
            return buf, False

        buffer, sent = _flush(buffer)

        for chunk in response.iter_content(CHUNK_SIZE):
            if not chunk:
                continue
            try:
                if sent:
                    client.sendall(chunk)
                else:
                    buffer = self._strip_garbage(buffer + chunk)
                    buffer, sent = _flush(buffer)
            except Exception:
                break

    # ── Reescrita de M3U8 ─────────────────────────────────────────────────────

    def _rewrite_m3u8(self, content: str, base: str, headers: dict) -> str:
        def proxify(uri: str) -> str:
            if not uri.startswith(("http://", "https://")):
                uri = urljoin(base, uri)
            if headers:
                h = "&".join(f"{k}={quote(v, safe='')}" for k, v in headers.items())
                uri = f"{uri}|{h}"
            return self.get_proxy_url(uri)

        def rewrite_uri_attr(m: re.Match) -> str:
            return f'URI="{proxify(m.group(1))}"'

        out = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                out.append(stripped)
                continue

            if stripped.startswith("#"):
                # Reescreve atributo URI= (chaves DRM, mapas de segmento, etc.)
                if "URI=" in stripped:
                    stripped = re.sub(r'URI=["\'](.*?)["\']', rewrite_uri_attr, stripped)
                out.append(stripped)
                continue

            # Linha de URL de segmento
            out.append(proxify(stripped))

        return "\n".join(out)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_proxy_url(self, url: str) -> str:
        return f"http://127.0.0.1:{self.port}/proxy?url={quote(url, safe='')}"

    def _send_error(self, client: socket.socket, code: int):
        messages = {
            400: "Bad Request",
            405: "Method Not Allowed",
            431: "Request Header Fields Too Large",
            500: "Internal Server Error",
            502: "Bad Gateway",
        }
        msg = messages.get(code, "Error")
        try:
            client.sendall(
                f"HTTP/1.1 {code} {msg}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".encode()
            )
        except Exception:
            pass


# ── Singleton thread-safe ─────────────────────────────────────────────────────

_proxy: StreamProxy | None = None
_proxy_lock = threading.Lock()


def get_proxy() -> StreamProxy | None:
    """Retorna (criando se necessário) a instância global do StreamProxy."""
    global _proxy
    with _proxy_lock:
        if _proxy is not None and not _is_port_responding(_proxy.port):
            log.warning("Proxy não está respondendo — reiniciando.")
            try:
                _proxy.stop()
            except Exception:
                pass
            _proxy = None

        if _proxy is None:
            p = StreamProxy()
            if not p.start():
                return None
            _proxy = p

        return _proxy
