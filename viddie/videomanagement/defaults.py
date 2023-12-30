default_format = """
Organize the scenario in scenes. Separate each scene into subsections so that a corresponding image can effectively describe each subsection.
Image : For each sentence of a scene, describe one representative image to appear during the sentence narration. 

The format of your answer must be:
json {"title": -,"target_audience": -,"topic": -,"scenes": [{"scene": string "dialogue": [{,"subsection ","image"}], }],}.
"""