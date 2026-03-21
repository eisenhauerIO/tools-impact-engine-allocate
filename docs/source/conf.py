"""Sphinx configuration for Impact Engine Allocate documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = "Impact Engine Allocate"
author = "eisenhauerIO"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "myst_parser",
    "nbsphinx",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
templates_path = ["_templates"]
exclude_patterns = ["build", "GUIDELINES.md"]
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 2,
}
html_static_path = ["_static"]

copyright = "eisenhauerIO — MIT License (code) | CC BY 4.0 (content)"

html_context = {
    "display_github": True,
    "github_user": "eisenhauerIO",
    "github_repo": "tools-impact-engine-allocate",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

nbsphinx_execute = "always"
nbsphinx_allow_errors = False

_gh_repo = "https://github.com/eisenhauerIO/tools-impact-engine-allocate"
_colab = "https://colab.research.google.com/github/eisenhauerIO/tools-impact-engine-allocate"
nbsphinx_prolog = rf"""
{{% set docname = env.doc2path(env.docname, base=None) %}}

.. |colab| image:: https://colab.research.google.com/assets/colab-badge.svg
    :target: {_colab}/blob/main/docs/source/{{{{ docname }}}}

.. only:: html

    .. nbinfo::
        Download the notebook `here <{_gh_repo}/blob/main/docs/source/{{{{ docname }}}}>`__!
        Interactive online version: |colab|

"""


def setup(app):
    """Register custom static files with Sphinx."""
    app.add_css_file("custom.css")
