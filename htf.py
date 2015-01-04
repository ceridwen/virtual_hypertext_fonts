import glob
import re
import fontforge

# For fonts with .pfb files, use fontforge to find the Unicode code points.
for filename in glob.glob('STIXGeneral-Regular.pfb'):
    font = fontforge.open(filename)
    print filename, font.fontname
    htf = open(filename.replace('pfb','htf'),'w')

    # Try to change the encoding
    encoding = fontforge.loadEncodingFile('stix-extra2.enc')
    print font.encoding, encoding
    font.encoding = encoding
    print font.encoding, encoding

    print len(font)

    for glyph in font.glyphs('encoding'):
        print glyph.encoding, glyph.unicode, glyph.comment, glyph.glyphname

    # I need the first and last elements for the first line of the
    # .htf file and to know which range to loop over.  One might think
    # that len(font) would be useful here, but for some reason it
    # corresponds to neither the actual number of glyphs in the font
    # table nor the position of the last glyph in the table.
    # first = font[0].encoding
    # glyphlist = [i for i in font.glyphs('encoding')]
    # last = glyphlist[-1].encoding
    # htf.write(filename.replace(".pfb","") + " " + str(first) + " " + str(last) + "\n")

    # # I can't loop over the iterator font.glyphs because there are
    # # gaps where the .pfb files don't have any glyphs, and tex4ht
    # # complains if the number of lines in the .htf file and the
    # # position of the last glyph are different.  Thus, I have to fill
    # # in the gaps with blank lines.  This means that I have to range
    # # over all values between the positions of the first and last
    # # glyphs and advance the iterator manually.
    # glyphs = font.glyphs('encoding')
    # glyph = glyphs.next()
    # for i in range(first, last + 1):
    #     # Read this as "if there is a glyph at this position"
    #     if glyph.encoding == i:
    #         # Fontforge returns -1 for glyphs without Unicode code
    #         # points.  I put blank lines in for them.
    #         if glyph.unicode != -1:
    #             htf.write("'&#" + str(hex(glyph.unicode)).lstrip("0") + ";' '' " + str(i) + " " + glyph.glyphname + "\n")
    #         else:
    #             htf.write("'' ''" + str(i) + " " + glyph.glyphname + "\n")
    #     else:
    #         htf.write("'' '' " + str(i) + "\n")
    #     if glyph.encoding == i and i < last:
    #         glyph = glyphs.next()
    # htf.write(filename.replace(".pfb",'') + " " + str(first) + " " + str(last) + "\n")
    htf.close()


for filename in glob.glob('stix-extra2.enc'):
    print filename
    enc = open(filename,'r')
    htf = open('test.enc','w')
    first = 0
#   last = subprocess.check_output(['grep', '-c', '"/uni"', filename])
    last = 255
    htf.write(filename.replace(".enc","") + " " + str(first) + " " + str(last) + "\n")
    i = first

    # Sometimes a line will have a / followed by either a normal
    # character or some word like "macron."  Since I have no idea what
    # something like "macron" should correspond to in the .htf, I just
    # pass it through.

    comment = re.compile(r'%.*')
    postscript = re.compile(r'/([\.\w]+)\s+')
    i = -1
    for line in enc:
        # Split the line into "everything before a %" and "everything
        # after a %" to take care of comments, then return the actual
        # Postscript commands including .notdef as a list of strings.
        for character in postscript.findall(comment.split(line)[0]):
            # The first Postscript command is the font name.  FIXME:
            # the font name needs to go on the first and last lines of
            # the .htf file.  FIXME: the first variable is badly
            # overloaded
            if first == 0:
                first = 1
            # Unicode characters
            elif character.startswith('uni'):
                htf.write("'&#x" + character.replace("uni","") + ";' '' " + str(i) + " \n")
            # Undefined characters
            elif character == '.notdef':
                htf.write("'' '' " + str(i) + "\n")
            # Everything else
            else:
                htf.write(character + " '' " + str(i) + "\n")
            i = i + 1
    htf.write(filename.replace(".enc","") + " " + str(first) + " " + str(last) + "\n")
    enc.close()
    htf.close()
