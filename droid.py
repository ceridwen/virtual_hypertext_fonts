#!/usr/bin/python

import glob
import re
import generate_htf
import aliases
import new
import collections

def font_css(font):
    css = ''
    # Slanted and italic are mutually exclusive.  They never
    # appear together in the Droid fonts and shouldn't
    # anywhere.
    if 'Italic' in font:
        css = css + 'font-style: italic; '
    elif 'Slanted' in font:
        css = css + 'font-style: oblique; '
    if 'SmallCaps' in font:
        css = css + 'font-font: small-caps; '
    if 'Bold' in font:
        css = css + 'font-weight: bold; '
    # Give monospace priority over sans-serif
    if 'Mono' in font:
        css = css + 'font-family: monospace; '
    elif 'Sans' in font:
        css = css + 'font-family: sans-serif; '
    return css.rstrip(' ')

# Make .htfs for fonts with non-standard encodings

# Generate a dictionary of lists of fonts with the same encoding using
# droid.map
fonts = collections.defaultdict(list)
for font in new.parse_map('droid.map'):
    fonts[font.encoding].append(font.tex_name)

# Create one htf for each encoding.
for enc in fonts:
    generate_htf.generate_htf('DroidSerif-Regular.pfb', enc, enc.replace('droid', 'DroidSerif-Regular').replace('enc','htf'))

# Make internal aliases for fonts with non-standard encodings
nonstandard_encoding = re.compile(r'-(0[1234]).tfm')
base_font = re.compile(r'DroidSerif-Regular-0[1234].tfm')
for path in glob.glob('/usr/share/texlive/texmf-dist/fonts/tfm/public/droid/*.tfm'):
    # Split the path using '/' and extract the base file name
    file = path.split('/')[-1]
    if nonstandard_encoding.search(file) and not base_font.match(file):
        print 'Generating an alias for ' + file.replace('.tfm','.htf')
        aliases.alias(file.replace('.tfm',''), [file.replace('.tfm','')], 'DroidSerif-Regular-' + nonstandard_encoding.search(file).group(1), font_css)

# Make external aliases for fonts with standard encodings (except X2; see below)
standard_encoding = re.compile(r'[12abcglrstx]{2,3}.tfm')
for path in glob.glob('/usr/share/texlive/texmf-dist/fonts/tfm/public/droid/*.tfm'):
    file = path.split('/')[-1]
    if standard_encoding.search(file):
        print 'Generating an alias for ' + file.replace('.tfm','.htf')
        aliases.alias(file.replace('.tfm',''), [file.replace('.tfm','')], 'known_encoding', font_css)

# Cyrillic fonts always cause trouble

# There's no X2-encoded .htf in texlive.  The encguide lists rxrm1000
# as the canonical X2 font, but I can't find an example of it
# anywhere.  Instead, I use cm-super-x2.enc and one of the .pfbs
# listed in cm-super-x2.map to make one.
# generate_htf.generate_htf('sfrm0500.pfb', 'cm-super-x2.enc', 'DroidSerif-Regular-x2.htf')
# for path in glob.glob('/usr/share/texlive/texmf-dist/fonts/tfm/public/droid/*x2.tfm'):
#     file = path.split('/')[-1]
#     if not file == 'DroidSerif-Regular-x2.tfm':
#         print 'Generating an alias for ' + file.replace('.tfm','.htf')
#         aliases.alias(file.replace('.tfm',''), [file.replace('.tfm','')], 'DroidSerif-Regular-x2', font_css)

new.test_file('droid', [x.split('/')[-1].replace('.tfm','') for x in glob.glob('/usr/share/texlive/texmf-dist/fonts/tfm/public/droid/*.tfm')])
