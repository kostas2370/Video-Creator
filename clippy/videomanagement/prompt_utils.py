
def format_reply(reply_format):
    code = reply_format.strip()

    return code


def format_prompt(template, userPrompt="", title ='', reply_format = ''):

    if template.format != "":
        video_format = format_reply(reply_format)

    output = f"Hello i would like you to make me a prompt about a {template} video. \n" \
             f"The title of the video will be {title} .  \n" \
             f"The information that you need are here : {userPrompt}  \n" \
             f"The format of your answer must be like that in {video_format}"

    return output




