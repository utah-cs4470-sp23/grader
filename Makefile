.PHONY: test-current test-hw1 test-hw2 count-hw1 count-hw2 upgrade

CURRENT=hw14
PART=all
DIR=..

# Some ideas from https://gist.github.com/sighingnow/deee806603ec9274fd47
ifndef OS
	ifeq ($(OS),Windows_NT)
		OS ?= windows
	else
		UNAME_S := $(shell uname -s)
		ifeq ($(UNAME_S),Linux)
			GLIBC_SUBV := $(shell ldd --version | head -n1 | sed 's/.*2\.\([0-9]*\).*/\1/g')
			ifeq ($(shell test $(VER) -ge 35; echo $$?),0)
				OS ?= linux
			else
				OS ?= linux-old
			endif
		endif
		ifeq ($(UNAME_S),Darwin)
			OS ?= macos
		endif
	endif
endif

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

count-hw9:
	@ sh hw9/test-part $(DIR) count

count-hw10:
	@ sh hw10/test-part $(DIR) count

count-hw11:
	@ sh hw11/test-part $(DIR) count

count-hw12:
	@ sh hw12/test-part $(DIR) count

count-hw13:
	@ sh hw13/test-part $(DIR) count

count-hw14:
	@ sh hw14/test-part $(DIR) count

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

test-hw9:
	sh hw9/test-part $(DIR) $(PART)

test-hw10:
	sh hw10/test-part $(DIR) $(PART)

test-hw11:
	sh hw11/test-part $(DIR) $(PART)

test-hw12:
	sh hw12/test-part $(DIR) $(PART)

test-hw13:
	sh hw13/test-part $(DIR) $(PART)

test-hw14:
	sh hw14/test-part $(DIR) $(PART)

jplc:
	curl -L 'https://github.com/utah-cs4470-sp23/class/releases/latest/download/jplc-$(OS)' -o ./jplc
	chmod +x jplc

print-os:
	@ echo $(OS)

upgrade:
	git pull origin main
	$(MAKE) -B jplc OS=$(OS)
