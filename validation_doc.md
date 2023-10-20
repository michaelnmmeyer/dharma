# More exhaustive validation in Oxygen

When you are editing files in Oxygen, they are validated automatically with the
DHARMA RelaxNG schema referenced in the file preamble. The schema location is
given in a processing instruction, for instance:

	<?xml-model href="https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_Schema.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>

The schema verifies many things, but it is not complete and cannot be, due to
limitations of RelaxNG. Thus, in addition to the automatic validation performed
by Oxygen, you need to run an extra validation process. This can be done from
within Oxygen, with a DHARMA-specific validator.

## Setup

In Oxygen, open the Preferences window with Option > Preferences. In the left
tab, navigate to Editor > Document Validation > Custom Validation Engines.
In the right part of the window, click on "New"

## Usage

You need a decent internet connection, because validation is done through file
upload on the DHARMA website.
