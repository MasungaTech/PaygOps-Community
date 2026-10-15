import markupsafe

from shared.helpers.html_safety_helper import (
    escape_nl2br,
    join_markup,
    merge_query_overrides_into_context,
    safe_merge_field_values,
    safe_var,
    sanitize_html,
    sanitize_step_run_query_overrides,
)


def test_escape_nl2br_escapes_html_and_preserves_newlines():
    result = escape_nl2br('line1\n<script>alert(1)</script>')
    assert '<br>' in result
    assert '<script>' not in result
    assert '&lt;script&gt;' in result


def test_safe_var_wraps_escaped_content():
    result = safe_var('<b>x</b>')
    assert result == markupsafe.Markup('<var>&lt;b&gt;x&lt;/b&gt;</var>')


def test_join_markup_escapes_plain_strings():
    result = join_markup('Hello ', safe_var('World'))
    assert result == markupsafe.Markup('Hello <var>World</var>')


def test_sanitize_html_strips_scripts():
    result = sanitize_html('<p>ok</p><script>alert(1)</script>')
    assert '<p>ok</p>' in result
    assert '<script>' not in result


def test_safe_merge_field_values_escapes_user_content():
    result = safe_merge_field_values('new', '<img onerror=alert(1)>')
    assert '<img' not in result
    assert 'line-through' in result


def test_sanitize_step_run_query_overrides_strips_html_from_plain_fields():
    result = sanitize_step_run_query_overrides({
        'search': '<script>x</script>hello',
        'entity': '42',
    })
    assert '<script>' not in result['search']
    assert 'hello' in result['search']
    assert result['entity'] == '42'


def test_sanitize_step_run_query_overrides_allows_safe_html_in_message():
    result = sanitize_step_run_query_overrides({
        'message': '<p>ok</p><script>x</script>',
    })
    assert '<p>ok</p>' in result['message']
    assert '<script>' not in result['message']


def test_merge_query_overrides_into_context_adds_arbitrary_params():
    context = {'uuid': 'abc', 'subject_client': 1}
    merge_query_overrides_into_context(context, {
        'param1': 'hello',
        'subject_client': 999,
        'uuid': 'hijacked',
    })
    assert context['param1'] == 'hello'
    assert context['subject_client'] == 1
    assert context['uuid'] == 'abc'
