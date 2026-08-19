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
    "sphinx.ext.napoleon",
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
]

html_theme = "furo"

html_theme_options = {
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "source_repository": "https://github.com/epics-extensions/run-iocsh",
    "source_branch": "main",
    "source_directory": "docs/",
    "sidebar_hide_name": False,
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/epics-extensions/run-iocsh",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0016 8c0-4.42-3.58-8-8-8z"/>
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
