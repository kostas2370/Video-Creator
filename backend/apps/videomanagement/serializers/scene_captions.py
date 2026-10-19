import math
import re

from rest_framework import serializers


class CaptionWordSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=40)
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)

    def validate(self, data):
        if re.search(r"\s", data["text"]):
            raise serializers.ValidationError("Edit one word at a time; add a row for another word.")
        if not all(math.isfinite(data[key]) for key in ("start", "end")) or data["end"] <= data["start"]:
            raise serializers.ValidationError("End time must be later than start time.")
        return data


class SceneCaptionsSerializer(serializers.Serializer):
    revision = serializers.RegexField(r"^[a-f0-9]{64}$")
    words = CaptionWordSerializer(many=True, max_length=10000)
