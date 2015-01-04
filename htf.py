#!/usr/bin/python

import fontforge
import os.path

def generate_htf(pfb, enc = None, htf_name = None, quiet = False, overwrite = False):
    """ Generates an htf file from a font's glyph file and encoding."""
    font = fontforge.open(pfb)

    # Change the encoding, if necessary.
    if enc:
        font.encoding = fontforge.loadEncodingFile(enc)

    # Set the output file's name.
    if htf_name:
        pass
    elif enc:
        htf_name = enc.replace('.enc','.htf')
    else:
        htf_name = pfb.replace('.pfb','.htf')

    if not overwrite and os.path.exists(htf_name):
        print "Didn't overwrite " + htf_name
        return

    if not quiet:
        print 'Generating ' + htf_name + ' for the font ' + font.fontname + ' using characters from ' + pfb + ' with the encoding ' + font.encoding,
        if enc: 
            print 'from ' + str(enc),
        print

    with open(htf_name,'w') as htf:

        # I can't loop over the iterator font.glyphs because there are
        # gaps in the encodings where the fonts don't have any glyphs,
        # and tex4ht complains if the number of lines in the .htf file
        # and the difference between the positions of the first and
        # last glyphs are different.  Thus, I have to fill in the gaps
        # with blank lines.  This means that I have to range over all
        # values between the positions of the first and last glyphs
        # and advance the iterator manually.
        glyphs = font.glyphs('encoding')
        glyph = glyphs.next()

        # Position of the first glyph in the encoding
        first = glyph.encoding

        # It's impossible to prepend to a file, so I write a
        # placeholder line to the beginning that I later overwrite,
        # with three spaces of padding where the position of the last
        # glyph will go.
        htf.write(htf_name.replace(".htf","") + " " + str(first) + "    \n")

        # There may be more than 256 glyphs in the font, but TeX can
        # only handle 256 and consequently .htf files shouldn't ever
        # need to have more than 256 characters.
        for i in range(first, 256):
            # When operating on .pfb files with glyphs at positions
            # 256 or higher, the iterator will happily return them but
            # they're outside the positions that TeX cares about, so I
            # have to break.
            if glyph.encoding > 255:
                break
            # Last will eventually hold the position of the last glyph
            # that occurs at or before the 255th position
            # (zero-indexed).
            last = i
            # Read this as "if there is a glyph at this position"
            if glyph.encoding == i:
                if glyph.unicode == -1:
                    # Fontforge returns -1 for glyphs without Unicode
                    # code points.  I request a pictorial character
                    # for those glyphs by setting the class, the
                    # second field in the .htf file, to '1'.
                    htf.write("'' '1' " + str(i) + " " + glyph.glyphname + "\n")
                else:
                    htf.write("'&#" + str(hex(glyph.unicode)).lstrip("0") + ";' '' " + str(i) + " " + glyph.glyphname + "\n")
            # If there are too few glyphs in the font, it's possible
            # I'll reach the end of the iterator before the end of the
            # loop, so catch the exception and break out early if that
            # happens.
                try:
                    glyph = glyphs.next()
                except StopIteration:
                    break
            else:
                # No character here, write a blank line.
                htf.write("'' '' " + str(i) + "\n")
 
        # Write the last line and then rewrite the first line of the
        # file now that I know where the last glyph is.
        htf.write(htf_name.replace(".htf","") + " " + str(first) + " " + str(last) + "\n")
        htf.seek(0)
        htf.write(htf_name.replace(".htf","") + " " + str(first) + " " + str(last).ljust(3) + "\n")
    htf.closed

# Command line handler
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 'This script generates virtual hypertext font files for use with TeX4ht from PostScript Font Binary files and font encoding files.')
    # These two file names have to be passed to the FontForge module, not
    # opened as file objects.
    parser.add_argument('pfb_file', help = 'The name of a PostScript Font Binary file.')
    parser.add_argument('-e', '--encoding_file', help = 'The name of a font encoding file.')
# I could open the .htf file here as a file object, but I want its
# default name to depend on the names of the previous two files, which
# I can't get without calling parse_args(), so instead I open it
# manually.
    parser.add_argument('htf_file', nargs='?', default = None, help = 'The name of the output htf file.  Defaults to the name of the encoding file, first, and then the name of the pfb file, with .enc or .pfb respectively replaced with .htf.')
    parser.add_argument('-q', '--quiet', action = 'store_true', help = 'Operate with no output.')
    parser.add_argument('-f', '--force', action = 'store_true', help ='Overwrite existing files.')
    parser.add_argument('-V', '--version', action = 'version', version = '%(prog) 1.0.0', help = 'Print version information and exit.')
    args = parser.parse_args()

    generate_htf(args.pfb_file, args.encoding_file, args.htf_file, args.quiet, args.force)

    # Input validation possibly harmful since FontForge can handle
    # other types of files.

    # import subprocess

    # filetype = subprocess.check_output(['file', htf_name])
    # print filetype,
    # if filetype.count('PostScript Type 1 font program data'):
    #     if enc:
    #         generate_htf(htf_name, enc)
    #         enc = None
    #     else:
    #         generate_htf(htf_name)
    # elif filetype.count('PostScript document text conforming DSC level 3.0') and htf_name.count('.enc'):
