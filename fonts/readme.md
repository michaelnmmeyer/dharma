# Font Subsetting

We do not use Google Fonts' HTTP API because, for some reason, they do not
include COMBINING RING BELOW in the fonts accessible through the API, although
the character is present in the full fonts that can be manually downloaded from
the website. They also probably exclude other characters useful for us, not
checked further.

Useful documentation for fonts subsetting:

* https://codecolibri.fr/optimiser-ses-polices-web-avec-le-font-subsetting
* https://fonttools.readthedocs.io/en/latest/subset

Google Fonts' API uses a separate file for Latin Basic, another for everything
else, probably to make font loading faster for English-speaking people. And
they use the same font file for all weights viz. they use font files that
bundle several weights instead of using separate files for each weight.

I tried to merge font files, but apparently some things need to be done on font
files for this to work, so I abandoned the idea. For each input font file, we
produce a corresponding subsetted output font file. I initially tried to subset
fonts by Script, but we end up with larger font files than by doing subsetting
by Unicode Block, so I chose the second option.

I only use Noto Fonts for simplicity and because they have a large coverage. I
tried Gentium and Junicode, but they do not look great on a screen, they look
too thin. There might be ways to improve this, but Noto Fonts look OK per
default, so I use them instead.

Font files in "selection" are pulled from the following repositories:

* https://github.com/notofonts/notofonts.github.io
* https://github.com/googlefonts/noto-emoji
* https://github.com/notofonts/noto-cjk

We get noto-emoji from https://fonts.google.com instead of from the github repo.
Because https://github.com/googlefonts/noto-emoji apparently doesn't have the
proper font files.

So far I have not dealt with CJK fonts, although we do need them. The problem
is that we need to know which of C, J and K we need to choose for display,
depending on the language of the output. Not sure how to do this. We need
someone knowledgeable about this to check we are doing the right thing.

There are several versions of each font in Google's repos. Whenever possible, I
choose the fonts under "unhinted/variable" or "unhinted/variable-ttf". (I do
not know the difference between the two.) Unhinted files are smaller than
hinted one without too much loss apparently. And choosing variable fonts makes
us use a single font file instead of many for each font weight, which makes
things simpler; variable font files might also be smaller overall, did not
check that.

## Update

Stopped using NotoSansMath, NotoSansSymbols and NotoSansSymbols2, even though
they have symbols we do need and that are not available in Noto Serif, e.g. ↓.
Using them screws up space between lines, maybe because the fonts do not have
the same parameters and are not serif. In any case, Web browsers are able to
pull missing chars from some more adequate fonts, so we are OK.

Also stopped using Noto Emoji, because it is really massive. People probably
already have an Emoji font somewhere on their computer. We could also pull
Noto Emoji from an official source to help with caching.
