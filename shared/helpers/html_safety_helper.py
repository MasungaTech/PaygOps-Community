import re

import bleach
from markupsafe import Markup, escape

RICH_TEXT_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'em', 'i',
    'li', 'ol', 'p', 'pre', 'strong', 'ul', 'var', 'span',
]
RICH_TEXT_ATTRIBUTES = {
    'a': ['href', 'title', 'class'],
    'span': ['class'],
    'p': ['class'],
    'var': ['class'],
}
RICH_TEXT_PROTOCOLS = ['http', 'https', 'mailto']


def escape_nl2br(text):
    if text is None or text == '':
        return Markup('')
    return Markup(escape(text).replace('\n', Markup('<br>\n')))


def safe_var(text):
    return Markup(f'<var>{escape(text)}</var>')


def join_markup(*parts):
    result = Markup('')
    for part in parts:
        if isinstance(part, Markup):
            result += part
        elif part is not None:
            result += escape(part)
    return result


def sanitize_html(html):
    if not html:
        return Markup('')
    if isinstance(html, Markup):
        html = str(html)
    return Markup(bleach.clean(
        html,
        tags=RICH_TEXT_TAGS,
        attributes=RICH_TEXT_ATTRIBUTES,
        protocols=RICH_TEXT_PROTOCOLS,
        strip=True,
    ))


def safe_merge_field_values(val1, val2, br=False):
    val1 = val1 if val1 is not None else ''
    val2 = val2 if val2 is not None else ''
    if val1 == val2 or val2 == '':
        return escape(val1) if not isinstance(val1, Markup) else val1
    parts = [escape(val1), Markup(' <var class="line-through">'), escape(val2), Markup('</var>')]
    if br:
        parts.append(Markup('<br>'))
    return Markup('').join(parts)


def escape_link_label(text):
    return escape(text if text is not None else '')


def strip_html_tags(text):
    if not text:
        return ''
    return re.sub(r'<.*?>', '', str(text))


STEP_RUN_RICH_HTML_KEYS = frozenset({'message'})

# Journey context keys owned by the CUJ runtime; arbitrary URL query params
# must not overwrite these when merged into context_data for workflows.
JOURNEY_CONTEXT_RESERVED_KEYS = frozenset({
    'completed_at',
    'current_step_id',
    'current_step_slug',
    'last_step_user_id',
    'name',
    'platform_url',
    'preview',
    'run_steps',
    'started_at',
    'started_by_task_id',
    'status',
    'step_data',
    'subject_client',
    'subject_lead',
    'user_journey_slug',
    'user_journey_version_id',
    'uuid',
})


def sanitize_plain_text(value):
    if value is None:
        return value
    if not isinstance(value, str):
        return value
    return bleach.clean(value, tags=[], attributes={}, strip=True)


def sanitize_step_run_query_value(key, value):
    if not isinstance(value, str):
        return value
    if key in STEP_RUN_RICH_HTML_KEYS:
        return str(sanitize_html(value))
    return sanitize_plain_text(value)


def sanitize_step_run_query_overrides(query_params):
    return {
        key: sanitize_step_run_query_value(key, value)
        for key, value in query_params.items()
    }


def merge_query_overrides_into_context(context_data, query_overrides):
    """Copy non-reserved sanitized query params onto journey context_data.

    These become automation received_input when a workflow step POSTs context.
    """
    for key, value in query_overrides.items():
        if key not in JOURNEY_CONTEXT_RESERVED_KEYS:
            context_data[key] = value
    return context_data
