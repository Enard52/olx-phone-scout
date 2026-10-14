"""httpx transport that sends requests through curl_cffi with a browser TLS fingerprint.

OLX's CloudFront rejects httpx's TLS handshake with 403 regardless of headers;
impersonating Chrome's fingerprint passes. Plugging in at the transport level keeps
httpx (and PoliteClient's pacing/retries/redirects) unchanged on top.
"""

from typing import cast

import httpx
from curl_cffi import CurlError
from curl_cffi.requests import AsyncSession, HttpMethod, Response

IMPERSONATE = "chrome"
# curl_cffi negotiates these itself and returns an already-decoded body. User-Agent comes from
# the impersonated browser so it matches the TLS fingerprint (a mismatched UA gets 403 too).
_SKIP_REQUEST_HEADERS = {"host", "content-length", "connection", "accept-encoding", "user-agent"}
_SKIP_RESPONSE_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


class BrowserTransport(httpx.AsyncBaseTransport):
    def __init__(self, impersonate: str = IMPERSONATE) -> None:
        self._session: AsyncSession[Response] = AsyncSession(impersonate=impersonate)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        headers = {
            k: v for k, v in request.headers.items() if k.lower() not in _SKIP_REQUEST_HEADERS
        }
        timeout = request.extensions.get("timeout", {}).get("read")
        try:
            resp = await self._session.request(
                cast(HttpMethod, request.method),
                str(request.url),
                headers=headers,
                data=await request.aread() or None,
                timeout=timeout,
                allow_redirects=False,  # httpx follows redirects itself
            )
        except CurlError as exc:
            raise httpx.NetworkError(str(exc), request=request) from exc
        resp_headers = [
            (k, v)
            for k, v in resp.headers.multi_items()
            if v is not None and k.lower() not in _SKIP_RESPONSE_HEADERS
        ]
        return httpx.Response(
            resp.status_code, headers=resp_headers, content=resp.content, request=request
        )

    async def aclose(self) -> None:
        await self._session.close()
