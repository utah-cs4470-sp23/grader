.PHONY: test-current test-hw1

CURRENT=hw1
PART=all
DIR=..

test-current: test-$(CURRENT)
count-current: count-$(CURRENT)

count-hw1:
	echo 6

test-hw1:
	sh hw1/test-part $(DIR) $(PART)
