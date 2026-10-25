"""Shared registration and late-bound lookup for voice and visual providers."""

from collections.abc import Mapping, Set
from dataclasses import dataclass
from importlib import import_module
from types import MappingProxyType


@dataclass(frozen=True)
class ProviderRegistration:
    module: str
    function: str
    capabilities: Mapping[str, object]

    @classmethod
    def from_handler(cls, handler, capabilities):
        return cls(
            handler.__module__, handler.__name__, MappingProxyType(dict(capabilities))
        )

    def handler(self):
        # Read the current module attribute so patches and reloads remain effective.
        return getattr(import_module(self.module), self.function)


class ProviderNames(Set):
    """Live, read-only names matching registration metadata."""

    def __init__(self, registry=None, *, mode=None, **capabilities):
        self.registry = registry
        self.mode = mode
        self.capabilities = capabilities

    def __get__(self, instance, owner):
        return type(self)(owner, mode=self.mode, **self.capabilities)

    def _names(self):
        return self.registry.names(mode=self.mode, **self.capabilities)

    def __contains__(self, value):
        return value in self._names()

    def __iter__(self):
        return iter(self._names())

    def __len__(self):
        return len(self._names())

    @classmethod
    def _from_iterable(cls, values):
        return frozenset(values)


class ProviderRegistry:
    """Registries share lookup rules but own independent registration state."""

    mode_label = "provider"
    default_mode = "default"
    defaults = {"default": None}
    _providers = {}
    _fallback_providers = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._providers = {}
        cls._fallback_providers = {}

    @classmethod
    def _mode(cls, mode):
        mode = cls.default_mode if mode is None else mode
        if mode not in cls.defaults:
            raise ValueError(f"Unsupported {cls.mode_label} mode: {mode}")
        return mode

    @classmethod
    def register(cls, name, mode=None, **capabilities):
        mode = cls._mode(mode)

        def decorator(handler):
            cls._providers.setdefault(mode, {})[name] = (
                ProviderRegistration.from_handler(handler, capabilities)
            )
            return handler

        return decorator

    @classmethod
    def register_fallback(cls, mode=None):
        mode = cls._mode(mode)

        def decorator(handler):
            cls._fallback_providers[mode] = ProviderRegistration.from_handler(
                handler, {}
            )
            return handler

        return decorator

    @classmethod
    def registration(cls, name=None, mode=None):
        """Built-in metadata only; custom fallbacks do not imply capabilities."""
        mode = cls._mode(mode)
        return cls._providers.get(mode, {}).get(name or cls.defaults[mode])

    @classmethod
    def names(cls, mode=None, **capabilities):
        modes = cls._providers if mode is None else (cls._mode(mode),)
        return frozenset(
            name
            for key in modes
            for name, entry in cls._providers.get(key, {}).items()
            if all(
                entry.capabilities.get(field) == value
                for field, value in capabilities.items()
            )
        )

    @classmethod
    def _select(cls, name, mode):
        mode = cls._mode(mode)
        registered = cls.registration(name, mode)
        if registered is not None:
            return registered
        fallback = cls._fallback_providers.get(mode)
        if fallback is not None:
            return fallback
        return cls.registration(cls.defaults[mode], mode)

    @classmethod
    def get(cls, name=None, mode=None):
        entry = cls._select(name, mode)
        return entry.handler() if entry is not None else None
