#!/usr/bin/python3

import fontforge
# import os.path
import re
import collections
import contextlib
import logging
from dvilike import OpcodeCommandsMachine, VFProcessor


def parse_map(map_file):
    """Extracts font names, encodings, and Type1 glyph files from a map file.

    This parser was built using the format description here:
    https://www.tug.org/texinfohtml/dvips.html#psfonts_002emap

    Briefly, each line of a map file that doesn't start with one of
    the comment characters contains the TeX name of a font, a Type1
    font glyph file (pf[ab] file), and optionally Postscript code
    enclosed in double quotes (spaces are allowed in the double
    quotes), a Postscript name for the font, and/or an encoding file.

    Args:
        map: A readable file object pointing to a map file.

    Returns:
        A list of named tuples each containing the TeX font name (.tfm
        file name), the Postscript name, any Postscript code, the
        encoding file name, and the pf[ab] file name for each font in
        the map file.
    """
    font = collections.namedtuple('font', 'tex_name ps_name ps_code enc_name type1_name')
    fonts = []

    # These regexes match special words in the format

    # Matches anything enclosed in double quotes, Postscript code
    ps_regex = re.compile('"([^"]*)"')
    # Matches words starting with '<[' or starting with '<' and ending
    # with '.enc', encoding files
    enc_regex = re.compile('<(\[\S+|\S+\.enc)')
    # Matches words starting with '<<' or starting with '<' and ending
    # with '.pf[ab]', Type 1 glyph files
    type1_regex = re.compile('<(<\S+|\S+\.pf[ab])')

    for line in map_file:
        tex_name = None
        ps_name = None
        ps_code = None
        enc_name = None
        type1_name = None
        # Skip lines starting with comment characters
        if not line.startswith((' ', '%', '*', ';', '#')):
            # Extract Postscript code in double quotes
            if ps_regex.search(line):
                ps_code = ps_regex.search(line).group(1)
                line = ps_regex.sub('', line)
            # Break the rest of the line into words
            for word in line.split():
                if enc_regex.match(word):
                    enc_name = enc_regex.match(word).group(1).lstrip('[')
                elif type1_regex.match(word):
                    type1_name = type1_regex.match(word).group(1).lstrip('<')
                # tex_name will be None for the first non-file word
                elif not tex_name:
                    tex_name = word
                    ps_name = word
                # Because of the previous block, tex_name will be
                # the same as ps_name if and only if it's reading
                # the second non-file word
                elif tex_name == ps_name:
                    ps_name = word
            fonts.append(font(tex_name, ps_name, ps_code, enc_name, type1_name))
    return fonts


def test_file(package, tex_names):
    """Generates a LaTeX file to test the .htfs for a font using fonttable.

    Args:
        package: The name of a font package.
        tex_names: A list of the TeX names of the fonts in the package.
    """
    with open(package + '-test.tex', 'w') as test:
        test.write('\\documentclass{article}\n\n')
        test.write('\\usepackage{' + package + '}\n')
        test.write('\\usepackage{fonttable}\n\n')
        test.write('\\begin{document}\n\n')
        for tex_name in sorted(tex_names):
            test.write('\\section{' + tex_name + '}\n')
            test.write('\\fonttable{' + tex_name + '}\n\n')
        test.write('\n\\end{document}\n')


def write_htf(chars, tex_name, htf):
    """ Writes a list of positions and characters to a file in .htf format.

    The format description for .htf files is here:
    https://www.tug.org/applications/tex4ht/mn-htf.html

    .htf files contain strings that are either ASCII characters, HTML
    entities for reserved characters, or HTML entities referring to
    Unicode code points.  This function writes the correct character
    or HTML entity to the output file, assigns characters to
    non-pictorial or pictorial classes based on whether they do or
    don't have a Unicode code point, and adds a comment including the
    character's name (if any) and its position in the file.
    
    Args:
        chars: A dictionary with character positions as keys (255
           should be the highest position) and values as two-element
           named tuples, 'code_point' as an int and 'name' as a
           string, of either one-element strings or a positive int
           representing a Unicode code point (or -1 for characters
           without code points) and an optional string representing a
           character name.
        htf: A writeable file object for the output .htf file.    
    """

    htf.write(tex_name + " " + str(min(chars)) + " " + str(max(chars)) + "\n")
    for i in range(min(chars), max(chars)):
        # Read this as "if there is a glyph at this position"
        if chars[i]:
            if chars[i].str == -1:
                # I request a pictorial character for glyphs without
                # Unicode code points by setting the class, the second
                # field in the .htf file, to '1'.
                htf.write("'' '1' " + str(i) + " " + chars[i].name + "\n")
            elif type(chars[i].str) == string and len(chars[i].str) == 1:
                htf.write(chars[i].str + " '' " + str(i) + " " + chars[i].name + "\n")
            elif type(chars[i].str) == int and chars[i].str > 0:
                htf.write("'&#" + hex(chars[i].str).lstrip("0") + ";' '' " + str(i) + " " + chars[i].name + "\n")
            else:
                logging.error('The output routine write_htf encountered a bad character, probably because of malformed input.')
        else:
            # No character here, write a blank line.
            htf.write("'' '' " + str(i) + "\n")
    htf.write(tex_name + " " + str(min(chars)) + " " + str(max(chars)) + "\n")


def get_characters(font_file, enc_file = None):
    """ Gets a list of characters from a font's glyph file in encoding order.

    This function uses FontForge to get the Unicode code points for
    each glyph from a font file.  Theoretically, it can handle any
    font file that FontForge can read, but tex4ht can only handle
    Type1 font files.

    Args:
        font_file: The name of a font file to open.
        enc_file: The name of an encoding file to open.

    Returns:
       chars: A dictionary with character positions as keys (255
           should be the highest position) and two-element named
           tuples as values, with 'code_point' as an int and 'name' as
           a string, of either one-element strings or a positive int
           representing a Unicode code point (or -1 for characters
           without code points) and an optional string representing a
           character name.
    """

    chars = {}
    character = collections.namedtuple('character', 'code_point name')

    with contextlib.closing(fontforge.open(font_file)) as font:
        # Change the encoding, if necessary.
        if enc_file:
            font.encoding = fontforge.loadEncodingFile(enc_file)

        for glyph in font.glyphs('encoding'):
            # When operating on font files with glyphs at positions
            # 256 or higher, the iterator will happily return them but
            # they're outside the positions that TeX cares about, so I
            # have to break.
            if glyph.encoding > 255:
                break
            chars[glyph.encoding] = character(glyph.unicode, glyph.glyphname)
    return chars


# T1 /usr/share/texmf/tex4ht/ht-fonts/unicode/lm/lm-ec.htf
# TS1 /usr/share/texmf/tex4ht/ht-fonts/unicode/jknappen/tc/tcrm.htf
# OMS /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmsy.htf
# OML /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmmi.htf
# OMX /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmex.htf
# OT1 /usr/share/texmf/tex4ht/ht-fonts/unicode/lm/lm-rep-cmrm.htf
# OT2 /usr/share/texmf/tex4ht/ht-fonts/unicode/ams/cyrillic/wncyr.htf
# LGR /usr/share/texmf/tex4ht/ht-fonts/unicode/cbgreek/grmn.htf
# T2A, T2B, T2C: /usr/share/texmf/tex4ht/ht-fonts/unicode/lh/lh-t2a/l[abc]rm.htf
    
# I don't understand why tex4ht has aliases for lbrm and lcrm that
# link to larm, since the symbols are different.  I can't find a
# prototype for X2 at all, but there's a ldrm.htf in the same
# directory as the t2 fonts so I guessed it might count.

known_encodings = {'t1': 'lm-ec',
                   'ts1': 'tcrm',
                   'ot1': 'lm-rep-cmrm',
                   'ot2' : 'wncyr',
                   'oms' : 'cmsy',
                   'oml' : 'cmmi',
                   'omx' : 'cmex',
                   't2a' : 'larm',
                   't2b' : 'lbrm',
                   't2c' : 'lcrm',
                   'x2' : 'ldrm',
                   'lgr' : 'grmn'}

def external_alias(tex_name, htf):
    """Writes an alias to an .htf file included with tex4ht.

    tex4ht accepts the name of an existing .htf file in lieu of a list
    of characters.  This function uses a font's TeX name to select one
    of the .htf files packaged with tex4ht corresponding to one of the
    standard TeX encodings.

    Args:
        tex_name: The TeX name of a font.
        htf: A writeable file object for the output .htf file.
    """
    for encoding in known_encodings:
        if encoding in tex_name.lower():
            htf.write("." + known_encodings[encoding] + "\n")


# def internal_alias(tex_name, htf):
#     htf.write("." + tex_name + "\n")


def variant_aliases(tex_names, font_css, htf):
    """Adds aliases and appropriate CSS code to an .htf file.

    Rather than requiring a separate .htf file for each font, for
    fonts with the same character set, tex4ht will also accept a list
    of characters or an alias to another .htf file followed by a list
    of font names and CSS font properties.  Note that for fonts named
    after the initial alias or list of characters, tex4ht will *only*
    process fonts whose TeX names can be truncated to the TeX name of
    the font the .htf file itself is named after.  In the output HTML,
    the CSS font properties are added wherever the font appears in the
    original TeX/LaTeX code.  Note that CSS font properties can also
    be applied to the font the .htf file is named after.  This
    function writes font names and CSS font properties to an .htf file.

    Args:
        tex_names: The TeX names of all variants of a font.
        font_css: A function that uses the TeX name of a font to
            assign it appropripate CSS font properties.
        htf: A writeable file object for the output .htf file.
    """
    for tex_name in tex_names:
        css = font_css(tex_name)
        if css:
            htf.write("htfcss: " + tex_name + " " + css + "\n")


class VFtoHTF(OpcodeCommandsMachine):
    """Builds a dictionary describing the characters in a virtual font from a parsed VF file.

    This class is designed to operate on the output of VFParser, a
    class that contains methods to transform a virtual font file (VF
    file) into lists of containers corresponding to the tree structure
    of the VF file itself.  Containers are a dictionary subclass whose
    keys can be accessed using attributes, e.g. container.name.  The
    class may be thought of as a state machine: using the __call__
    function it inherits from OpcodeCommandsMachine, feed it
    containers representing individual commands one at a time and it
    will record the TeX names of the fonts the virtual font refers to
    and then which character in which real font is typeset at a given
    position in the virtual font.

    Attributes:
        chars: A dictionary with character positions in the virtual
            font as keys and lists of two-element named tuples as
            values, each of which has has a 'char_code' attribute
            holding the character to look up in the real font file as
            an int and the TeX name of the real font as a string.
            This attribute serves as the effective return value of the
            class, access it after the class is finished processing
            the VF file.  In most cases, these will be one-element
            lists, but sometimes a virtual font will typeset a single
            character by typesetting two or more characters from the
            real fonts, in which case the list will contain more than
            one element.
    """

    def __init__(self):
        """Initializes the _commands dictionary and several state variables.

        Calls OpcodeCommandsMachine's __init__ to build _commands,
        which maps VF and DVI commands to functions, assigns the
        command 'put' to the function 'set' because the differences
        between the commands don't matter in this context (they both
        typeset characters but change the physical position on the
        page in different ways), and initializes chars; fonts, a
        dictionary that maps the VF file's internal numbers to TeX
        font names; vf_char, the named tuple to hold the position and
        TeX name for a character in a real font; and _default_font,
        the name of the font that appears first in the VF file.
        """
        super().__init__()
        self._commands['put'] = self.set
        self.fonts = {}
        self.chars = collections.defaultdict(list)
        self.vf_char = collections.namedtuple('vf_char', 'char_code tex_name')
        self._default_font = None

    def _vf_char(self, char_code):
        """Returns a vf_char with char_code as the position and _current_font as the font.
        """
        return self.vf_char(char_code, self._current_font)

    def fnt_def(self, container):
        """Sets the default font to the first font and defines all the fonts.

        This function assigns the TeX name of the font that appears
        first in the VF file to _default_font and internal font
        numbers to font TeX names in fonts.
        """
        if not self._default_font:
            self._default_font = container.tex_name
        self.fonts[container.font_num] = container.tex_name

    def char(self, container):
        """Defines which VF character is being typeset and recurses on the DVI code.

        Each time short_char or long_char is called in a VF file, the
        font that will be used to typeset characters in the DVI code
        is reset to the default.  _current_char holds the position in
        the virtual font of the character to be typeset.  It then
        calls itself on each command in the DVI code.  The subsequent
        three functions will change the current font (the 'fnt'
        command) and add characters to chars as appropriate (the 'set'
        and 'set_char' commands) when the appropriate commands occur
        in the DVI code.
        """
        self._current_font = self._default_font
        self._current_char = container.char_code
        for dvi_container in container.dvi_code:
            self(dvi_container)

    def fnt(self, container):
        self._current_font = self.fonts[container.font_num]

    def set_char(self, container):
        self.chars[self._current_char].append(self._vf_char(container.opcode))

    def set(self, container):
        self.chars[self._current_char].append(self._vf_char(container.char_code))

    # None of these VF or DVI commands need to be processed to extract
    # the characters from a virtual font file.
    def pre(self, container):
        pass
    def post(self, container):
        pass
    def set_rule(self, container):
        pass
    def put_rule(self, container):
        pass
    def push(self, container):
        pass
    def pop(self, container):
        pass
    def right(self, container):
        pass
    def w(self, container):
        pass
    def x(self, container):
        pass
    def down(self, container):
        pass
    def y(self, container):
        pass
    def z(self, container):
        pass
    def xxx(self, container):
        pass


if __name__ == '__main__':
    file = 'DroidSerif-Regular-ot1.vf'
    # file = 'extending_hardys_proof.dvi'

    with open(file, 'rb') as f:
        machine = VFtoHTF()
        for x in VFProcessor(f):
            print(x)
            machine(x)
        print(machine.chars)


# # Command line handler
# if __name__ == '__main__':
#     import argparse
#     parser = argparse.ArgumentParser(description = 'This script generates virtual hypertext font files for use with TeX4ht from PostScript Font Binary glyph files, font encoding files, and virtual font files.  When called with only font files or only font and encoding files, it outputs as many .htf files as given font files.  It assigns encoding files and output file names to font files in order, so any font files without encoding files must come after font files with encoding files.  When called with a virtual font file, it will attempt to construct one .htf file for the virtual font.  If also supplied with a map file, it will search the map file for the font names and files in the virtual font.  Otherwise, it will assume that fonts are in the same order as they are in the virtual font file.')
#     # Some of these I can't open as file objects.  The glyph and
#     # encoding files have to be passed to FontForge methods as file
#     # names, I want the default name of the .htf file to depend on the
#     # glyph or encoding file which I won't know until after parsing
#     # the arguments.  I prefer to pass file names to parse_vf
#     # parse_map because it makes them easier to use in other scripts.
#     parser.add_argument('pfb_file', nargs = '+', help = 'The name(s) of PostScript Font Binary file(s).')
#     parser.add_argument('-e', '--encoding_file', nargs = '+', help = 'The name(s) of font encoding file(s).')
#     parser.add_argument('-vf', '--virtual_font_file', help = 'The name of a virtual font file.')
#     parser.add_argument('-m', '--map_file', help = 'The name of a map file.')
#     parser.add_argument('-o', '--output_file', nargs = '+', help = 'The name(s) of output virtual hypertext font file(s).  The default is the name of the virtual font file, the encoding file, and then the name of the pfb file, in order, with .vf, .enc, or .pfb respectively replaced with .htf.')
#     parser.add_argument('-q', '--quiet', action = 'store_true', help = "Don't print non-error messages.")
#     parser.add_argument('-f', '--force', action = 'store_true', help ='Overwrite existing files.')
#     parser.add_argument('-V', '--version', action = 'version', version = '%(prog) 1.0.0', help = 'Print version information and exit.')
#     args = parser.parse_args()

    # Should probably replace these complicated conditionals with some
    # kind of OO class structure that has different behavior.

    # if args.virtual_font_file:
    #     font_char_lists = []
    #     out = vf.replace('.vf','.htf')
        
    #     # Use the map file to line up the encoding and font files
    #     if args.map_file:
            
    #         # TODO: this is severely broken
    #         fonts = []
    #         for file in pfb:
    #             fonts.append(fontforge.open(file))
    #             if enc:
    #                 encodings = []
    #                 for file in enc:
    #                     encodings.append(fontforge.loadEncodingFile(file))
    #                 else:
    #                     pass

    # else:
    #     # TODO: This is broken by 3.3 because map now truncates like zip does in 2.7
    #     for font in map(None, args.pfb_file, args.encoding_file, args.output_file):
    #         # Set the output file's name.
    #         if font[2]:
    #             out = font[2]
    #         elif font[1]:
    #             out = font[1].replace('.enc','.htf')
    #         else:
    #             out = font[0].replace('.pfb','.htf')

    #         if not args.quiet:
    #             print('Generating ' + out + ' using characters from ' + pfb)
    #             if font[1]:
    #                 print(' with the encoding from ' + font[1], end=' ')
    #             print()

    #         # Write to file
    #         write_htf(out, get_characters(font[0], font[1]), args.force)


    # # Don't overwrite an existing file unless specifically requested
    # if not overwrite and os.path.exists(name):
    #     print("Didn't overwrite " + name)
    #     return
