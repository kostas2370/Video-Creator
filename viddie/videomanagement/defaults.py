"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""


default_format = """
Organize the scenario in scenes. Separate each scene into sentences so that a corresponding image can effectively describe each sentence.
Image : For each sentence of a scene, describe one representative image to appear during the sentence narration. 

The format of your answer must be:
json {"title": -,"target_audience": -,"topic": -,"scenes": [{"scene": string "dialogue": [{,"sentence ","image"}], }],}.
"""