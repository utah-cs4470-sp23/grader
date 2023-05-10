#!/usr/bin/env python3

from pathlib import Path
import tempfile
import subprocess
from dataclasses import dataclass
import traceback
import shlex
import difflib
import argparse
import sys
import normalize_asm
import time
import ppsexp

DIR="~/jpl/pavpan/"
TIMEOUT=60 # Seconds

class ParseSuccessError(Exception): pass
class StudentCompilerFailed(Exception): pass
class StudentCompilerTimeout(Exception): pass
class StudentCompilerInvalid(Exception): pass

class CorrectCompilerInvalid(Exception): pass

def parse_success(out):
    parts = out.strip().rsplit("\n", 1)
    if len(parts) > 1:
        main_body, last_line = parts
    else:
        main_body, last_line = "", parts[0]
    last_line = last_line.casefold()
    has_success = last_line.count("Compilation succeeded".casefold())
    has_failure = last_line.count("Compilation failed".casefold())
    if has_success and has_failure:
        raise ParseSuccessError("Found both 'Compilation succeeded' and 'Compilation failed'")
    elif has_success > 1:
        raise ParseSuccessError("Found 'Compilation succeeded' more than once")
    elif has_failure > 1:
        raise ParseSuccessError("Found 'Compilation failed' more than once")
    elif has_success == 0 and has_failure == 0:
        if "Compilation succeeded".casefold() in main_body.casefold():
            raise ParseSuccessError("'Compilation succeeded' message not last line of output")
        elif "Compilation failed".casefold() in main_body.casefold():
            raise ParseSuccessError("'Compilation failed' message not last line of output")
        else:
            raise ParseSuccessError("Could not find 'Compilation succeeded' or 'Compilation failed'")
    else:
        return has_success > has_failure, main_body

def run_student(flags, in_file):
    try:
        res = subprocess.run([
            "make",
            "--silent", # Don't print commands as they are run
            "--no-print-directory", # Don't print change directory message
            "-C", DIR,
            "run",
            "FLAGS=" + flags,
            "TEST=" + str(in_file.resolve()),
        ], capture_output=True, timeout=TIMEOUT, text=True)
    except subprocess.TimeoutExpired as e:
        raise StudentCompilerTimeout(e)
    except subprocess.CalledProcessError as e:
        raise StudentCompilerFailed(e)
    else:
        try:
            success, out = parse_success(res.stdout)
        except ParseSuccessError as e:
            raise StudentCompilerInvalid(str(e), res.stdout, res.stderr)
        return success, out

def run_compiler(flags, in_file):
    res = subprocess.run(["./jplc"] + shlex.split(flags) + [str(in_file.resolve())],
                         capture_output=True, timeout=TIMEOUT, text=True)
    try:
        success, out = parse_success(res.stdout)
    except ValueError as e:
        print(e)
        print(res.stdout)
        raise 
    return success, out
    
@dataclass
class FileSpec:
    in_file : Path
    flags : str

    def matches(self, name):
        return name == "all" or self.in_file.name.startswith(name)

    def index(self):
        idx = self.in_file.name
        if self.in_file.name.endswith(".jpl"):
            idx = self.in_file.name.removesuffix(".jpl")
        if idx.isdigit():
            idx = f"{idx:0>8}"
        return idx

@dataclass
class ValidSpec(FileSpec):
    def run(self):
        success, out = run_student(self.flags, self.in_file)
        if not success:
            raise StudentCompilerInvalid(f"File should have been accepted", out, None)
        
    def regen(self):
        pass

@dataclass
class InvalidSpec(FileSpec):
    def run(self):
        success, out = run_student(self.flags, self.in_file)
        if success:
            raise StudentCompilerInvalid(f"File should not have been accepted", out, None)
        
    def regen(self):
        pass

@dataclass
class DiffSpec(FileSpec):
    expected_file : Path
    normalize : None

    def __init__(self, in_file, flags, normalize=None):
        self.in_file = in_file
        self.flags = flags
        self.expected_file = in_file.parent / (in_file.name + ".expected")
        self.normalize = normalize

    def run(self):
        assert self.expected_file.exists(), \
            f"Expected output for {self.expected_file.name} not found"
        with self.expected_file.open() as f:
            expected = f.read()
        success, out = run_student(self.flags, self.in_file)
        if not success:
            raise StudentCompilerInvalid(f"File should have been accepted", out, None)
        expected = expected.strip().split("\n")
        out = out.strip().split("\n")
        if self.normalize:
            expected = list(self.normalize(expected))
            out = list(self.normalize(out))
            
        diff_lines = list(difflib.context_diff(
            expected, out, lineterm="",
            fromfile=self.expected_file.name, tofile="Your output"))
        if diff_lines:
            count = len([line for line in diff_lines if line.startswith("- ") or line.startswith("+ ") or line.startswith("! ")])
            raise StudentCompilerInvalid(f"{count} lines differ", "\n".join(diff_lines), None)

    def regen(self):
        success, out = run_compiler(self.flags, self.in_file)
        if not success:
            raise CorrectCompilerInvalid(f"File should have been accepted", out)
        with self.expected_file.open("wt") as f:
            f.write(out)

@dataclass
class RunSpec(FileSpec):
    def run(self):
        success, out = run_student(self.flags, self.in_file)
        msg = "was successful" if success else "failed"
        raise StudentCompilerInvalid(f"Compilation {msg}", out, None)

def print_fancy(name, out):
    if not out: return
    if isinstance(out, bytes): out = out.decode("latin1")
    print(f"======= {name}: =======")
    print(out)
    print()
    
def makespec(T, path, *args, **kwargs):
    for f in sorted(path.iterdir(), key=lambda f: f.name):
        if f.name.endswith(".jpl"):
            yield T(f, *args, **kwargs)
            
def regen_all(filespecs):
    failures = 0
    for filespec in filespecs:
        print(filespec.in_file.name, "...", flush=True, end=" ")
        try:
            filespec.regen()
        except CorrectCompilerInvalid as e:
            failures += 1
            print("error")
            print(str(e.args[0]))
            print(e.args[1])
            break
        except Exception:
            failures += 1
            print("error")
            raise
        else:
            print("done")
    return failures

def test_all(name, filespecs, grade=False, timeout=False):
    start_time = time.time()
    total = 0
    success = 0
    total_since = len(name) + 1
    filespecs = sorted(filespecs, key=FileSpec.index)
    outputs = []
    print(f"{name} ", end="", flush=True)
    for filespec in filespecs:
        total += 1
        total_since += 1
        try:
            filespec.run()
        except StudentCompilerTimeout as e:
            total_since = 0
            e = e.args[0]
            print("T")
            print(f"{filespec.in_file.name}: Timeout after {e.timeout} seconds")
            print_fancy("StdOut", e.stdout)
            print_fancy("StdErr", e.stderr)
            if not grade: sys.exit(1)
        except StudentCompilerFailed as e:
            total_since = 0
            print("F")
            e = e.args[0]
            print(f"{filespec.in_file.name}: Process returned bad error code {e.returncode}")
            print_fancy("StdOut", e.stdout)
            print_fancy("StdErr", e.stderr)
            if not grade: sys.exit(2)
        except StudentCompilerInvalid as e:
            total_since = 0
            print("W")
            msg, out, err = e.args
            print(f"{filespec.in_file.name}:", msg)
            print_fancy("StdOut", out)
            print_fancy("StdErr", err)
            if not grade: sys.exit(3)
        except Exception as e:
            total_since = 0
            print("X")
            print(f"{filespec.in_file.name}: The auto-grader encountered a fatal error")
            print("Please report this to the instructors")
            print("======= Traceback: =======")
            traceback.print_exc()
        else:
            print(".", end="", flush=True)
            success += 1
        if total_since > 71:
            total_since = 0
            print()
    print()
    if grade:
        print(f"Passed {success}/{total} = {success/total*100:.1f}% tests")
    return total - success
            
HERE = Path(__file__).parent.resolve()

CURRENT_HW = "3"

HWS = {
   "2": {
       "1": makespec(DiffSpec, HERE / "hw2/lexer-tests1/", "-l"),
       "2": makespec(ValidSpec, HERE / "hw2/lexer-tests2/", "-l"),
       "3": makespec(InvalidSpec, HERE / "hw2/lexer-tests3/", "-l"),
   },
   "3": {
       "1": makespec(DiffSpec, HERE / "hw3/ok/", "-p", normalize=ppsexp.ppsexp),
       "2": makespec(DiffSpec, HERE / "hw3/ok-fuzzer/", "-p", normalize=ppsexp.ppsexp),
       "3": makespec(InvalidSpec, HERE / "hw3/fail-fuzzer1/", "-p"),
       "4": makespec(InvalidSpec, HERE / "hw3/fail-fuzzer2/", "-p"),
       "5": makespec(InvalidSpec, HERE / "hw3/fail-fuzzer3/", "-p"),
   },
   "4": {
       "1": makespec(DiffSpec, HERE / "hw4/ok/", "-p", normalize=ppsexp.ppsexp),
       "2": makespec(DiffSpec, HERE / "hw4/ok-fuzzer/", "-p", normalize=ppsexp.ppsexp),
       "3": makespec(InvalidSpec, HERE / "hw4/fail-fuzzer1/", "-p"),
       "4": makespec(InvalidSpec, HERE / "hw4/fail-fuzzer2/", "-p"),
       "5": makespec(InvalidSpec, HERE / "hw4/fail-fuzzer3/", "-p"),
   },
   "5": {
       "1": makespec(DiffSpec, HERE / "hw5/ok/", "-p", normalize=ppsexp.ppsexp),
       "2": makespec(DiffSpec, HERE / "hw5/ok-fuzzer/", "-p", normalize=ppsexp.ppsexp),
       "3": makespec(InvalidSpec, HERE / "hw5/fail-fuzzer1/", "-p"),
       "4": makespec(InvalidSpec, HERE / "hw5/fail-fuzzer2/", "-p"),
       "5": makespec(InvalidSpec, HERE / "hw5/fail-fuzzer3/", "-p"),
   },
   "6": {
       "1": makespec(DiffSpec, HERE / "hw6/ok/", "-t", normalize=ppsexp.ppsexp),
       "2": makespec(DiffSpec, HERE / "hw6/ok-fuzzer/", "-t", normalize=ppsexp.ppsexp),
       "3": makespec(InvalidSpec, HERE / "hw6/fail-fuzzer1/", "-t"),
       "4": makespec(InvalidSpec, HERE / "hw6/fail-fuzzer2/", "-t"),
       "5": makespec(InvalidSpec, HERE / "hw6/fail-fuzzer3/", "-t"),
   },
   "7": {
       "1": makespec(DiffSpec, HERE / "hw7/ok/", "-t", normalize=ppsexp.ppsexp),
       "2": makespec(InvalidSpec, HERE / "hw7/fail/", "-t"),
       "3": makespec(DiffSpec, HERE / "hw7/ok-fuzzer/", "-t", normalize=ppsexp.ppsexp),
       "4": makespec(InvalidSpec, HERE / "hw7/fail-fuzzer/", "-t"),
   },
   "8": {
       "1": makespec(DiffSpec, HERE / "hw8/ok/", "-t", normalize=ppsexp.ppsexp),
       "2": makespec(InvalidSpec, HERE / "hw8/fail/", "-t"),
       "3": makespec(DiffSpec, HERE / "hw8/ok-fuzzer/", "-t", normalize=ppsexp.ppsexp),
       "4": makespec(InvalidSpec, HERE / "hw8/fail-fuzzer/", "-t"),
   },
   "9": {
       "1": makespec(DiffSpec, HERE / "hw9/ok1/", "-s", normalize=normalize_asm.normalize),
       "2": makespec(DiffSpec, HERE / "hw9/ok2/", "-s", normalize=normalize_asm.normalize),
       "3": makespec(DiffSpec, HERE / "hw9/ok3/", "-s", normalize=normalize_asm.normalize),
       "4": makespec(DiffSpec, HERE / "hw9/ok-fuzzer/", "-s", normalize=normalize_asm.normalize),
   },
   "10": {
       "1": makespec(DiffSpec, HERE / "hw10/ok1/", "-s", normalize=normalize_asm.normalize),
       "2": makespec(DiffSpec, HERE / "hw10/ok2/", "-s", normalize=normalize_asm.normalize),
       "3": makespec(DiffSpec, HERE / "hw10/ok3/", "-s", normalize=normalize_asm.normalize),
       "4": makespec(DiffSpec, HERE / "hw10/ok4/", "-s", normalize=normalize_asm.normalize),
       "5": makespec(DiffSpec, HERE / "hw10/ok-fuzzer/", "-s", normalize=normalize_asm.normalize),
       "ec": makespec(DiffSpec, HERE / "hw10/extra-fuzzer/", "-s", normalize=normalize_asm.normalize),
   },
   "11": {
       "1": makespec(DiffSpec, HERE / "hw11/ok1/", "-s", normalize=normalize_asm.normalize),
       "2": makespec(DiffSpec, HERE / "hw11/ok2/", "-s", normalize=normalize_asm.normalize),
       "3": makespec(DiffSpec, HERE / "hw11/ok3/", "-s", normalize=normalize_asm.normalize),
       "4": makespec(DiffSpec, HERE / "hw11/ok4/", "-s", normalize=normalize_asm.normalize),
       "5": makespec(DiffSpec, HERE / "hw11/ok-fuzzer/", "-s", normalize=normalize_asm.normalize),
       "ec": makespec(DiffSpec, HERE / "hw11/extra/", "-s", normalize=normalize_asm.normalize),
   },
}

def main(args):
    if args.tool not in ["grade", "test", "count", "regen", "run"]:
        raise ValueError(f"Unknown tool {args.tool}; only have these:\n" + \
                         "  grade, test, count, regen, run")
    failures = 0
    if args.hw == "all":
        homeworks = HWS
    elif args.hw == "current":
        homeworks = { CURRENT_HW: HWS[CURRENT_HW] }
    elif args.hw in HWS:
        homeworks = { args.hw: HWS[args.hw] }
    else:
        raise ValueError(f"Unknown homework number {args.hw}; only have these:\n" + \
                         "  " + ", ".join(HWS.keys()))
    if args.tool == "count" and len(homeworks) > 1:
        raise ValueError("Cannot 'count' more than one homework at a time")
    for hwname, homework in homeworks.items():
        if args.part == "all":
            parts = homework
        elif args.part in homework:
            parts = { args.part: homework[args.part] }
        else:
            raise ValueError(f"Unknown part number {args.part}; hw{hwname} only has:\n" + \
                             "  " + ", ".join(homework.keys()))

        if args.tool == "count":
            cnt = len([k for k in parts.keys() if k.isdigit()])
            print(cnt)
            return
        for partname, part in parts.items():
            tests = [test for test in part if test.matches(args.test)]
            if not tests:
                raise ValueError(f"Unknown test number {args.test} in hw{hwname} part {partname}")

            name = f"Homework {hwname} part {partname}"
            if args.tool == "grade":
                failures += test_all(name, tests, grade=True)
            elif args.tool == "test":
                failures += test_all(name, tests)
            elif args.tool == "regen":
                failures += regen_all(tests)
            elif args.tool == "run":
                failures += test_all(name, [RunSpec(test.in_file, test.flags) for test in tests])
    sys.exit(failures)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test and grade CS 4470 assignments")
    parser.add_argument("tool", type=str,
                        help="What to do: grade, test, count, regen")
    parser.add_argument("--hw", type=str, default="current",
                        help="Which homework assignment to test")
    parser.add_argument("--part", type=str, default="all",
                        help="Which phase assignment to test")
    parser.add_argument("--test", type=str, default="all",
                        help="Which specific test to run")
    args = parser.parse_args()
    try:
        main(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(2)
    except KeyboardInterrupt:
        print("interrupted")
        sys.exit(1)
