"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

from importlib.metadata import version as get_version

project = "run-iocsh"
copyright = "2025, European Spallation Source ERIC"  # noqa: A001
author = "European Spallation Source ERIC"
try:
    version = get_version("run-iocsh")
    release = version
except Exception:
    # Fallback when package is not installed
    version = "dev"
    release = "dev"


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",  # Markdown support
    "sphinx.ext.intersphinx",  # Cross-references to other docs
    "sphinx.ext.viewcode",  # "View Source" links
    "sphinx.ext.todo",  # TODO directive support
    "autoapi.extension",  # Automatic API documentation
    "sphinx_copybutton",  # Copy buttons on code blocks
]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["Thumbs.db", ".DS_Store"]

autoapi_dirs = ["../run_iocsh"]
autoapi_type = "python"
autoapi_file_patterns = ["*.py"]
autoapi_ignore = ["*/tests/*", "*/test_*"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"

# Theme options are theme-specific
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#2980B9",
        "color-brand-content": "#2980B9",
        "color-admonition-title--note": "#2980B9",
        "color-admonition-title--tip": "#2980B9",
        "color-admonition-title--important": "#2980B9",
        "color-admonition-title--caution": "#E67E22",
        "color-admonition-title--warning": "#E74C3C",
        "font-stack": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        "font-stack--monospace": "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Source Code Pro', monospace",
        "font-size--small": "0.875rem",
        "font-size--small--2": "0.8125rem",
        "font-size--small--3": "0.75rem",
        "font-size--small--4": "0.6875rem",
        "font-size--normal": "1rem",
        "font-size--large": "1.125rem",
        "font-size--large--2": "1.25rem",
        "font-size--large--3": "1.5rem",
        "font-size--large--4": "1.875rem",
        "font-size--large--5": "2.25rem",
        "font-size--large--6": "3rem",
        "line-height": "1.6",
        "line-height--heading": "1.2",
        "font-weight--normal": "400",
        "font-weight--bold": "600",
        "font-weight--heading": "600",
    },
    "dark_css_variables": {
        "color-brand-primary": "#3498DB",
        "color-brand-content": "#3498DB",
        "color-admonition-title--note": "#3498DB",
        "color-admonition-title--tip": "#3498DB",
        "color-admonition-title--important": "#3498DB",
        "color-admonition-title--caution": "#F39C12",
        "color-admonition-title--warning": "#E74C3C",
        "font-stack": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        "font-stack--monospace": "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Source Code Pro', monospace",
        "font-weight--normal": "400",
        "font-weight--bold": "600",
        "font-weight--heading": "600",
    },
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "source_repository": "https://gitlab.esss.lu.se/e3/run-iocsh",
    "source_branch": "main",
    "source_directory": "docs/",
    "source_edit_link": "https://gitlab.esss.lu.se/e3/run-iocsh/-/edit/main/docs/{filename}",
    "source_view_link": "https://gitlab.esss.lu.se/e3/run-iocsh/-/blob/main/docs/{filename}",
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

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
html_sidebars = {}

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (relative to this directory) to use as a favicon
# of the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

html_show_sourcelink = True
html_show_sphinx = True
html_show_copyright = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "e3": ("http://e3.pages.esss.lu.se/", None),
    "epics": ("https://docs.epics-controls.org/en/latest/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx.
language = "en"

myst_admonition_enable = True
myst_deflist_enable = True
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "substitution",
]

# If true, `todo` and `todoList` directives produce output
todo_include_todos = True

# Ignore highlighting ansi in notebooks
suppress_warnings = [
    "misc.highlighting_failure",
    "myst.header",
    "myst.xref_missing",
]

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# The reST default role (used for this markup: `text`) to use for all documents.
default_role = "any"

# If true, keep warnings as "system message" paragraphs in the built documents.
keep_warnings = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ["run_iocsh."]
