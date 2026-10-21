"""Contract shared by the platform-specific publishers."""

from abc import ABC, abstractmethod

from ..models import PublishJob


class Publisher(ABC):
    def __init__(self, account, token):
        self.account = account
        self.token = token

    @abstractmethod
    def upload(self, job: PublishJob) -> None:
        """Upload the saved export and record its remote processing identifier."""

    @abstractmethod
    def check_status(self, job: PublishJob) -> None:
        """Refresh processing status and complete publishing when necessary."""
