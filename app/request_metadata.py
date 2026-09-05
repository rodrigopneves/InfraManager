import re
from dataclasses import dataclass

from flask import has_request_context, request


MAX_ENDPOINT_LENGTH = 120
MAX_IP_ADDRESS_LENGTH = 45
MAX_USER_AGENT_LENGTH = 255
CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")


@dataclass(frozen=True)
class RequestMetadata:
    ip_address: str | None
    user_agent: str | None
    endpoint: str | None


def sanitize_request_value(value: str, max_length: int) -> str | None:
    sanitized = CONTROL_CHARACTERS.sub(" ", value).strip()
    return sanitized[:max_length] or None


def get_request_metadata() -> RequestMetadata:
    if not has_request_context():
        return RequestMetadata(None, None, None)

    return RequestMetadata(
        ip_address=sanitize_request_value(
            request.remote_addr or "", MAX_IP_ADDRESS_LENGTH
        ),
        user_agent=sanitize_request_value(
            request.headers.get("User-Agent", ""), MAX_USER_AGENT_LENGTH
        ),
        endpoint=sanitize_request_value(
            request.endpoint or "unknown", MAX_ENDPOINT_LENGTH
        ),
    )
