import textwrap

import markdown
from jinja2.ext import Extension
from jinja2.nodes import CallBlock

MARKDOWN_EXTENSIONS = [
    'admonition',
    'attr_list',
    'codehilite',
    'smarty',
    'tables',
    'pymdownx.betterem',
    'pymdownx.caret',
    'pymdownx.details',
    'pymdownx.emoji',
    'pymdownx.keys',
    'pymdownx.magiclink',
    'pymdownx.mark',
    'pymdownx.smartsymbols',
    'pymdownx.superfences',
    'pymdownx.tabbed',
    'pymdownx.tasklist',
    'pymdownx.tilde',
]


class MarkdownExtension(Extension):
    """Jinja2 {% markdown %} block tag, compatible with the former jinja-markdown package."""

    tags = {'markdown'}

    def __init__(self, environment):
        super().__init__(environment)
        environment.extend(markdowner=markdown.Markdown(extensions=MARKDOWN_EXTENSIONS))

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endmarkdown'], drop_needle=True)
        return CallBlock(self.call_method('_render_markdown'), [], [], body).set_lineno(lineno)

    def _render_markdown(self, caller):
        return self.environment.markdowner.convert(self._dedent(caller()))

    def _dedent(self, text):
        return textwrap.dedent(text.strip('\n'))
