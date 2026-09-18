from django.test.runner import DiscoverRunner
from django.test.utils import override_settings

from apps.apikeysmanagement.models import ApiKeys


class ServiceKeysRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)

        keys = {
            setting: f"test-{setting.lower()}" for _, setting in ApiKeys.FIELDS.values()
        }
        self._keys = override_settings(**keys)
        self._keys.enable()

    def teardown_test_environment(self, **kwargs):
        self._keys.disable()
        super().teardown_test_environment(**kwargs)
