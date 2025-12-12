import contextvars
from dataclasses import dataclass, asdict
import logging


@dataclass
class RequestContext:
    request_id: str = "-"
    user_id: str = "-"
    path: str = "-"
    method: str = "-"

_context_var = contextvars.ContextVar(
    "request_context",
    default=RequestContext(),
)


def set_request_context(**kwargs):
    """
    request_id, user_id, path, method 중 필요한 것만 키워드로 넘기면 됨
    """
    ctx = _context_var.get()
    data = asdict(ctx)
    data.update({k: str(v) for k, v in kwargs.items() if v is not None})
    _context_var.set(RequestContext(**data))


def clear_request_context():
    _context_var.set(RequestContext())


def get_request_context() -> RequestContext:
    return _context_var.get()


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_request_context()
        record.request_id = getattr(record, "request_id", ctx.request_id)
        record.user_id = getattr(record, "user_id", ctx.user_id)
        record.path = getattr(record, "path", ctx.path)
        record.method = getattr(record, "method", ctx.method)
        return True
