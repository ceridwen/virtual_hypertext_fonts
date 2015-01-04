#!/usr/bin/python

import fontforge
import os.path
import glob
import re
import collections
import subprocess
from dvivf import OpcodeCommandsMachine, VFTranslator

# Accepts the name of a map file as a string and returns a list of
# named tuples each containing the TeX font name (.tfm file name), the
# Postscript name, any ps code enclosed in double quotes, the encoding
# file, and the pf[ab] file.
def parse_map(map):
    """Parses a map file into a list of font names, encodings, and glyph files."""
    font = collections.namedtuple('font', 'tex_name ps_name ps_code encoding type1')
    fonts = []

    # This parser was built using the format description here:
    # https://www.tug.org/texinfohtml/dvips.html#psfonts_002emap

    # These regexes match special words in the format

    # Matches anything enclosed in double quotes, Postscript code
    ps_regex = re.compile('"([^"]*)"')
    # Matches words starting with '<[' or starting with '<' and ending
    # with '.enc', encoding files
    enc_regex = re.compile('<(\[\S+|\S+\.enc)')
    # Matches words starting with '<<' or starting with '<' and ending
    # with '.pf[ab]', Type 1 glyph files
    type1_regex = re.compile('<(<\S+|\S+\.pf[ab])')

    with open(map, 'r') as file:
        for line in file:
            tex_name = None
            ps_name = None
            ps_code = None
            encoding = None
            type1 = None
            # Skip lines starting with comment characters
            if not line.startswith((' ', '%', '*', ';', '#')):
                # Extracts Postscript code in double quotes
                if ps_regex.search(line):
                    ps_code = ps_regex.search(line).group(1)
                    line = ps_regex.sub('', line)
                # Break the rest of the line into words
                for word in line.split():
                    if enc_regex.match(word):
                        encoding = enc_regex.match(word).group(1).lstrip('[')
                    elif type1_regex.match(word):
                        type1 = type1_regex.match(word).group(1).lstrip('<')
                    # tex_name will be None for the first non-file word
                    elif not tex_name:
                        tex_name = word
                        ps_name = word
                    # tex_name == ps_name for the second non-file word
                    elif tex_name == ps_name:
                        ps_name = word
                fonts.append(font(tex_name, ps_name, ps_code, encoding, type1))
    file.closed
    return fonts


# Generates a LaTeX file to test the .htfs for a font using fonttable.
# Accepts the name of a package and a list of fonts to test.
def test_file(package, fonts):
    with open(package + '-test.tex','w') as test:
        test.write('\\documentclass{article}\n\n')
        test.write('\\usepackage{' + package + '}\n')
        test.write('\\usepackage{fonttable}\n\n')
        test.write('\\begin{document}\n\n')
        for font in sorted(fonts):
            test.write('\\section{' + font + '}\n')
            test.write('\\fonttable{' + font + '}\n\n')
        test.write('\n\\end{document}\n')
    test.closed


# The conditionals here should probably be replaced with OO
# polymorphism.

# Accepts the name of a font; the names of all variants of that font;
# the name of a font to make an internal alias to, 'known_encoding' to
# get an external alias to a packaged .htf file, or None to append
# font CSS attributes to an existing htf file; and a function that
# takes a file name and returns a (possibly empty) appropriate string
# of CSS font properties.
def alias(base, variants, alias_font, font_css):
    """Creates an .htf file with an alias to another for a font with a standard encoding and adds CSS font properties to an .htf file for all variants of a font."""

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

    # Without a font to alias to, we must be appending to an existing file
    if not alias_font:
        # The documentation for open warns that "'a' for appending
        # . . .  on some Unix systems means that all writes append to
        # the end of the file regardless of the current seek
        # position," but this function only appends to end so it
        # should be portable.
        mode = 'a'
    else:
        mode = 'w'

    with open(base + '.htf', mode) as htf:
        if alias_font == 'known_encoding':
            # Alias to an .htf file with a known encoding.
            for encoding in known_encodings:
                if encoding in base.lower():
                    htf.write("." + known_encodings[encoding] + "\n")
        elif alias_font:
            htf.write("." + alias_font + "\n")
        for variant in variants:
            css = font_css(variant)
            if css:
                htf.write("htfcss: " + variant + " " + css + "\n")
    htf.closed


class VFtoHTF(OpcodeCommmandsMachine):
    def __init__(self):
        super.__init__(self)
        self._commands['put'] = self.set
        self.fonts = {}
        self.characters = {}
        character = collections.namedtuple('character', ['code', 'font_name'])

    def fnt_def(self, **container):
        if not self.default_font:
            self.default_font = font_name
        self.fonts[font_num] = font_name
        
    def char(self, **container):
        self.current_font = self.default_font
        self.set_character = None
        for command in dvi_code:
            self(command)
        self.characters[code] = character(self.set_character, self.current_font)

    def fnt(self, **container):
        self.set_character = self.fonts[font_num]

    def set_char(self, **container):
        self.set_character = opcode

    def set(self, **container):
        self.set_character = code

    def pre(self, **container):
        pass
    def post(self, **container):
        pass
    def set_rule(self, **container):
        pass
    def put_rule(self, **container):
        pass
    def push(self, **container):
        pass
    def pop(self, **container):
        pass
    def right(self, **container):
        pass
    def w(self, **container):
        pass
    def x(self, **container):
        pass
    def down(self, **container):
        pass
    def y(self, **container):
        pass
    def z(self, **container):
        pass
    def xxx(self, **container):
        pass


# Takes the name of a vf file and returns a 
# def parse_vf(vf):
#     """ Extracts fonts and character mappings from a virtual font file. """
#     subprocess.check_output(['vftovp', 'DroidSerif-Regular-ot1.vf'])
#     subprocess.check_output(['vftovp', '-charcode-format=octal', 'DroidSerif-Regular-ot1.vf'])
#    ete2.parser.newick.read_newick(subprocess.check_output(['vftovp', '-charcode-format=octal', 'DroidSerif-Regular-ot1.vf']) + ';')

# S := propertylist+

# propertylist := '('name string|number|propertylist')'


# name is a string, overwrite is a boolean, and characters is a
# dictionary with character positions as keys (255 should be the
# highest position) and values as two-element named tuples of either
# one-element strings or a positive int representing a Unicode code
# point (or -1 for characters without code points) and an optional
# string representing a character name.
def write_htf(name, characters, overwrite = False):
    """ Writes a list of positions and characters to a file in .htf format. """

    # Don't overwrite an existing file unless specifically requested
    if not overwrite and os.path.exists(name):
        print("Didn't overwrite " + name)
        return

    with open(name, 'w') as htf:
        htf.write(name.replace(".htf","") + " " + str(min(characters)) + " " + str(max(characters)) + "\n")
        for i in range(min(characters), max(characters)):
            # Read this as "if there is a glyph at this position"
            if characters[i]:
                if characters[i].str == -1:
                    # Fontforge returns -1 for glyphs without Unicode
                    # code points.  I request a pictorial character
                    # for those glyphs by setting the class, the
                    # second field in the .htf file, to '1'.
                    htf.write("'' '1' " + str(i) + " " + characters[i].name + "\n")
                elif type(characters[i].str) == string and len(characters[i].str) == 1:
                    htf.write(characters[i].str + " '' " + str(i) + " " + characters[i].name + "\n")
                elif type(characters[i].str) == int and characters[i].str > 0:
                    htf.write("'&#" + str(hex(characters[i].str)).lstrip("0") + ";' '' " + str(i) + " " + characters[i].name + "\n")
                else:
                    # TODO
                    raise ValueError()
            else:
                # No character here, write a blank line.
                htf.write("'' '' " + str(i) + "\n")
        htf.write(htf_name.replace(".htf","") + " " + str(min(characters)) + " " + str(max(characters)) + "\n")
    htf.closed


# Use FontForge to get a the characters for a font as a dictionary of
# named tuples containing Unicode code points (or -1 for characters
# without code points) and the name of each character (if it has one).
def get_characters(pfb, enc = None):
    """ Gets a list of characters from a font's glyph file in encoding order."""
    
    # Dictionary to hold the character information
    characters = {}

    font = fontforge.open(pfb)

    # Change the encoding, if necessary.
    if enc:
        font.encoding = fontforge.loadEncodingFile(enc)

    for glyph in font.glyphs('encoding'):
        # When operating on .pfb files with glyphs at positions
        # 256 or higher, the iterator will happily return them but
        # they're outside the positions that TeX cares about, so I
        # have to break.
        if glyph.encoding > 255:
            break

        character = collections.namedtuple('character', ['unicode', 'name'])
        characters[glyph.encoding] = character(glyph.str, glyph.glyphname)
        font.close()
    return characters


# Command line handler
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 'This script generates virtual hypertext font files for use with TeX4ht from PostScript Font Binary glyph files, font encoding files, and virtual font files.  When called with only font files or only font and encoding files, it outputs as many .htf files as given font files.  It assigns encoding files and output file names to font files in order, so any font files without encoding files must come after font files with encoding files.  When called with a virtual font file, it will attempt to construct one .htf file for the virtual font.  If also supplied with a map file, it will search the map file for the font names and files in the virtual font.  Otherwise, it will assume that fonts are in the same order as they are in the virtual font file.')
    # Some of these I can't open as file objects.  The glyph and
    # encoding files have to be passed to FontForge methods as file
    # names, I want the default name of the .htf file to depend on the
    # glyph or encoding file which I won't know until after parsing
    # the arguments.  I prefer to pass file names to parse_vf
    # parse_map because it makes them easier to use in other scripts.
    parser.add_argument('pfb_file', nargs = '+', help = 'The name(s) of PostScript Font Binary file(s).')
    parser.add_argument('-e', '--encoding_file', nargs = '+', help = 'The name(s) of font encoding file(s).')
    parser.add_argument('-vf', '--virtual_font_file', help = 'The name of a virtual font file.')
    parser.add_argument('-m', '--map_file', help = 'The name of a map file.')
    parser.add_argument('-o', '--output_file', nargs = '+', help = 'The name(s) of output virtual hypertext font file(s).  The default is the name of the virtual font file, the encoding file, and then the name of the pfb file, in order, with .vf, .enc, or .pfb respectively replaced with .htf.')
    parser.add_argument('-q', '--quiet', action = 'store_true', help = "Don't print non-error messages.")
    parser.add_argument('-f', '--force', action = 'store_true', help ='Overwrite existing files.')
    parser.add_argument('-V', '--version', action = 'version', version = '%(prog) 1.0.0', help = 'Print version information and exit.')
    args = parser.parse_args()

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
