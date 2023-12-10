
def format_reply(reply_format):
    code = reply_format.strip()

    return code


def format_prompt(template, userprompt="", title='', target_audience=''):

    if title == '':
        title = "The title will be selected by you, depending on the prompt"

    if target_audience == '':
        target_audience = " Select an appropriate target audience."

    output = f"Write a scenario named \' {title} \' \n" \
             f"Video category : {template.category} \n" \
             f"The target audience : {target_audience}" \
             f"Description : {userprompt}  \n" \
             f"Structure : {template.format}" \


    return output


def format_update_form(text, prompt):
    return f"The text i will give you is a scene in a video. {text}. Rewrite this text: {prompt} . The text must be around the same size"
