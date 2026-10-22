"""Contract shared by the platform-specific publishers."""

from abc import ABC, abstractmethod

from rest_framework.exceptions import ValidationError

from ..models import PublishJob


class Publisher(ABC):
    def __init__(self, account, token=None):
        self.account = account
        self.token = token

    def validate_options(self, options, metadata, size, context):
        """Validate export limits shared by all publishers; no token is needed."""
        if not size or size > 4 * 1024**3:
            raise ValidationError("The first publishing release supports exports up to 4 GB.")

    @abstractmethod
    def upload(self, job: PublishJob) -> None:
        """Upload the saved export and record its remote processing identifier."""

    @abstractmethod
    def check_status(self, job: PublishJob) -> None:
        """Refresh processing status and complete publishing when necessary."""
