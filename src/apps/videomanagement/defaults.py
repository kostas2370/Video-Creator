default_format = """
 Organize the scenario in scenes. Each scene should consist of individual sections. For 
each section, develop the narration and the description of an image representing the narration

Your answer must be in the following JSON format:
{"title": -,"audience": -,"genre": -,"scenes": [{"scene",sections: [{"narration ","image_description"},]},]}.
"""

default_format1 = """
 Organize the scenario in scenes. Each scene should consist of individual sentences. For 
each sentence, develop the narration and the description of an image representing the sentence

Your answer must be in the following JSON format:
{"title": -,"audience": -,"genre": -,"scenes": [{"scene",sentences: [{"sentence ","image_description"},]},]}.
"""


default_format2 = """


The format of your answer must be like that in json 
json {"title": -,"target_audience": -,"topic": -,"scenes": [{"scene": string "dialogue": [{,"sentence","image_description"}], }],}. . 
image_description :For each sentence, add an image description
"""