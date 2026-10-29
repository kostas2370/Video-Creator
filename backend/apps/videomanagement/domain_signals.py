from django.dispatch import Signal

# Receivers may enrich video.settings before generation persists the storyboard.
# Arguments: video, storyboard, new_script.
storyboard_generated = Signal()
