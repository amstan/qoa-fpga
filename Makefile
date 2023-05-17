QOA = qoa-reference

qoa-reference/sokol_audio.h:
	wget https://raw.githubusercontent.com/floooh/sokol/master/sokol_audio.h -O $@
qoa-reference/dr_flac.h:
	wget https://raw.githubusercontent.com/mackron/dr_libs/master/dr_flac.h -O $@
qoa-reference/dr_mp3.h:
	wget https://raw.githubusercontent.com/mackron/dr_libs/master/dr_mp3.h -O $@

qoa-reference/qoaconv: qoa-reference/dr_flac.h qoa-reference/dr_mp3.h qoa-reference/
	cd qoa-reference; make qoaconv

qoa-reference/qoaplay: qoa-reference/sokol_audio.h qoa-reference/
	cd qoa-reference; make qoaplay

all_reference_tools: qoa-reference/qoaconv qoa-reference/qoaplay

clean_reference_tools:
	cd qoa-reference; git clean -x -f

clean: clean_reference_tools
	rm -Rf build/*
