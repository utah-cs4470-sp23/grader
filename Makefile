.PHONY: test-current test-hw1

CURRENT=hw1
PART=all
DIR=..

test-current: test-$(CURRENT)
count-current: count-$(CURRENT)

count-hw1:
	@ hw1/test-part $(DIR) count

test-hw1:
	sh hw1/test-part $(DIR) $(PART)
