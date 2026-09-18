from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class NoServiceKeysRunner(DiscoverRunner):
    """Run the suite as if the deployment held no provider keys.

    Without this the result depends on whatever the developer happens to have in
    .env: voice visibility is gated on a key resolving, so a local run with keys
    passes tests that fail in CI, which has none. Tests that need a key set one
    with override_settings.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)

        from apps.apikeysmanagement.models import ApiKeys

        blanked = {setting: "" for _, setting in ApiKeys.FIELDS.values()}
        self._no_keys = override_settings(**blanked)
        self._no_keys.enable()

    def teardown_test_environment(self, **kwargs):
        self._no_keys.disable()
        super().teardown_test_environment(**kwargs)
