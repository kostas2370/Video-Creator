"""Provider token formats, independent of database persistence and generation."""

from collections.abc import Mapping
from dataclasses import dataclass


def first_count(usage, fields):
    """Accept reported nonnegative integer counts, including an explicit zero."""
    for field in fields:
        value = (
            usage.get(field)
            if isinstance(usage, Mapping)
            else getattr(usage, field, None)
        )
        if type(value) is int and value >= 0:
            return value
    return None


@dataclass(frozen=True)
class TokenUsageAdapter:
    input_fields: tuple[str, ...] = (
        "input_tokens",
        "prompt_tokens",
        "prompt_token_count",
    )
    output_fields: tuple[str, ...] = (
        "output_tokens",
        "completion_tokens",
        "candidates_token_count",
    )
    total_fields: tuple[str, ...] = ("total_tokens", "total_token_count")
    additional_input_fields: tuple[str, ...] = ()

    def normalize(self, usage):
        input_tokens = first_count(usage, self.input_fields)
        output_tokens = first_count(usage, self.output_fields)
        total_tokens = first_count(usage, self.total_fields)
        if input_tokens is not None:
            input_tokens += sum(
                first_count(usage, (field,)) or 0
                for field in self.additional_input_fields
            )
        if (
            total_tokens is None
            and input_tokens is not None
            and output_tokens is not None
        ):
            total_tokens = input_tokens + output_tokens
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }


DEFAULT_TOKEN_ADAPTER = TokenUsageAdapter()
# Provider-specific semantics belong here, not in the persistence function.
TOKEN_USAGE_ADAPTERS = {
    "ANTHROPIC": TokenUsageAdapter(
        additional_input_fields=(
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        ),
    ),
}


def normalize_token_usage(usage, provider=None):
    adapter = TOKEN_USAGE_ADAPTERS.get(provider, DEFAULT_TOKEN_ADAPTER)
    return adapter.normalize(usage)
