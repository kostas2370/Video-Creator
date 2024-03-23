def format_prompt(template_format, template_category, userprompt="", title='', target_audience=''):

    if title == '':
        title = "The title will be selected by you, depending on the prompt"

    if target_audience == '':
        target_audience = " Select an appropriate target audience."

    output = f"This is a request from Viddie application \n"\
             f"Write a scenario titled \' {title} \', that I will use to create a video required by my user\n" \
             f"The script should obey the following specifications:\n"\
             f"Video genre : {template_category} \n" \
             f"The audience : {target_audience}\n" \
             f"Viddie's user prompt : {userprompt}  \n" \
             f"Structure : {template_format}" \


    return output


def format_prompt_for_official_gpt(template_format, template_category, userprompt="", title='', target_audience=''):

    if title == '':
        title = "The title will be selected by you, depending on the prompt"

    if target_audience == '':
        target_audience = " Select an appropriate target audience."

    system_output = f"This is a request from Viddie application \n"\
                    f"Write a scenario titled \' {title} \', that I will use to create a video required by my user\n" \
                    f"The script should obey the following specifications:\n"\
                    f"Structure : {template_format}" \

    user_output = f"Video genre : {template_category} \n  {userprompt} The audience : {target_audience}\n"

    return system_output, user_output


def format_update_form(text, prompt):
    return f"The text i will give you is a scene in a video. {text}. Rewrite this text: {prompt} . " \
           f"The text must be around the same size"


def format_dalle_prompt(title, image_description):
    return f'Title : {title} \nImage Description:{image_description}'
