from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.videomanagement.services.draft_jobs import draft_result


class DraftJobQuery(serializers.Serializer):
    job = serializers.CharField(max_length=2048)


class DraftJobView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = DraftJobQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(
            draft_result(request.user, query.validated_data["job"]),
            headers={"Cache-Control": "no-store"},
        )
