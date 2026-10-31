STORY_FORMAT_GUIDANCE = {
    "GENERAL": "Follow the series premise and the new episode idea.",
    "ANIMATED_STORY": (
        "Create a short animated character story: immediate visual hook, clear conflict, "
        "escalation, then a satisfying visual payoff or a deliberate cliffhanger. "
        "Use expressive actions and readable emotions, with one main action per shot. "
        "Keep the cast small and do not rely on narration to explain visible events. "
        "Describe animation in the saved visual style."
    ),
    "SERIAL_DRAMA": (
        "Create an episode of a cinematic serial drama: open on an urgent emotional hook, "
        "establish a character's desire and relationship stakes, escalate through a "
        "confrontation or revelation, and end on an unresolved turn or cliffhanger. "
        "Advance existing relationships and consequences from reviewed episode memories. "
        "Keep action filmable, with one main dramatic beat per shot. "
        "Do not resolve the entire series in one episode or retell previous episodes."
    ),
}


def series_visual_continuity(*, characters, visual_style, cast):
    parts = [f"Cast: {characters}", f"Style: {visual_style}"]
    for character in cast:
        parts.append(
            f"{character['name']} — fixed appearance: {character['appearance']}"
        )
        if character.get("wardrobe"):
            parts.append(f"Default wardrobe: {character['wardrobe']}")
    if cast:
        parts.append(
            "Keep fixed character features consistent. Include characters only when called "
            "for by the shot. Wardrobe may change when the story explicitly calls for it."
        )
    return "\n".join(parts)
