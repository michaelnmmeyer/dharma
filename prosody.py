import os, sys, unicodedata, json, logging
from dharma import config, tree, biblio, people, texts

def load_data():
	f = texts.save("project-documentation", "DHARMA_prosodicPatterns_v01.xml")
	xml = tree.parse(f)
	items = {}
	for item in xml.find("//item"):
		pros = [node for node in item.find(".//seg") if node["type"] == "prosody"]
		if len(pros) != 1:
			logging.error("several prosodic entries in the same entry")
			continue
		pros = pros[0]
		names = set()
		for name in item.find("name") + item.find("label"):
			name = name.text()
			if not name:
				continue
			name = unicodedata.normalize("NFC", name)
			names.add(name)
		for name in names:
			if name in items:
				print(f"duplicate meter: {name}", file=sys.stderr)
				continue
			items[name] = pros.text()
	return items

def make_db():
	data = load_data()
	db = config.db("texts")
	db.execute("delete from prosody")
	for name, pattern in sorted(data.items()):
		db.execute("insert into prosody(name, pattern) values(?, ?)",
			(name, pattern))

# TODO use Symbola for fonts symbol
pattern_tbl = str.maketrans({
	"-": "\N{metrical breve}",
	"+": "\N{en dash}",
	"=": "\N{metrical short over long}",
	"2": "\N{metrical two shorts over long}",
})
def render_pattern(p):
	return "\N{narrow no-break space}".join(p.translate(pattern_tbl))

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
	if not target.startswith("bib:"):
		return None, None
	if target == "bib:AuthorYear_01":
		return None, None
	ref = target.removeprefix("bib:")
	loc = []
	for r in node.find("citedRange"):
		unit = r["unit"]
		if not unit or unit not in bibl_units:
			unit = "page"
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

def parse_list_rec(item, bib_entries):
	rec = {
		"syllables": None,
		"class": None,
		"names": [],
		"xml": None,
		"prosody": None,
		"gana": None,
		"notes": [],
		"bibliography": [],
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
		lang = klass["lang"] or "und"
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
		lang = name["lang"] or "und"
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
	for bibl in item.find("listBibl/bibl"):
		ref, loc = extract_bib_ref(bibl)
		if not ref:
			continue
		entry = bib_entries.get(ref)
		if not entry:
			entry = biblio.Entry(ref)
			bib_entries[ref] = entry
		rec["bibliography"].append({
			"ref": entry.reference(loc=loc),
			"notes": fetch_notes(bibl),
		})
	return rec

def parse_list(list):
	heading = list.first("head").text()
	items = []
	bib_entries = {}
	for item in list.find("item"):
		items.append(parse_list_rec(item, bib_entries))
	return {
		"heading": heading,
		"items": items,
	}

def parse_prosody():
	db = config.db("texts")
	f = db.load_file("DHARMA_prosodicPatterns_v01")
	xml = tree.parse(f)
	ret = {
		"notation": parse_front(xml),
		"lists": [],
	}
	for list in xml.find("//body/list"):
		ret["lists"].append(parse_list(list))
	return ret

def find_mismatching_xml_prosody():
	path = config.path_of("repos/project-documentation/DHARMA_prosodicPatterns_v01.xml")
	xml = tree.parse(path)
	for item in xml.find("//item"):
		x = item.first("seg[@type='xml']")
		p = item.first("seg[@type='prosody']")
		if x and p:
			tr = render_pattern(x.text()).replace("\N{narrow no-break space}", "")
			if tr != p.text():
				print(item.first("name").text() or item.first("label").text())
				print("  " + x.text())
				print("  " + p.text())
				print("")

if __name__ == "__main__":
	@config.transaction("texts")
	def main():
		print(config.to_json(parse_prosody()))
	main()
