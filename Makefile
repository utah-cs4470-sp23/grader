.PHONY: test-current test-hw1 test-hw2 count-hw1 count-hw2

CURRENT=hw2
PART=all
DIR=..

test-current: test-$(CURRENT)
count-current: count-$(CURRENT)

count-hw1:
	@ sh hw1/test-part $(DIR) count

count-hw2:
	@ sh hw2/test-part $(DIR) count

test-hw1:
	sh hw1/test-part $(DIR) $(PART)

test-hw2:
	sh hw2/test-part $(DIR) $(PART)
