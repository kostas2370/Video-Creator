from dataclasses import dataclass
from typing import Iterator


def format_prompt(
    template_format: str,
    genre: str,
    userprompt: str = "",
    title: str = "",
    target_audience: str = "",
) -> str:
    """
    Generate a formatted script prompt for video creation.

    Parameters:
    -----------
    template_format : str
        The structure/format of the video script.
    genre : str
        The genre/category of the video.
    userprompt : str, optional
        The user's prompt or request. Default is an empty string.
    title : str, optional
        The title of the scenario. If not provided, it will be generated based on the prompt.
    target_audience : str, optional
        The target audience for the video. Default is an empty string.

    Returns:
    --------
    str
        The formatted script prompt.

    Detailed Steps:
    ---------------
    1. If 'title' is not provided, generate it based on the prompt.
    2. If 'target_audience' is not provided, generate a suggestion.
    3. Construct the formatted script prompt with the provided parameters.

    Notes:
    ------
    - This function generates a script prompt for video creation, tailored to the specified format, category, user
      prompt, title, and target audience.
    """

    if title == "":
        title = "The title will be selected by you, depending on the prompt"

    if target_audience == "":
        target_audience = " Select an appropriate target audience."

    output = (
        f"This is a request from Viddie application.\n"
        f"Write a scenario titled '{title}', that I will use to create a video required by my user.\n"
        f"The script should obey the following specifications:\n"
        f"Video genre : {genre}\n"
        f"The audience : {target_audience}\n"
        f"Viddie's user prompt : {userprompt}\n"
        f"Structure : {template_format}\n\n"
        f"IMPORTANT INSTRUCTIONS FOR SCENES:\n"
        f"- Provide vivid, highly detailed visual descriptions for every shot.\n"
        f"- Ensure each scene visually flows logically into the next one (continuous motion, environment, and lighting)."
    )
    return output


def format_update_form(text: str, prompt: str) -> str:
    return (
        f"The text i will give you is a scene in a video. {text}. Rewrite this text: {prompt} . "
        f"The text must be around the same size"
    )


def scene_text(sentence: dict) -> str:
    """The text that identifies a scene.

    Normally the narration. With narration switched off the script is not asked for a
    spoken line at all, so the shot description stands in — Scene rows are looked up by
    this text later, so it has to come from somewhere.
    """
    return (sentence.get("sentence") or sentence["image_description"]).strip()


@dataclass(frozen=True)
class ScriptLine:
    text: str
    image_description: str
    is_last: bool


def script_lines(gpt_answer: dict) -> Iterator[ScriptLine]:
    for scene in gpt_answer["scenes"]:
        sentences = scene["sentences"]
        for index, sentence in enumerate(sentences):
            yield ScriptLine(
                text=scene_text(sentence),
                image_description=sentence["image_description"],
                is_last=index == len(sentences) - 1,
            )


def format_dalle_prompt(title: str, image_description: str) -> str:
    return f"Title : {title} \nImage Description:{image_description}"


def format_sora_prompt(
    image_description: str,
    next_scene_description: str = "",
    title: str = "",
    style: str = "",
    camera_movement: str = "",
) -> str:
    """Formats a highly detailed prompt for video generation (e.g., Sora),

    incorporating next-scene context for narrative and visual continuity.
    """
    parts = []
    main_desc = image_description.strip()
    if style:
        main_desc += f", rendered in a {style.strip()} visual style"
    parts.append(f"Cinematic video shot: {main_desc}.")

    if camera_movement:
        parts.append(f"Camera movement: {camera_movement.strip()}.")

    if next_scene_description:
        parts.append(
            f"Seamlessly transition towards the upcoming scene: {next_scene_description.strip()}. "
            f"Maintain consistent lighting, character features, and subject motion."
        )
    if title:
        parts.append(f"Shot from the video titled '{title}'.")

    return " ".join(parts)
