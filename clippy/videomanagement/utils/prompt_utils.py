
def format_reply(reply_format):
    code = reply_format.strip()

    return code


def format_prompt(template, userprompt="", title='', target_audience=''):

    if title == '':
        title = "The title will be selected by you, depending on the prompt"

    if target_audience == '':
        target_audience = "You will select the target audience"

    output = f"Hello i would like you to make me a scenario about a {template.category} video. \n" \
             f"The title of the video will be {title} .  \n" \
             f"The target audience : {target_audience}" \
             f"The information that you need are here : {userprompt}  \n" \
             f"The format of your answer must be like that in {template.format}" \
             f"the images must contain only 1 value" \


    return output
