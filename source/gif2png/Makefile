# Makefile for gif2png

VERSION = $(shell sed -n <NEWS '/::/s/^\([^:]*\).*/\1/p' | head -1)

TAR = tar

CFLAGS += -DVERSION=\"$(VERSION)\"

SOURCES = 437_l1.c gif2png.c gifread.c memory.c version.c
OBJECTS = $(SOURCES:.c=.o)

all: gif2png gif2png.1 web2png.1

gif2png: $(OBJECTS) 
	$(CC) $(CFLAGS) $(OBJECTS) -lpng -lz -lm $(LDFLAGS) -o gif2png

437_l1.o: 437_l1.c
gif2png.o: gif2png.c gif2png.h
gifread.o: gifread.c gif2png.h
memory.o: memory.c gif2png.h
version.o: version.c

gif2png.1: gif2png.xml
	xmlto man gif2png.xml

gif2png.html: gif2png.xml
	xmlto html-nochunks gif2png.xml

web2png.1: web2png.xml
	xmlto man web2png.xml

check:
	cd test; make --quiet test

clean:
	rm -f gif2png *.o gif2png.1 web2png.1

version:
	@echo $(VERSION)

prefix ?= /usr
bindir ?= $(prefix)/bin
mandir ?= $(prefix)/share/man

install: gif2png gif2png.1 web2png.1
	mkdir -p $(DESTDIR)$(bindir)
	mkdir -p $(DESTDIR)$(mandir)/man1
	cp gif2png web2png $(DESTDIR)$(bindir)/
	cp gif2png.1 web2png.1 $(DESTDIR)$(mandir)/man1/

uninstall:
	rm $(bindir)/gif2png $(bindir)/web2png
	rm $(mandir)/man1/gif2png.1 $(mandir)/man1/web2png.1

PYLINTOPTS = --rcfile=/dev/null --reports=n \
	--msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
	--dummy-variables-rgx='^_'
SUPPRESSIONS = \
	--disable=C0111,C0103,C0301,C0321,C0326,W0402,W0110,W0141,W0401,W0614,R0912,R0914,R0915
pylint:
	@pylint $(PYLINTOPTS) $(SUPPRESSIONS) web2png

CHECK_OPTS = -UPNG_LIBPNG_VER_STRING -UZLIB_VERSION
cppcheck:
	cppcheck $(CHECK_OPTS) --template gcc --enable=all $(SOURCES)

SPLINTOPTS = -warnposix +charint -exitarg -compdestroy -exportlocal
splint:
	splint +quiet $(SPLINTOPTS) $(SOURCES)

EXTRA_DIST = README NEWS COPYING INSTALL control Makefile web2png \
	gif2png.xml web2png.xml gif2png.1 web2png.1 gif2png-logo.png test
DISTFILES = $(SOURCES) gif2png.h $(EXTRA_DIST)

gif2png-$(VERSION).tar.gz: $(DISTFILES)
	$(TAR) --transform='s:^:gif2png-$(VERSION)/:' --show-transformed-names -czf gif2png-$(VERSION).tar.gz $(DISTFILES)

dist: gif2png-$(VERSION).tar.gz

release: gif2png-$(VERSION).tar.gz gif2png.html
	shipper version=$(VERSION) | sh -e -x

refresh: gif2png.html
	shipper -N -w version=$(VERSION) | sh -e -x
