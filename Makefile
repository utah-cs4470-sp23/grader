.PHONY: test-current test-hw1 test-hw2 count-hw1 count-hw2

CURRENT=hw6
PART=all
DIR=..

OS=linux

test-current: test-$(CURRENT)
count-current: count-$(CURRENT)

count-hw1:
	@ sh hw1/test-part $(DIR) count

count-hw2:
	@ sh hw2/test-part $(DIR) count

count-hw3:
	@ sh hw3/test-part $(DIR) count

count-hw4:
	@ sh hw4/test-part $(DIR) count

count-hw5:
	@ sh hw5/test-part $(DIR) count

count-hw6:
	@ sh hw6/test-part $(DIR) count

count-hw7:
	@ sh hw7/test-part $(DIR) count

count-hw8:
	@ sh hw8/test-part $(DIR) count

test-hw1: jplc
	sh hw1/test-part $(DIR) $(PART)

test-hw2:
	sh hw2/test-part $(DIR) $(PART)

test-hw3: jplc
	sh hw3/test-part $(DIR) $(PART)

test-hw4: jplc
	sh hw4/test-part $(DIR) $(PART)

test-hw5: jplc
	sh hw5/test-part $(DIR) $(PART)

test-hw6: jplc
	sh hw6/test-part $(DIR) $(PART)

test-hw7: jplc
	sh hw7/test-part $(DIR) $(PART)

test-hw8: jplc
	sh hw8/test-part $(DIR) $(PART)

jplc:
	curl -L 'https://github.com/utah-cs4470-sp23/class/releases/latest/download/jplc-$(OS)' -o ./jplc
	chmod +x jplc

pp-gh:
	curl -L 'https://github.com/utah-cs4470-sp23/class/releases/latest/download/pp-gh' -o ./pp-gh
	chmod +x pp-gh
