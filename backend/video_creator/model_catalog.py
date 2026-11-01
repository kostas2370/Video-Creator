SCRIPT_MODEL_REPLACEMENTS = {
    "claude-3-5-sonnet-20240620": "claude-sonnet-5-5",
    "gemini-1.5-pro": "gemini-4-argon",
    "gemini-1.5-flash": "gemini-3.8-flash",
    "gemini-1.0-pro": "gemini-3.5-flash-lite",
}


def current_script_model(model):
    return SCRIPT_MODEL_REPLACEMENTS.get(model, model)
