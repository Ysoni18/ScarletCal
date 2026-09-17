"""Bound HTTP input and log operational metadata without schedule contents."""

import logging
from time import monotonic
from uuid import uuid4

from starlette.responses import JSONResponse

logger = logging.getLogger('scarletcal.web')
MAX_BODY_BYTES = 200_000  # Transport byte cap; the schedule character limit is separate.


class RequestGuard:
    """Buffer at most MAX_BODY_BYTES before the JSON parser sees a request."""

    def __init__(self, app, max_body_bytes=MAX_BODY_BYTES):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request_id = uuid4().hex
        started = monotonic()
        status = 500
        response_started = False

        async def guarded_send(message):
            nonlocal status, response_started
            if message['type'] == 'http.response.start':
                response_started = True
                status = message['status']
                headers = list(message.get('headers', []))
                headers.extend([
                    (b'cache-control', b'no-store'),
                    (b'x-content-type-options', b'nosniff'),
                    (b'referrer-policy', b'no-referrer'),
                    (b'x-frame-options', b'DENY'),
                    (b'x-request-id', request_id.encode()),
                ])
                # Swagger's external scripts require a different policy.
                if scope['path'] not in ('/docs', '/redoc', '/docs/oauth2-redirect'):
                    headers.append((b'content-security-policy',
                        b"default-src 'self'; script-src 'self'; style-src 'self'; "
                        b"img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                        b"base-uri 'none'; frame-ancestors 'none'; form-action 'self'"))
                message = {**message, 'headers': headers}
            await send(message)

        async def too_large():
            await JSONResponse({'detail': 'Request is too large. Paste only your registered courses.'},
                               status_code=413)(scope, receive, guarded_send)

        try:
            for key, value in scope.get('headers', []):
                if key.lower() == b'content-length':
                    try:
                        length = int(value)
                    except ValueError:
                        length = -1
                    if length < 0:
                        await JSONResponse({'detail': 'Invalid request length.'}, status_code=400)(
                            scope, receive, guarded_send)
                        return
                    if length > self.max_body_bytes:
                        await too_large()
                        return
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    status = 499
                    return
                chunk = message.get('body', b'')
                if len(body) + len(chunk) > self.max_body_bytes:
                    await too_large()
                    return
                body.extend(chunk)
                if not message.get('more_body', False):
                    break
            delivered = False

            async def replay():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}

            await self.app(scope, replay, guarded_send)
        except Exception:
            # Exception messages/tracebacks may contain user text. Never log them.
            logger.error('request_failed request_id=%s', request_id)
            if response_started:
                raise
            await JSONResponse({
                'detail': 'Calendar service encountered an error. Please try again.',
                'request_id': request_id,
            }, status_code=500)(scope, receive, guarded_send)
        finally:
            route = scope.get('route')
            # Route templates only: no user-supplied paths, query strings, or IPs.
            logger.info('request request_id=%s route=%s status=%s duration_ms=%d',
                        request_id, getattr(route, 'path', 'unmatched'), status,
                        int((monotonic() - started) * 1000))
