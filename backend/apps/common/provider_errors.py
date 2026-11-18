from functools import wraps

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
        code = None
        if isinstance(error, ProviderRequestError):
            code = error.code
        elif isinstance(error, APITimeoutError):
            code = "timeout"
        elif isinstance(error, APIConnectionError):
            code = "connection"
        elif isinstance(error, APIStatusError):
            body = error.body if isinstance(error.body, dict) else {}
            body = body.get("error", body)
            reason = body.get("code") if isinstance(body, dict) else None
            if reason in (
                "insufficient_quota",
                "billing_hard_limit_reached",
                "billing_not_active",
            ):
                code = "quota"
            elif error.status_code == 401:
                code = "credentials"
            elif error.status_code == 403:
                code = "access"
            elif error.status_code == 429:
                code = "rate_limit"
            elif error.status_code >= 500:
                code = "unavailable"
        if code:
            return {"provider": "OpenAI", "code": code, "message": MESSAGES[code]}
        error = error.__cause__ or error.__context__
    return None


def openai_errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            failure = provider_failure(error)
            if failure:
                raise ProviderRequestError(failure["code"]) from error
            raise

    return wrapped
