import html, re
from dharma import common, tree, biblio, people, texts, langs

lang_attr = langs.lang_attr

def make_db():
	texts.save("project-documentation", "DHARMA_prosodicPatterns_v01.xml")
	_, index = parse_prosody()
	db = common.db("texts")
	db.execute("delete from prosody")
	for row in index:
		db.execute("""
			insert into prosody(name, pattern, description, entry_id)
			values(:name, :pattern, :description, :entry_id)""", row)

# TODO use Symbola for fonts symbol; no, is proprietary, find sth else
pattern_tbl = str.maketrans({
	"-": "\N{metrical breve}",
	"+": "\N{en dash}",
	"=": "\N{metrical short over long}",
	"2": "\N{metrical two shorts over long}",
	"\N{devanagari danda}": "|",
	"\N{devanagari double danda}": "||",
})
def render_pattern(p):
	buf = []
	for seg in re.findall(r"(?:\|\|)|(?:[0-9]{2,})|(?:.)", p):
		if len(seg) > 1:
			if not seg.isdigit():
				seg = seg.translate(pattern_tbl)
			# .prosody-segment is for letter-spacing. We keep
			# together groups of digits and double daṇḍas, otherwise
			# we add a bit a space.
			buf.append(f'<span class="prosody-segment">{seg[:-1]}</span>')
			buf.append(seg[-1])
		else:
			seg = seg.translate(pattern_tbl)
			buf.append(html.escape(seg))
	p = "".join(buf)
	return f'<span class="prosody">{p}</span>'

def is_pattern(p):
	return all(ord(c) in pattern_tbl or c.isdigit() or c in "|/" for c in p)

def parse_front(xml):
	table = xml.first("//front//table")
	heading = table.first("head").text()
	rows = []
	for row in table.find("row[not @role='label']"):
		cells = row.find("cell")
		assert len(cells) == 3
		description, xml_notation, prosody = [c.text() for c in cells]
		if not prosody:
			prosody = xml_notation
		rows.append((description, xml_notation, prosody))
	return {
		"heading": heading,
		"items": rows,
	}

bibl_units = set(biblio.cited_range_units)

def extract_bib_ref(node):
	assert node.name == "bibl"
	ptr = node.first("ptr")
	if not ptr:
		return None, None
	target = ptr["target"]
	if target == "bib:AuthorYear_01":
		return None, None
	ref = target.removeprefix("bib:")
	loc = []
	for r in node.find("citedRange"):
		unit = r["unit"] or "page"
		if unit not in bibl_units:
			unit = "mixed"
		val = r.text()
		if not val:
			continue
		loc.append((unit, val))
	return ref, loc

def fetch_notes(item):
	# <note resp="part:zapa">The name of this meter in CK is "kusumitagandha", while in Vr̥t is "kusumitajanma".</note>
	notes = []
	for note in item.find("note"):
		text = note.text()
		if not text:
			continue
		resps = []
		for resp in note["resp"].split():
			resp = resp.removeprefix("part:")
			if not resp:
				continue
			name = people.plain(resp) or people.plain("jodo")
			resps.append((resp, name))
		notes.append({"authors": resps, "text": text})
	return notes

latex_note_symbols = ("*", "†", "‡", "§", "¶", "‖", "**", "††", "‡‡")

def get_lang(cache, code):
	ret = cache.get(code)
	if not ret:
		ret = langs.Language(code)
		cache[ret.id] = ret
	return ret

def parse_list_rec(item, bib_entries, langs):
	rec = {
		"syllables": None,
		"class": None,
		"names": [],
		"xml": None,
		"prosody": None,
		"gana": None,
		"notes": [],
		"bibliography": {
			"refs": [],
			"notes": [],
		},
	}
	# <measure unit="syllable">22</measure>
	measure = item.find("measure")
	assert len(measure) <= 1
	if measure:
		measure = measure[0]
		assert measure["unit"] == "syllable"
		measure = measure.text()
		if measure:
			rec["syllables"] = measure
	# <label type="generic" xml:lang="san-Latn">vikr̥ti</label>
	klass = item.find("label[@type='generic']")
	assert len(klass) <= 1
	if klass:
		klass = klass[0]
		lang = get_lang(langs, lang_attr(klass) or "und")
		klass = klass.text()
		if klass:
			rec["class"] = (klass, lang)
	rec["notes"] = fetch_notes(item)
	# <name xml:lang="san-Latn">campakamālā</name>
	names = item.find("name")
	for name in names:
		text = name.text()
		if not text:
			continue
		lang = get_lang(langs, lang_attr(name) or "und")
		rec["names"].append((text, lang))
	# <seg type="xml">----+-+---+-+---=/++++-+-+---+-+---=</seg>
	# <seg type="prosody">⏑⏑⏑⏑–⏑–⏑⏑⏑–⏑||–⏑⏑⏑⏓/––––⏑–⏑–⏑⏑⏑–⏑–⏑⏑⏑⏓</seg>
	# <seg type="gana">na-ja-bha-ja-bha-la-ga/ma-ra-ja-sa-ja-sa</seg>
	for type in ("xml", "prosody", "gana"):
		seg = item.first(f"seg[@type='{type}']")
		if not seg:
			continue
		seg = seg.text()
		if not seg or seg == "no data available":
			continue
		if type == "prosody":
			seg = render_pattern(seg)
		rec[type] = seg
	symbols = iter(latex_note_symbols)
	for bibl in item.find("listBibl/bibl"):
		ref, loc = extract_bib_ref(bibl)
		if not ref:
			continue
		entry = bib_entries.get(ref)
		if not entry:
			entry = biblio.Entry(ref)
			bib_entries[ref] = entry
		syms = ""
		for note in fetch_notes(bibl):
			symbol = next(symbols)
			note["symbol"] = symbol
			syms += symbol
			rec["bibliography"]["notes"].append(note)
		ref = f'{entry.reference(loc=loc)}<sup>{syms}</sup>'
		rec["bibliography"]["refs"].append(ref)
	return rec

def parse_list(list, langs):
	heading = list.first("head").text()
	items = []
	bib_entries = {}
	for item in list.find("item"):
		items.append(parse_list_rec(item, bib_entries, langs))
	return {
		"heading": heading,
		"items": items,
	}

def make_name_index(lists):
	item_id = 0
	index = [] # might contain duplicates
	for list in lists:
		for item in list["items"]:
			item_id += 1
			item["id"] = item_id
			pattern = description = None
			if item["prosody"]:
				pattern = item["prosody"]
			elif item["xml"]:
				pattern = f'<span class="xml">{html.escape(item["xml"])}</span>'
			elif item["gana"]:
				pattern = html.escape(item["gana"])
			if not pattern and item["notes"]:
				description = html.escape(item["notes"][0]["text"])
			if item["class"]:
				index.append({
					"name": item["class"][0],
					"entry_id": item_id,
					"pattern": pattern,
					"description": description,
				})
			for name in item["names"]:
				index.append({
					"name": name[0],
					"entry_id": item_id,
					"pattern": pattern,
					"description": description,
				})
	return index

def parse_prosody():
	db = common.db("texts")
	f = db.load_file("DHARMA_prosodicPatterns_v01")
	xml = tree.parse(f)
	ret = {
		"notation": parse_front(xml),
		"lists": [],
	}
	langs = {}
	for list in xml.find("//body/list"):
		ret["lists"].append(parse_list(list, langs))
	index = make_name_index(ret["lists"])
	return ret, index

if __name__ == "__main__":
	@common.transaction("texts")
	def main():
		print(common.to_json(parse_prosody()))
	main()
