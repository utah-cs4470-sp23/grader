CS 4470 Compilers Auto-grader
=============================

This repository contains the auto-grader for CS 4470 Compilers. The
code inside will automatically run any time you push to your
repository, via Github Actions. You can also download this repository
to your own computer, and run it there.

Structure of the auto-grader
----------------------------

The auto-grader contains one folder for each homework assignment,
named `hw1`, `hw2`, and so on. Each folder contains scripts as well as
test files and directories.

Each homework assignment consists of multiple *parts*---between 1 and
6 of them. Each part is graded separately and has a separate weight
given in each assignment description. They are run separately. A part
typically consists of a number of individual tests (usually about a
hundred, though it varies). Your score for each part is typically the
number of tests passed.

Keep your auto-grader up to date. In certain cases the instructors
will fix bugs, add or remove tests, or make other changes to the
auto-grader. If you are using an out-of-date auto-grader, you may
waste time fixing bugs or implementing features that you are not
supposed to handle.

Only runs of the auto-grader on Github matter for your score. If it
works on your machine but not on Github, you will not receive credit.
Push to Github early and often to maintain an understanding of your
progress through the assignment.

Running the auto-grader
-----------------------

To run the auto-grader, you will need to check out both the grader
repository and your compiler repository and know the absolute path to
both.

Additionally, you will need a number of dependencies installed on your
machine, including at least a Unix shell (only Dash and Bash tested),
Make (only GNU Make tested), standard Unix tools like `grep` and `sed`
(only GNU versions tested), GCC or compatible compiler (only GCC
tested), NASM or compatible assembler (only NASM tested), and, for the
first assignment, the Imagemagick tools.

Run the auto-grader like so:

    make -C /autograder/repo test-current DIR=/compiler/repo PART=X

Here both paths **must be absolute paths**.
    
Here the `X` is `PART=X` is a number from 1 to however many parts your
assignment has. If you are unsure, check the assignment description.

The `test-current` rule runs the current homework, as of whenever you
last pulled from the grader repository. Additionally, you can run a
specific homework assignment like so:

    make -C /autograder/repo test-hw3 DIR=/compiler/repo PART=X

Here you can choose any (released) homework assignment instead of
`hw3`.

If you see any unexpected error messages, contact the instructors.

Troubleshooting
---------------

On Linux, you might get an error about the required GLIBC version. You
may be able to fix it by running this command:

    make -C /autograder/repo -B jplc OS=linux-old
    
This downloads a special version of the JPL compiler made for older
(2018-era) Linux distributions.
