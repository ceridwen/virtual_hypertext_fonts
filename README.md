## Synopsis

This library is a collection of scripts for generating the virtual
hypertext font files
(https://www.tug.org/applications/tex4ht/mn-htf.html) that TeX4ht
(https://www.tug.org/tex4ht/) requires.

## Code Example

The main functions live in htf.py.

* parse_map() extracts the Postscript and TeX names, encodings, and
  Type 1 glyph from a Postscript map file.

* write_htf() takes a mapping with character positions as keys and
  tuples of a Unicode code point and the name of a glyph as values,
  the TeX name of a font, and a file object, then writes to the file
  in the virtual hypertext format.

* get_characters() takes a font file and optionally an encoding file,
  then applies the encoding (if any) to the font and outputs a
  dictionary in the format that write_htf() accepts.

* external_alias() takes a TeX font name and an output file object,
  then uses the TeX name of the font to create a virtual hypertext
  font alias to one of the .htf files packaged with TeX4ht in the
  output file.

* variant_aliases() takes a list of TeX font names, a function that
  assigns CSS properties to fonts based on their names, and an output
  file object, then adds aliases for those fonts to the end of the
  output file.  Unlike for the previous functions, this must be an
  existing file already created with write_htf() or external_alias().

* VFtoHTF() is a class that takes VF files parsed by dvilike.py (see
  Installation below) and converts them into a dictionary suitable for
  processing with write_htf().  To use it, instantiate the class and
  then call the instance on each packet of the parsed VF file.  After
  the end of the VF file, the instance variable chars will contain the
  output dictionary.

Because each font has its own naming conventions and often doesn't
include information on which encodings it uses, building virtual
hypertext font files usually requires writing a specialized script
that calls the above functions.

## Motivation

While TeX4ht contains a library of virtual hypertext fonts for older
fonts, there are no such files for many modern fonts and thus TeX4ht
doesn't support them.  This library mostly automates the process of
generating new virtual hypertext font files.

## Installation

The library functions themselves are all found in htf.py.  The library
requires FontForge (https://fontforge.github.io/) compiled with Python
scripting and Python 3 support
(https://github.com/fontforge/fontforge/blob/master/INSTALL-git.md and
https://fontforge.github.io/en-US/downloads/source/); compiling with
Python 3 support requires setting the PYTHON=python3 (or whatever the
name of your Python 3 interpreter is) environment variable before
running ./configure.  VFtoHTF also requires dvilike.py
(https://github.com/ceridwen/dvilike), which in turns requires
Construct (https://pypi.python.org/pypi/construct).

## Tests

test_file(), a function included in htf.py, takes the name of a font
package (what you'd call with \usepackage{} in LaTeX) and the TeX
names of the fonts in the package to generate a LaTeX file that when
compiled with htlatex will test all the glyphs included in the font
package.
