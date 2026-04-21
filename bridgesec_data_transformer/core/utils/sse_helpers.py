"""
Shared SSE transport helpers.

Used by both LogStreamView (log streaming) and BulkProgressStreamView (progress streaming).
Keeping SSE formatting in one place means both streams stay consistent.
"""
from django.http import StreamingHttpResponse


def sse_event(data: str, event: str = None) -> str:
    """
    Format a single SSE message per WHATWG spec.

    SSE format:
    - Optional: event: <type>
    - Required: data: <payload>
    - Required: blank line (terminates event)

    Args:
        data:  Payload string (usually JSON)
        event: Optional event name (e.g., "complete", "error")

    Returns:
        String ending with \\n\\n (the SSE event terminator)

    Examples:
        sse_event('{"id":"1"}')
        → 'data: {"id":"1"}\\n\\n'

        sse_event('{"status":"done"}', event="complete")
        → 'event: complete\\ndata: {"status":"done"}\\n\\n'
    """
    lines = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {data}")
    lines.append("\n")   # blank line terminates the SSE event
    return "\n".join(lines)


def make_sse_response(generator) -> StreamingHttpResponse:
    """
    Wrap a generator in a StreamingHttpResponse with the correct SSE headers.

    Sets:
    - Content-Type: text/event-stream
    - Cache-Control: no-cache  (prevents proxy caching)
    - X-Accel-Buffering: no    (prevents Nginx buffering)
    """
    response = StreamingHttpResponse(generator, content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
