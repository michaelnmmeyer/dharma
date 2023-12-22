# Use of `<citedRange>` in `<bibl>`

For `<citedRange>`, we have two conflicting rules:

* `@unit` need not be given for page ranges, as in
  `<citedRange>36-42</citedRange>'
* complex locations should be encoded without a `@unit`, as in `<citedRange>p. 291 nn. 9, 10; p. 320</citedRange>`

We can probably assume that something like `82, 87-90, 93, 100-105` always
represents a page range, but then there are a lot of `<citedRange>` without a
unit that look like this:

	199 n. 4
	CVIII
	no. Ghan 1
	258-9 (III)
	1938-39: 71, no. B.452
	2, caption of fig. 3
	3, 15, 24-25 (H)
	3, 4 n. 1 and 7
	109 (no. 13B), 122 (no. 18A), 124 (no. 21), 128 (no. 26)
	2004-05: 206 (7)
	58-61, ills. 126-36
	[...]

Assuming that anything that starts with a digit is a page range would still be
OK in most cases, but it would be preferable to follow a convention that removes
the ambiguity.

Likewise, it is impossible to tell unambiguously whether the contents of
`<citedRange>` represents a single item (page, volume, etc.) --- in which case
the singular form of the unit should be used (p., vol., etc.) --- or several
items --- in which case the plural form is needed (pp., vols., etc.). It is
reasonably clear for cases like `82, 87-90, 93, 100-105` (only digits, hyphens
and commas), but beyond that I cannot do much. We have references like:

	B/1965-1966
	E.42-E.45
	IR 91
	1077, note 7
	110 (no. 13D) = 127 (no. 24)

As a reminder, here is how each value of `@unit` is displayed:

	@type     singular  plural
	---       ---       ---
	volume    vol.      vols.
	appendix  appendix  appendixes
	book      book      books
	section   §         §§
	page      p.        pp.
	item      №         №
	figure    fig.      figs.
	plate     plate     plates
	table     table     tables
	note      n.        nn.
	part      part      parts
	entry     s.v.      s.vv.
	line      l.        ll.
