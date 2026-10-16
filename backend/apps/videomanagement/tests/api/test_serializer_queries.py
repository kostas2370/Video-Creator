from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.usermanagement.baker_recipes import user
from ...baker_recipes import scene, video
from ...serializers.requests import (
    AddSceneSerializer, AddScenesSerializer, ManualSceneSerializer,
    ManualTextSerializer, SceneUpdateSerializer,
)
from ...views.scene_view import SceneView
from ...views.video_view import VideoView


class SerializerQueryTests(TestCase):
    def setUp(self):
        self.user = user.make()

    def bind(self, cls, action, pk, data):
        method = "patch" if action == "partial_update" else "post"
        request = getattr(APIRequestFactory(), method)("/", data, format="json")
        force_authenticate(request, user=self.user)
        view = cls()
        view.args = ()
        view.kwargs = {"pk": pk}
        view.format_kwarg = None
        view.action_map = {method: action}
        view.request = request
        view.request = view.initialize_request(request)
        return view

    def cases(self):
        ai = video.make(created_by=self.user, video_type="AI", status="READY")
        manual = video.make(created_by=self.user, video_type="MANUAL", status="READY")
        return (
            (SceneView, "partial_update", scene.make(video=ai).pk, {"text": "Hello"}, SceneUpdateSerializer),
            (SceneView, "partial_update", scene.make(video=manual).pk, {"text": ""}, ManualTextSerializer),
            (VideoView, "add_scene", ai.pk, {"text": "Hello"}, AddSceneSerializer),
            (VideoView, "add_scene", ai.pk, {"scenes": []}, AddScenesSerializer),
            (VideoView, "add_scene", manual.pk, {}, ManualSceneSerializer),
        )

    def test_serializer_selection_reuses_the_checked_object_without_queries(self):
        for cls, action, pk, data, expected in self.cases():
            with self.subTest(view=cls.__name__, serializer=expected.__name__):
                view = self.bind(cls, action, pk, data)
                with CaptureQueriesContext(connection) as queries:
                    owned = view.get_object()
                self.assertGreater(len(queries), 0)
                with self.assertNumQueries(0):
                    self.assertEqual(view.get_serializer_class(), expected)
                    self.assertIsInstance(view.get_serializer(data=data), expected)
                    self.assertIs(view.get_object(), owned)

    def test_cached_objects_still_check_permissions(self):
        stranger = user.make()
        for cls, action, pk, data, _ in self.cases():
            with self.subTest(view=cls.__name__, action=action):
                view = self.bind(cls, action, pk, data)
                view.get_object()
                view.request.user = stranger
                with self.assertRaises(PermissionDenied):
                    view.get_object()

    def test_a_new_request_reads_updated_project_state(self):
        made = video.make(created_by=self.user, video_type="AI", status="READY")
        first = self.bind(VideoView, "add_scene", made.pk, {})
        self.assertEqual(first.get_serializer_class(), AddSceneSerializer)
        video_model = type(made)
        video_model.objects.filter(pk=made.pk).update(video_type="MANUAL")
        second = self.bind(VideoView, "add_scene", made.pk, {})
        self.assertEqual(second.get_serializer_class(), ManualSceneSerializer)

    def test_schema_generation_does_not_fetch_objects(self):
        for cls, action, pk, data, _ in self.cases():
            with self.subTest(view=cls.__name__, action=action):
                view = self.bind(cls, action, pk, data)
                view.swagger_fake_view = True
                with self.assertNumQueries(0):
                    expected = SceneUpdateSerializer if cls is SceneView else AddSceneSerializer
                    self.assertEqual(view.get_serializer_class(), expected)
