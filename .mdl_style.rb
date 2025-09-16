# Rules are defined here:
# https://github.com/markdownlint/markdownlint/blob/master/docs/RULES.md
#
# This file defines custom style selections used for ESS documentation
all

# Set unordered list preference
rule 'MD004', :style => :consistent

# Be explicit about desired indent level
rule 'MD007', :indent => 3

# Ignore line length rule in code blocks
rule 'MD013', :code_blocks => false

# Set line length to 120 characters
rule 'MD013', :line_length => 120

# Allow repeated header names in different locations
rule 'MD024', :allow_different_nesting => true

# Use ordered style for numbered lists
rule 'MD029', :style => :ordered

# Allow leading $ sign in console commands
exclude_rule 'MD014'

# Allow html tag syntax (i.e. <tag>) in docs. Not used as tags in our case, but
# to show command line options.
exclude_rule 'MD033'

# Allow bare URLs as the [text](URL) format in Sphinx/MyST markdown allows that
# format, but it fails the MD034 test
exclude_rule 'MD034'

# Allow for anchors at start of file, otherwise they are
# not found in cross-referencing
exclude_rule 'MD041'
