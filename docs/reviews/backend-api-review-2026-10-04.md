# Backend views, serializers, and models review

Reviewed the application views, serializers, and models in `videomanagement`, `usermanagement`, and `apikeysmanagement`, including the current working tree changes. Followed relevant permissions, services, migrations, and tests to confirm behavior. This is a targeted code review, not an exhaustive security audit.

The two scene-image findings from the previous review are fixed: integer query validation followed by a scene-scoped 404 lookup, and a writable multipart upload schema with the actual 200 response. JSON remains accepted for audio-only updates. Four regression tests cover uploads/replacement, invalid and missing IDs, the schema, and JSON compatibility; the existing foreign-scene test covers ownership.

All eight numbered findings below are now fixed. The original observations are retained as the review record; source locations refer to that snapshot. Runtime request serializers now live in `backend/apps/videomanagement/request_serializers.py`.

## Completed fixes

| Issue | Resolution |
| --- | --- |
| 1 | Provider timestamps have a migration with one-time backfills; inherited endpoint URLs support 500 characters. |
| 2 | The voice API exposes list, retrieve, and delete. Creation and updates return 405; response fields are explicitly read-only. |
| 3 | PATCH supplies only requested changes; assets and settings are preserved when omitted. Narrow saves also preserve concurrent worker status and dispatch tokens. |
| 4 | Scene text updates, rewrites, and image generation validate input before any work or charging. |
| 5 | Scene credit is reserved through an atomic conditional update and refunded on exceptions. Stale permission checks cannot spend exhausted credit. |
| 6 | Failed render/resume publication restores a retryable status and returns 503. Each dispatch has a token that workers consume atomically, preventing obsolete and duplicate messages from running. A publication error after worker startup preserves the worker's claim. Previously queued jobs remain supported. |
| 7 | Unsupported video POST/PUT routes return 405. Supported editing uses PATCH and response serializers expose an explicit read-only field list. |
| 8 | The login migration merges duplicate counts while retaining the earliest record/date, then enforces database uniqueness on user/IP. |

The serializer cleanup is also complete: empty persistence stubs and the unnecessary input serializer representation override were removed, the module was renamed, and scene creation consumes `validated_data`. A decimal credit representation remains a design recommendation rather than a requirement for the corrected concurrency behavior.

Final verification: **738 backend tests passed**, Ruff passed, `git diff --check` passed, and Django's migration consistency check reports no changes. The tests include historical-row migration checks, stale credit reservations/refunds, PATCH preservation, upload documentation, unsupported routes, broker failures, retry safety, and duplicate delivery.

Three migrations are ready for rollout: `apikeysmanagement.0008_provider_timestamps`, `videomanagement.0012_video_dispatch_token`, and `usermanagement.0005_unique_login_user_ip`. Apply migrations before starting the updated backend and workers. Verification used an isolated SQLite test database; production database migrations and live broker behavior were not exercised.

## 1. P1 — Provider model fields have no corresponding migration

Location: `backend/apps/apikeysmanagement/models.py`, `AbstractCustomProvider.created_at` and `updated_at` (lines 156–157).

The existing working tree edit moves timestamps into the abstract base. This adds both fields to `UserCustomTTSProvider`, but its migrations do not create these columns. Ordinary ORM reads and writes now reference nonexistent columns. The broader test run produced database errors including `table apikeysmanagement_usercustomttsprovider has no column named created_at`.

Add a migration with a deliberate backfill for existing TTS providers. Also review the inherited `endpoint_url`: removing the visual provider override reduces its accepted length from 500 to Django's default 200. Preserve 500 if this shortening was unintended. These edits predate the scene-image work.

## 2. P1 — Ordinary users can publish voices into the shared catalog

Locations: `backend/apps/videomanagement/views/general_views.py`, `VoiceView` (lines 74–80); `backend/apps/videomanagement/serializers.py`, `VoiceModelSerializer` (lines 69–72).

`ModelViewSet` exposes creation, while the serializer exposes every model field and does not force ownership. Object permissions do not run on creation. A normal authenticated user's POST with name, provider `OPENAI`, type `API`, and a path returns 201 with `created_by=None`; that voice then appears for other users with access to the provider. Confirmed with an isolated API probe and a second user's availability query.

If the endpoint only needs listing and deletion, expose those operations explicitly. If creation is intended, assign the owner on the server, prevent ownership reassignment, and make shared-catalog creation an explicit privileged operation.

## 3. P1 — A title-only PATCH clears assets and corrupts settings

Locations: `backend/apps/videomanagement/views/video_view.py`, `partial_update` (lines 64–68); `backend/apps/videomanagement/swagger_serializers.py`, `VideoUpdateSerializer`; `backend/apps/videomanagement/services/VideoServices.py`, `video_update`.

PATCH validation is performed without `partial=True`. The serializer supplies defaults for omitted fields, including `avatar_position="streamer"`, which is not even one of its allowed choices. The service unconditionally replaces avatar/intro/outro and the entire settings dictionary.

Confirmed: PATCHing only `{"title": "Renamed"}` clears an existing intro and outro and replaces `{"narration": false, "subtitles": true, "avatar_position": "left,bottom"}` with `{"subtitles": null, "avatar_position": "streamer"}`. Losing `narration=false` also changes how downstream code interprets narration.

Validate partial updates as partial, distinguish omitted fields from explicit clearing, update only supplied asset fields, and merge supplied settings into the current dictionary. Changing the serializer alone is insufficient because the service also has defaults and unconditional assignments. Expand the existing rename test to assert preservation of assets and settings.

## 4. P2 — Missing scene rewrite input causes a server error

Location: `backend/apps/videomanagement/views/scene_view.py`, `generate`, and the raw input handling in `partial_update`.

The decorator names `SceneUpdateSerializer`, but the action never validates with it. An empty JSON body reaches `None.strip()` and raises `AttributeError`; numbers and null values also fail. Confirmed through the scene rewrite API.

Instantiate the request serializer, call `is_valid(raise_exception=True)`, and consume `validated_data`. Apply the same runtime validation principle to the scene text update and image-description actions. Swagger declarations do not validate requests.

## 5. P2 — Generation balance updates lose concurrent charges

Location: `backend/apps/videomanagement/views/scene_view.py`, the debit/save pairs in `partial_update`, `generate`, and `generate_image_scene`.

Each action subtracts from the user instance loaded for its request and saves it. Two requests that load the same starting balance overwrite each other's deductions. An isolated probe using two independently loaded instances confirmed that two successful rewrites deduct only 0.03 in total instead of 0.06. Saving the full user also risks overwriting unrelated concurrent account changes.

Use an atomic database update for debits, and centralize quota reservation/checking so concurrent requests cannot both spend the same allowance. Consider a decimal field for explicitly priced credits; that alone does not solve the race.

## 6. P2 — Queue publication failures leave videos stuck

Location: `backend/apps/videomanagement/views/video_view.py`, `render_video` (lines 138–153), with the same ordering in `resume`.

The view changes the status before publishing the task. If publication fails, the status remains in flight with no worker responsible for it. Confirmed by making `render_video_task.delay` raise: the video remains `RENDERING` and the next render request returns 409.

Provide a recoverable dispatch path. For reliable delivery, record a job/outbox entry transactionally and retry publication. A simpler interim approach must handle failed publication and restore a retryable state without racing a worker or duplicating jobs. `on_commit` alone does not address broker failure after commit.

## 7. P2 — Inherited video write routes use an unsupported nested serializer

Locations: `backend/apps/videomanagement/views/video_view.py`, `ModelViewSet` and `get_serializer_class`; `backend/apps/videomanagement/serializers.py`, `VideoSerializer.prompt` (line 107).

Only PATCH is implemented through the update service. The inherited PUT route uses `VideoSerializer`, whose nested writable prompt has no custom update implementation. Confirmed that PUT with a title and nested prompt raises DRF's writable-nested-field assertion, producing a server error. The inherited create route is subject to the same serializer design problem.

Expose only supported routes, or implement explicit write serializers and service calls for each supported operation. Use an explicit field allowlist and make server-owned fields read-only when introducing those write serializers; simply enabling nested writes would expose additional fields through `fields="__all__"`.

## 8. P2 — Login lookup assumes uniqueness absent from the database

Locations: `backend/apps/usermanagement/models.py`, `Login` (lines 54–58); `backend/apps/usermanagement/views.py`, `LoginView.post` (line 114).

The view calls `get_or_create(user=user, ip=user_ip)`, but the model does not constrain that pair. Concurrent first logins can create duplicates; subsequent logins then raise `MultipleObjectsReturned`. Confirmed that duplicate pairs can be inserted and that the exact view lookup then raises. The concurrent insertion itself was not stress-tested.

Deduplicate existing rows while preserving counts, then add a database `UniqueConstraint` on `(user, ip)`.

## Smaller cleanup opportunities

- Remove empty serializer `create()` and `update()` implementations where the serializer is validation-only. The default explicit unsupported-operation error is more useful than silently returning `None`.
- Move runtime request serializers out of a module named `swagger_serializers.py`, or rename the module to reflect its actual role.
- `AddSceneSerializer.to_representation()` compares the entire dictionary with `"TWITCH"`; that branch can never run. Fix the comparison or remove the output transformation if this serializer is only for input. Services should use `validated_data` instead of relying on serialization to transform request data.
- For monetary or precisely priced credit balances, `FloatField` merits replacement with a deliberate decimal representation and rounding policy.

## Initial review verification

- All 19 scene API and schema tests pass, including preserved JSON update support.
- Broader test selection: `apps.videomanagement.tests.api apps.videomanagement.tests.test_models apps.usermanagement.tests apps.apikeysmanagement.tests`, using `video_creator.settings.local`. The final run executed 329 tests with 0 assertion failures and 18 errors. All 18 errors were `OperationalError: table apikeysmanagement_usercustomttsprovider has no column named created_at`, confirming finding 1.
- Seven additional isolated probes confirmed findings 2–8 using a disposable test database. Provider generation and queue publication were mocked where relevant; no real generation jobs were dispatched.
- A migration consistency check with `makemigrations --check --dry-run --noinput` exited with status 3. No migration was written or applied.
