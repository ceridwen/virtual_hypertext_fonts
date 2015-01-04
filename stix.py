#!/usr/bin/python

import glob
import os.path
import generate_htf
import aliases
import new

def font_css(font):
    css = ''
    if 'it' in font:
        css = css + 'font-style: italic; '
    if 'generalsc' in font:
        css = css + 'font-font: small-caps; '
    # I'm treating all blackboard bold fonts as bold.
    if 'bold' in font or 'bb' in font:
        css = css + 'font-weight: bold; '
    if 'sf' in font:
        css = css + 'font-family: sans-serif; '
    if 'scr' in font or 'cal' in font:
        css = css + 'font-family: cursive; '
    return css.rstrip(' ')

# Text fonts
for path in glob.glob(os.path.expanduser('~/texmf/fonts/tfm/public/stix/*-stixgeneral.tfm')):
    # Extract the base font's name from the path
    font = path.split('/')[-1].replace('.tfm','')
    print 'Generating aliases for ' + font + '.tfm'
    print [x.split('/')[-1].replace('.tfm','') for x in glob.glob(os.path.expanduser('~/texmf/fonts/tfm/public/stix/') + font + '*.tfm')]
    # All STIX text fonts have standard encodings
    aliases.alias(font, [x.split('/')[-1].replace('.tfm','') for x in glob.glob(os.path.expanduser('~/texmf/fonts/tfm/public/stix/') + font + '*.tfm')], 'known_encoding', font_css)

# Math fonts

# Have to include the italics math fonts while excluding the bold
# versions because the italics versions have different symbols.  No
# simple wildcard pattern can match the necessary math fonts.
for path in glob.glob(os.path.expanduser('~/texmf/fonts/tfm/public/stix/stix-*.tfm')):
    if not '-bold' in path:
        font = path.split('/')[-1].replace('.tfm','')
        print "Generating " + font + ".htf"
        if 'stix-math' in font:
            generate_htf.generate_htf(font + '.pfb')
            # The math fonts only have bold variants
            aliases.alias(font, [font, font + '-bold'], None, font_css)
        else:
            # The extra fonts have no variants needing aliases
            generate_htf.generate_htf('STIXGeneral-Regular.pfb', font + '.enc')

# The nominally-OT2 fonts have extra glyphs above position 127 so need
# special handling
generate_htf.generate_htf('STIXGeneral-Regular.pfb', 'stix-ot2.enc', 'ot2-stixgeneral.htf', overwrite = True)
aliases.alias('ot2-stixgeneral', [x.split('/')[-1].replace('.tfm','') for x in glob.glob(os.path.expanduser('~/texmf/fonts/tfm/public/stix/ot2-stixgeneral*.tfm'))], None, font_css)

# Make a test file
new.test_file('stix', [x.split('/')[-1].replace('.tfm','') for x in glob.glob(os.path.expanduser('~/texmf/fonts/tfm/public/stix/*.tfm'))])
