from drf_yasg.inspectors import SwaggerAutoSchema


class SceneImageUploadSchema(SwaggerAutoSchema):
    def get_consumes(self):
        # Swagger 2 cannot describe both JSON and file uploads for one operation.
        # Show the upload form; the action also accepts JSON for audio-only updates.
        return ["multipart/form-data", "application/x-www-form-urlencoded"]
