"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""


from .models import TemplatePrompts


def get_template(template_select: str):
    if template_select.isnumeric():
        template = TemplatePrompts.objects.filter(id = template_select)

    elif len(template_select) > 0:
        template = TemplatePrompts.objects.filter(category = template_select.upper())

    else:
        template = None

    return template.first() if template and template.count() > 0 else None
