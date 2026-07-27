"""Configuration file for the Sphinx documentation builder."""

from importlib.metadata import version as get_version

project = "run-iocsh"
copyright = "2025, European Spallation Source ERIC"  # noqa: A001
author = "European Spallation Source ERIC"
try:
    version = get_version("run-iocsh")
    release = version
except Exception:
    version = "dev"
    release = "dev"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "autoapi.extension",
    "sphinx_copybutton",
]

exclude_patterns = ["Thumbs.db", ".DS_Store"]

autoapi_dirs = ["../run_iocsh"]
autoapi_type = "python"
autoapi_file_patterns = ["*.py"]
autoapi_ignore = ["*/tests/*", "*/test_*"]
autoapi_add_toctree_entry = False
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]

html_theme = "furo"

html_theme_options = {
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "source_repository": "https://gitlab.esss.lu.se/e3/run-iocsh",
    "source_branch": "master",
    "source_directory": "docs/",
    "source_edit_link": "https://gitlab.esss.lu.se/e3/run-iocsh/-/edit/master/docs/{filename}",
    "source_view_link": "https://gitlab.esss.lu.se/e3/run-iocsh/-/blob/master/docs/{filename}",
    "sidebar_hide_name": False,
    "footer_icons": [
        {
            "name": "GitLab",
            "url": "https://gitlab.esss.lu.se/e3/run-iocsh",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 24 24">
                    <path d="M23.6004 9.5927l-.0337-.0862L20.3.9814a.851.851 0 00-.3362-.405.8748.8748 0 00-.9997.0539.8748.8748 0 00-.29.4399l-3.2055 8.3842H7.5373l-3.2056-8.3842a.8573.8573 0 00-.29-.4412.8748.8748 0 00-.9997-.0537.8585.8585 0 00-.3362.4049L.4332 9.5015l-.0325.0862a6.0657 6.0657 0 002.0119 7.0105l.0113.0087.03.0213 4.976 3.7264 2.462 1.863 1.4995 1.1321a1.0085 1.0085 0 001.2197 0l1.4995-1.1321 2.4619-1.863 4.976-3.7264.0113-.0087a6.0657 6.0657 0 002.0094-7.003z"/>
                </svg>
            """,
            "class": "",
        },
    ],
}

html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "_static/logo.svg"
html_sidebars = {}
html_show_sourcelink = True
html_show_sphinx = True
html_show_copyright = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "e3": ("https://e3.pages.ess.eu/", None),
    "epics": ("https://docs.epics-controls.org/en/latest/", None),
}

templates_path = ["_templates"]
master_doc = "index"
language = "en"

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "substitution",
]
# Give headings anchors so intra-page links like [text](#a-heading) resolve.
myst_heading_anchors = 3

todo_include_todos = True

suppress_warnings = [
    "misc.highlighting_failure",
    "myst.header",
    "myst.xref_missing",
]

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

default_role = "any"
keep_warnings = False
add_module_names = True
show_authors = False
pygments_style = "sphinx"
modindex_common_prefix = ["run_iocsh."]
