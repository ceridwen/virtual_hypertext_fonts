#!/usr/bin/python

import glob
import re
import collections # Provides a dictionary subclass defaultdict
import generate_htf

# I don't know if this is general or if the .map format is more
# complicated.  This only accepts lines with .enc files on them.
postscript = re.compile(r'([-\w]+\b).*?<(\b[-\w]+\.enc\b).*?<(\b[-\w]+\.pfb\b)')

# Accepts the name of a map file as a string and returns a dictionary
# of lists with the enc file names as keys and lists of font names as
# values.
def parse_map(map):
    """Uses a map file to create lists of fonts with the same encoding."""
    # defaultdict provides an easier way to group key-value pairs
    # into lists
    # https://docs.python.org/2/library/collections.html#collections.defaultdict
    d = collections.defaultdict(list)
    with open(map, 'r') as file:
        for line in file:
            # Use try-except to ignore lines that don't match the regex
            try: 
                # For the Droid fonts I only need the name and
                # encoding, but in general I might need the pfb too in
                # which case I'd have to change the data structure.
                [name, enc, pfb] = postscript.match(line).groups()
                d[enc].append(name)
            except AttributeError:
                pass
    file.closed
    return d


# T1 /usr/share/texmf/tex4ht/ht-fonts/unicode/lm/lm-ec.htf
# TS1 /usr/share/texmf/tex4ht/ht-fonts/unicode/jknappen/tc/tcrm.htf
# OMS /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmsy.htf
# OML /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmmi.htf
# OMX /usr/share/texmf/tex4ht/ht-fonts/unicode/cm/cmex.htf
# OT1 /usr/share/texmf/tex4ht/ht-fonts/unicode/lm/lm-rep-cmrm.htf
# OT2 /usr/share/texmf/tex4ht/ht-fonts/unicode/ams/cyrillic/wncyr.htf
# LGR /usr/share/texmf/tex4ht/ht-fonts/unicode/cbgreek/grmn.htf

# I don't understand why tex4ht has aliases for lbrm and lcrm that
# link to larm, since the symbols are different.  I can't find a
# prototype for X2 at all.

# T2A, T2B, T2C, X2 /usr/share/texmf/tex4ht/ht-fonts/unicode/lh/lh-t2a/larm.htf

known_encodings = {'t1': 'lm-ec', 'ts1': 'tcrm', 'ot1': 'lm-rep-cmrm', 'ot2' : 'wncyr', 'oms' : 'cmsy', 'oml' : 'cmmi', 'omx' : 'cmex', 't2a' : 'larm', 't2b' : 'lbrm', 't2c' : 'lcrm', 'x2' : 'larm', 'lgr' : 'grmn'}


# Accepts the name of a font, the names of all variants of that font,
# and a mode ('w' or 'a') that determines whether it appends to an
# existing htf file or creates a new one.
def alias(base, variants, mode):
    """Creates an alias to an .htf file for a font with a standard encoding and adds CSS font properties to an .htf file for all variants of a font."""
    with open(base + '.htf', mode) as htf:
        if mode == 'w':
            # Alias to an .htf file with a known encoding.
            for encoding in known_encodings:
                if encoding in base.lower():
                    htf.write("." + known_encodings[encoding] + "\n")
        for variant in variants:
            css = ''
            # Slanted and italic are mutually exclusive.  They never
            # appear together in the Droid fonts and shouldn't
            # anywhere.
            if 'Italic' in variant:
                css = css + 'font-style: italic; '
            elif 'Slanted' in variant:
                css = css + 'font-style: oblique; '
            if 'SmallCaps' in variant:
                css = css + 'font-variant: small-caps; '
            if 'Bold' in variant:
                css = css + 'font-weight: bold; '
            # Give monospace priority over sans-serif
            if 'Mono' in variant:
                css = css + 'font-family: monospace; '
            elif 'Sans' in variant:
                css = css + 'font-family: sans-serif; '
            print variant, css
            if css:
                htf.write("htfcss: " + variant + " " + css.rstrip(" ") + "\n")
    htf.closed

# Font groups with non-standard encodings
fonts = parse_map('droid.map')
for enc in fonts:
    # Create one htf for each encoding.
    generate_htf.generate_htf('DroidSerif-Regular.pfb', enc, enc.replace('droid', 'DroidSerif-Regular').replace('enc','htf'))
    alias(enc.replace('droid', 'DroidSerif-Regular').replace('.enc',''), fonts[enc], 'a')

# Font groups with standard encodings

# Matches the base font name
serifregular = re.compile(r'DroidSerif-Regular-[12abcglrstx]{2,3}.tfm')
for path in glob.glob("/usr/share/texlive/texmf-dist/fonts/tfm/public/droid/*.tfm"):
    # Extract the base font's file name from the path
    file = path.split('/')[-1]
    if serifregular.search(file):
        # The list comprehension here just extracts each font name from the path
        alias(file.replace('.tfm',''), [x.split('/')[-1].replace('.tfm','') for x in glob.glob("/usr/share/texlive/texmf-dist/fonts/tfm/public/droid/*" + file.replace("DroidSerif-Regular",""))], 'w')
