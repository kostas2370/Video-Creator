from openai import APIConnectionError, APIStatusError, APITimeoutError

MESSAGES = {
    "credentials": "OpenAI rejected the API key. It may be invalid, expired, or revoked. Check the OpenAI key in API keys settings, or ask the administrator if you use service keys.",
    "quota": "OpenAI quota or billing limit reached. Check your OpenAI billing and available credits before retrying.",
    "rate_limit": "OpenAI is receiving too many requests. Wait a moment, then try again.",
    "access": "OpenAI denied access to this model or operation. Check your project's permissions and model access.",
    "timeout": "OpenAI took too long to respond. Please try again.",
    "connection": "Could not connect to OpenAI. Check the connection and try again.",
    "unavailable": "OpenAI is temporarily unavailable. Please try again later.",
}

HTTP_ERROR_CODES = {401: "credentials", 403: "access", 429: "rate_limit"}
CONNECTION_ERROR_CODES = {APITimeoutError: "timeout", APIConnectionError: "connection"}


class ProviderRequestError(Exception):
    def __init__(self, code):
        self.code = code if code in MESSAGES else "unavailable"
        super().__init__(self.code)

    def __str__(self):
        return MESSAGES[self.code]


def provider_failure(error):
    seen = set()
    while isinstance(error, BaseException) and id(error) not in seen:
        seen.add(id(error))
        code = next(
            (
                value
                for kind, value in CONNECTION_ERROR_CODES.items()
                if isinstance(error, kind)
            ),
            None,
        )
        if isinstance(error, ProviderRequestError):
            code = error.code
        if isinstance(error, APIStatusError):
            body = error.body if isinstance(error.body, dict) else {}
            details = body.get("error", body)
            reason = details.get("code") if isinstance(details, dict) else None
            code = HTTP_ERROR_CODES.get(
                error.status_code, "unavailable" if error.status_code >= 500 else None
            )
            if reason in (
                "insufficient_quota",
                "billing_hard_limit_reached",
                "billing_not_active",
            ):
                code = "quota"
        if code:
            return {"provider": "OpenAI", "code": code, "message": MESSAGES[code]}
        error = error.__cause__ or error.__context__
    return None
