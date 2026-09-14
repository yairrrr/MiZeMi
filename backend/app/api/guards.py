"""Small, in-process HTTP abuse limits for a single classroom server."""
from collections import deque
from time import monotonic

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send

MAX_BODY_BYTES = 16_384
MAX_CLIENT_BUCKETS = 2048


class ClassroomHttpGuard:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._requests: dict[str, deque[float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def secure_send(message):
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                headers['Cache-Control'] = 'no-store'
                headers['X-Content-Type-Options'] = 'nosniff'
                headers['Referrer-Policy'] = 'no-referrer'
                headers['X-Frame-Options'] = 'DENY'
            await send(message)

        async def reject(status, message):
            response = JSONResponse({'error': {'code': 'VALIDATION_ERROR', 'message': message}}, status_code=status)
            await response(scope, receive, secure_send)

        if scope['method'] == 'POST':
            now = monotonic()
            self._requests = {ip: times for ip, times in self._requests.items() if times and times[-1] > now - 60}
            ip = (scope.get('client') or ('unknown', 0))[0]
            if ip not in self._requests and len(self._requests) >= MAX_CLIENT_BUCKETS:
                await reject(429, 'The server is busy. Please try again in a minute.')
                return
            times = self._requests.setdefault(ip, deque())
            while times and times[0] <= now - 60:
                times.popleft()
            # Classroom phones may share one NAT IP; allow a full class to join.
            if len(times) >= 240:
                await reject(429, 'Too many requests. Please try again in a minute.')
                return
            times.append(now)
            length = Headers(scope=scope).get('content-length')
            if length is not None and (not length.isascii() or not length.isdigit()
                                       or len(length.lstrip('0')) > len(str(MAX_BODY_BYTES))
                                       or int(length.lstrip('0') or '0') > MAX_BODY_BYTES):
                await reject(413, 'The request is too large.')
                return
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > MAX_BODY_BYTES:
                    await reject(413, 'The request is too large.')
                    return
                if not message.get('more_body', False):
                    break
            consumed = False

            async def bounded_receive():
                nonlocal consumed
                if consumed:
                    return await receive()
                consumed = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}

            await self.app(scope, bounded_receive, secure_send)
            return
        await self.app(scope, receive, secure_send)
