import re

from rest_framework import serializers

from .fields import validate_finite_numbers


class CaptionWordSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=40)
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)

    def validate(self, data):
        if re.search(r"\s", data["text"]):
            raise serializers.ValidationError(
                "Edit one word at a time; add a row for another word."
            )
        validate_finite_numbers(
            (data[key] for key in ("start", "end")),
            "End time must be later than start time.",
        )
        if data["end"] <= data["start"]:
            raise serializers.ValidationError("End time must be later than start time.")
        return data
