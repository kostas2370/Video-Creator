def format_prompt(
    template_format: str,
    template_category: str,
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
    template_category : str
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
        f"This is a request from Viddie application \n"
        f"Write a scenario titled ' {title} ', that I will use to create a video required by my user\n"
        f"The script should obey the following specifications:\n"
        f"Video genre : {template_category} \n"
        f"The audience : {target_audience}\n"
        f"Viddie's user prompt : {userprompt}  \n"
        f"Structure : {template_format}"
    )
    return output


def format_update_form(text: str, prompt: str) -> str:
    return (
        f"The text i will give you is a scene in a video. {text}. Rewrite this text: {prompt} . "
        f"The text must be around the same size"
    )


def format_dalle_prompt(title: str, image_description: str) -> str:
    return f"Title : {title} \nImage Description:{image_description}"


def determine_fields(first_scene):
    if "scene" in first_scene and isinstance(first_scene["scene"], list):
        search_field = "scene"
    elif "sections" in first_scene:
        search_field = "sections"
    elif "dialogue" in first_scene:
        search_field = "dialogue"
    else:
        search_field = "sentences"

    narration_field = (
        "sentence" if "sentence" in first_scene[search_field][0] else "narration"
    )

    return search_field, narration_field
