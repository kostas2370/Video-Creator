from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageCostRequest:
    count: int = 1
    generation_mode: str = "STANDARD"
    durations: tuple[float | None, ...] = ()
    provider_name: str = ""
    output_type: str = "IMAGE"


@dataclass(frozen=True)
class TTSCostRequest:
    text: str
    requests: int = 1
    voice: object = None
    provider_name: str = ""


class ImageProvider(ABC):
    @staticmethod
    @abstractmethod
    def generate(*args, **kwargs):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def calculate(request: ImageCostRequest) -> dict:
        raise NotImplementedError


class TTSProvider(ABC):
    @staticmethod
    @abstractmethod
    def generate(*args, **kwargs):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def calculate(request: TTSCostRequest) -> dict:
        raise NotImplementedError
