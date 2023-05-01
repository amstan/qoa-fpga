qoa/sokol_audio.h:
	wget https://raw.githubusercontent.com/floooh/sokol/master/sokol_audio.h -O $@
qoa/dr_flac.h:
	wget https://raw.githubusercontent.com/mackron/dr_libs/master/dr_flac.h -O $@
qoa/dr_mp3.h:
	wget https://raw.githubusercontent.com/mackron/dr_libs/master/dr_mp3.h -O $@

qoa/qoaconv: qoa/dr_flac.h qoa/dr_mp3.h qoa/
	cd qoa; make qoaconv

qoa/qoaplay: qoa/sokol_audio.h qoa/
	cd qoa; make qoaplay

all_reference_tools: qoa/qoaconv qoa/qoaplay

clean_reference_tools:
	cd qoa; git clean -x -f

clean:
	rm -Rf build/*
