# Test makefile for the gif2png test images
#
IMAGESTEMS = 666666 ducks gtcd opus ten-wire

PATH := ..:.:${PATH}

test: gif2png-test web2png-test

# Run this to regression-test the converter
gif2png-test:
	for x in $(IMAGESTEMS); do echo "$${x}:"; ../gif2png -v $${x}.gif; cmp $${x}.png $${x}.png-check; done

# Run this as a visual check. The thing to do is 'Next' a couple times 
# on each pair to verify that the image and its conversion are visually 
# identical.
blink:
	for x in $(IMAGESTEMS); do display $${x}.gif $${x}.png-check; done

# Run this to make a set of check images with a known-good version
make-checkimages:
	for x in $(IMAGESTEMS); do mv $${x}.png $${x}.png-check; done

web2png-test:
	cp test.html-gif test.html
	cp links2.js-gif links2.js
	cp style.css-gif style.css
	../web2png .
	-diff -u test.html-gif test.html
	-diff -u links2.js-gif links2.js
	-diff -u style.css-gif style.css

clean: 
	rm -f *.png *.bak
