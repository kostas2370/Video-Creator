"""Limits are editor safeguards, not social platform API limits."""

import re
import unicodedata

from rest_framework import serializers


class TagTextField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class TagListField(serializers.ListField):
    child = TagTextField(max_length=80, allow_blank=False)
    default_error_messages = {
        "hashtag": "Use only letters, numbers and underscores in hashtags.",
        "keyword": "Use nonempty keyword phrases without commas or #.",
    }

    def __init__(self, **kwargs):
        super().__init__(max_length=20, **kwargs)

    def to_internal_value(self, data):
        tags = super().to_internal_value(data)
        result, seen = [], set()
        for tag in tags:
            tag = unicodedata.normalize("NFC", tag).lstrip("#").strip()
            if self.field_name == "tiktok":
                tag = re.sub(r"\s+", "", tag)
                if not tag or not all(
                    char.isalnum()
                    or char == "_"
                    or unicodedata.category(char).startswith("M")
                    for char in tag
                ):
                    self.fail("hashtag")
            else:
                tag = " ".join(tag.split())
                if not tag or any(char in tag for char in ",#"):
                    self.fail("keyword")
            if tag.casefold() not in seen:
                result.append(tag)
                seen.add(tag.casefold())
        return result


class VideoTagsSerializer(serializers.Serializer):
    tiktok = TagListField()
    youtube = TagListField()
    search = TagListField()


class SaveVideoTagsSerializer(serializers.Serializer):
    tags = VideoTagsSerializer()
    previous_tags = serializers.JSONField()


class GenerateVideoTagsSerializer(serializers.Serializer):
    previous_tags = serializers.JSONField()
