for f in texts/DHARMA_INS*; do
	out="texts.hid/$(basename $f)"
	if test -s "texts.hid/$(basename $f)"; then
		continue
	fi
	if python patch.py "$f" > tmp_internal.hid; then
		xmllint --format --encode utf8 tmp_internal.hid > $out
	else
		echo $f
	fi
done
