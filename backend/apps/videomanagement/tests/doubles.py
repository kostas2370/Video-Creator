"""Stand-ins for the moviepy clips the render pipeline passes around.

A MagicMock is not enough for these: the code multiplies `clip.duration` by a float and
compares it against the audio's, so a duration has to be a real number, and every
effect has to hand back something that still has one. FakeClip does that and records
what was done to it, which is what the tests assert on.
"""


class FakeClip:
    """A clip whose duration is a real number and whose effects are recorded."""

    def __init__(self, duration=10.0, size=(1920, 1080)):
        self.duration = duration
        self.size = size
        self.h = size[1]
        self.effects = []
        self.closed = False
        self.audio = None

    def _record(self, name, *args, **kwargs):
        self.effects.append(name)
        return self

    def __getattr__(self, name):
        # Effects that neither change the duration nor are asserted on individually:
        # resize, margin, set_position, volumex, audio_fadein, crossfadein, and so on.
        def effect(*args, **kwargs):
            return self._record(name, *args, **kwargs)

        return effect

    def without_audio(self):
        self.audio = None
        return self._record("without_audio")

    def subclip(self, start, end):
        self.duration = end - start
        return self._record("subclip")

    def set_duration(self, duration):
        self.duration = duration
        return self._record("set_duration")

    def fx(self, effect, **kwargs):
        if kwargs.get("total_duration") is not None:
            self.duration = kwargs["total_duration"]

        return self._record(f"fx:{getattr(effect, '__name__', effect)}")

    def fadein(self, duration):
        return self._record("fadein")

    def fadeout(self, duration):
        return self._record("fadeout")

    def set_audio(self, audio):
        self.audio = audio
        return self._record("set_audio")

    def close(self):
        self.closed = True


class FakeAudio:
    """An audio clip with a real duration. Effects return it unchanged."""

    def __init__(self, duration=10.0):
        self.duration = duration
        self.effects = []
        self.closed = False
        self.written_to = None

    def __getattr__(self, name):
        def effect(*args, **kwargs):
            self.effects.append(name)
            return self

        return effect

    def write_audiofile(self, path, *args, **kwargs):
        self.written_to = path

    # Dunder lookups skip __getattr__, so the context manager has to be spelled out —
    # scene_narration_duration opens its clip with `with`.
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False

    def close(self):
        self.closed = True
