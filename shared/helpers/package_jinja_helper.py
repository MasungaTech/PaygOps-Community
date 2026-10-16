import os
import re


USER_JOURNEY_PACKAGE_FILE_SUFFIX = '-create_user_journey_versions.json'

# Automatou renders package JSON as Jinja. Keep {{sN.field}} install-time
# references, and wrap user-journey runtime templates so they survive install.
_JINJA_CHUNK_RE = re.compile(
    r'\{%\s*raw\s*%\}.*?\{%\s*endraw\s*%\}'
    r'|\{\{[^{}]+\}\}',
    re.DOTALL,
)
_PACKAGE_STEP_REF_RE = re.compile(r'\{\{\s*s\d+\.[a-zA-Z_][\w.]*\s*\}\}')


def is_user_journey_package_file(filename):
    return os.path.basename(filename).endswith(USER_JOURNEY_PACKAGE_FILE_SUFFIX)


def is_package_step_reference(value):
    return isinstance(value, str) and bool(_PACKAGE_STEP_REF_RE.fullmatch(value.strip()))


def _escape_runtime_jinja_chunk(match):
    chunk = match.group(0)
    if chunk.startswith('{%') or _PACKAGE_STEP_REF_RE.fullmatch(chunk):
        return chunk
    return '{% raw %}' + chunk + '{% endraw %}'


def escape_runtime_jinja_templates(value):
    if isinstance(value, dict):
        return {key: escape_runtime_jinja_templates(val) for key, val in value.items()}
    if isinstance(value, list):
        return [escape_runtime_jinja_templates(item) for item in value]
    if isinstance(value, str):
        return _JINJA_CHUNK_RE.sub(_escape_runtime_jinja_chunk, value)
    return value
