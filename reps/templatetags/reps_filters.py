import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="footnotes")
def footnotes(text):
    """Convert [1], [2], etc. in narrative text to superscript anchor links."""
    def replace_ref(match):
        num = match.group(1)
        return f'<sup><a href="#source-{num}" class="footnote-ref">[{num}]</a></sup>'

    result = re.sub(r"\[(\d+)\]", replace_ref, str(text))
    return mark_safe(result)
