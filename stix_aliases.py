#!/usr/bin/python

import glob
# import re

# This program generates external aliases, from STIX fonts to other
# .htf files based on their encodings, and internal aliases, aliases
# from STIX fonts to other STIX fonts.

# These are some prototype .htf files for setting up external aliases.
# For the STIX fonts, I only need T1, OT1, OT2, and TS1, but I might
# as well keep the others since I bothered to find them.

known_encodings = {'t1': 'lm-ec', 'ts1': 'tcrm', 'ot1': 'lm-rep-cmrm', 'ot2' : 'wncyr', 'oms' : 'cmsy', 'oml' : 'cmmi', 'omx' : 'cmex'}

# T1 /usr/share/texmf/tex4ht/ht-fonts/unicode/lm/lm-ec.htf
# TS1 /usr/share/texmf/tex4ht/ht-fonts/unicode/jknappen/tc/tcrm.htf
# OMS /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmsy.htf
# OML /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmmi.htf
# OMX /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmex.htf
# OT1 /usr/share/texmf/tex4ht/ht-fonts/unicode/lm/lm-rep-cmrm.htf
# OT2 /usr/share/texmf/tex4ht/ht-fonts/unicode/ams/cyrillic/wncyr.htf

def alias(path, mode):
    """Creates an alias to an .htf file with a standard encoding and adds CSS font properties to an .htf file for all variants of a font."""
    # Split the path using '/' and extract the base file name
    font = path.split('/')[-1].replace('.tfm','')
    print font
    # For the text fonts all font variants go in the same file
    if mode == 'w':
        variants = [x.split('/')[-1].replace('.tfm','') for x in glob.glob("/home/cara/texmf/fonts/tfm/public/stix/" + font + "*.tfm")]
    # The math fonts only have bold variants
    elif mode == 'a' and 'stix-math' in font:
        variants = [font, font + '-bold']
    # The extra fonts have no variants
    else:
        variants = [font]
    print variants
    with open(font + '.htf', mode) as htf:
        if mode == 'w':
            # Alias to an .htf file with a known encoding for the text fonts
            htf.write("." + known_encodings[font.split("-")[0]] + "\n")
        for variant in variants:
            css = ''
            if 'it' in variant:
                css = css + 'font-style: italic; '
            if 'generalsc' in variant:
                css = css + 'font-variant: small-caps; '
            # I'm treating all blackboard bold fonts as bold.
            if 'bold' in variant or 'bb' in variant:
                css = css + 'font-weight: bold; '
            if 'sf' in variant:
                css = css + 'font-family: sans-serif; '
            if 'scr' in variant or 'cal' in variant:
                css = css + 'font-family: cursive; '
            print variant, css
            if css:
                htf.write("htfcss: " + variant + " " + css.rstrip(" ") + "\n")
    htf.closed

# Text fonts
for file in glob.glob("/home/cara/texmf/fonts/tfm/public/stix/*-stixgeneral.tfm"):
    alias(file, "w")

# Math fonts

# Have to include the italics math fonts while excluding the bold
# versions because the italics versions have different symbols.  No
# simple wildcard pattern can match the necessary math fonts.
for file in glob.glob("/home/cara/texmf/fonts/tfm/public/stix/stix-*.tfm"):
    if not '-bold' in file:
        alias(file, "a")
