class RequestObjectMixin:
    """Reuse a detail lookup within one request without skipping permission checks."""

    def get_object(self):
        if not hasattr(self, "_request_object"):
            self._request_object = super().get_object()
        else:
            self.check_object_permissions(self.request, self._request_object)
        return self._request_object
