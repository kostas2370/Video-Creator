from .models import TemplatePrompts


def get_template(template_select : str):
    if template_select.isnumeric():
        template = TemplatePrompts.objects.filter(id = template_select)

    elif len(template_select) > 0:
        template = TemplatePrompts.objects.filter(category = template_select)

    else:
        template = None

    return template
