#!/usr/bin/env python3

from typing import Optional, Tuple
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
import concurrent.futures as futures

DIR="~/jpl/pavpan/"
TIMEOUT=60 # Seconds

class ParseSuccessError(Exception): pass
class CompilerFailed(Exception): pass
class CompilerTimeout(Exception): pass
class CompilerInvalid(Exception): pass

def parse_success(out : str) -> Tuple[bool, str]:
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

def run_student(flags, in_file, require=None):
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
        raise CompilerTimeout(e)
    except subprocess.CalledProcessError as e:
        raise CompilerFailed(e)
    else:
        try:
            success, out = parse_success(res.stdout)
        except ParseSuccessError as e:
            raise CompilerInvalid(str(e), res.stdout, res.stderr)
        if require is not None and success != require:
            raise CompilerInvalid(f"File should {' ' if require else 'not '}have been accepted", out, res.stderr)
        return success, out, res.stderr

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

    def run(self):
        raise NotImplementedError

    def regen(self):
        raise NotImplementedError

@dataclass
class ValidSpec(FileSpec):
    def run(self):
        success, out, err = run_student(self.flags, self.in_file, require=True)
        
    def regen(self):
        pass

@dataclass
class InvalidSpec(FileSpec):
    def run(self):
        success, out, err = run_student(self.flags, self.in_file, require=False)
        
    def regen(self):
        pass

def diff(fromtext, totext, fromfile=None, tofile=None):
    diff_lines = list(difflib.context_diff(
        fromtext, totext, lineterm="", fromfile=fromfile, tofile=tofile))
    if diff_lines:
        count = len([line for line in diff_lines if line.startswith("- ") or line.startswith("+ ") or line.startswith("! ")])
        raise CompilerInvalid(f"{count} lines differ", "\n".join(diff_lines), None)

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
        success, out, err = run_student(self.flags, self.in_file, require=True)
        expected = expected.strip().split("\n")
        out = out.strip().split("\n")
        if self.normalize:
            expected = list(self.normalize(expected))
            out = list(self.normalize(out))
        diff(expected, out, fromfile=self.expected_file.name, tofile="Your compiler")

    def regen(self):
        success, out = run_compiler(self.flags, self.in_file)
        if not success:
            raise CompilerInvalid(f"File should have been accepted", out)
        with self.expected_file.open("wt") as f:
            f.write(out)

@dataclass
class OptSpec(FileSpec):
    expected_O0 : Path
    expected_O1 : Path

    def __init__(self, in_file, flags):
        self.in_file = in_file
        self.flags = flags
        self.expected_O0 = in_file.parent / (in_file.name + ".expected")
        self.expected_O1 = in_file.parent / (in_file.name + ".expected.opt")

    def run(self):
        assert self.expected_O0.exists(), \
            f"Expected output for {self.expected_O0.name} not found"
        with self.expected_O0.open() as f:
            expected = f.read()
        success, out, err = run_student("-s", self.in_file, require=True)
        expected = list(normalize_asm.normalize(expected.strip().split("\n")))
        out = list(normalize_asm.normalize(out.strip().split("\n")))
        diff(expected, out, fromfile=self.expected_O0.name, tofile="Your compiler")

        assert self.expected_O1.exists(), \
            f"Expected output for {self.expected_O1.name} not found"
        with self.expected_O1.open() as f:
            expected = f.read()
        success, out, err = run_student(f"-s {self.flags}", self.in_file, err, require=True)
        expected = list(normalize_asm.normalize(expected.strip().split("\n")))
        out = list(normalize_asm.normalize(out.strip().split("\n")))
        diff(expected, out, fromfile=self.expected_O1.name, tofile="Your compiler")

    def regen(self):
        success, out = run_compiler("-s", self.in_file)
        if not success:
            raise CompilerInvalid(f"File should have been accepted", out)
        with self.expected_O0.open("wt") as f:
            f.write(out)
        success, out = run_compiler(f"-s {self.flags}", self.in_file)
        if not success:
            raise CompilerInvalid(f"File should have been accepted", out)
        with self.expected_O1.open("wt") as f:
            f.write(out)

@dataclass
class RunSpec(FileSpec):
    def run(self):
        success, out, err = run_student(self.flags, self.in_file)
        msg = "was successful" if success else "failed"
        raise CompilerInvalid(f"Compilation {msg}", out, err)

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
        except CompilerInvalid as e:
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

def test_one(filespec : FileSpec) -> Tuple[str, str, Optional[str], Optional[str]]:
    try:
        filespec.run()
    except CompilerTimeout as e:
        e = e.args[0]
        msg = f"{filespec.in_file.name}: Timeout after {e.timeout} seconds"
        return "T", msg, e.stdout, e.stderr
    except CompilerFailed as e:
        e = e.args[0]
        msg = f"{filespec.in_file.name}: Process returned bad error code {e.returncode}"
        return "F", msg, e.stdout, e.stderr
    except CompilerInvalid as e:
        msg, out, err = e.args
        msg = f"{filespec.in_file.name}: {msg}"
        return "W", msg, out, err
    else:
        return ".", "", None, None

def test_all(name, filespecs, grade=False, threads=None):
    start_time = time.time()
    total = 0
    failure = 0
    total_since = len(name) + 1
    filespecs = sorted(filespecs, key=FileSpec.index)
    outputs = []
    print(f"{name} ", end="", flush=True)
    if threads is None:
        domap = map
    else:
        pool = futures.ThreadPoolExecutor(max_workers=threads)
        domap = pool.map
    for status, msg, out, err in domap(test_one, filespecs):
        total += 1
        total_since += 1
        print(status, end="", flush=True)
        if status != ".":
            print()
            print(msg)
            print_fancy("Standard Out", out)
            print_fancy("Standard Error", err)
            total_since = 0
            failure += 1
            if not grade: sys.exit(1)
        if total_since > 71:
            total_since = 0
            print()
    print()
    if grade:
        print(f"Passed {total - failure}/{total} = {(1 - failure/total)*100:.1f}% tests")
    if threads:
        pool.shutdown()
    return failure
            
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
   "12": {
       "1": makespec(OptSpec, HERE / "hw12/ok1/", "-O1"),
       "2": makespec(OptSpec, HERE / "hw12/ok2/", "-O1"),
       "3": makespec(OptSpec, HERE / "hw12/ok3/", "-O1"),
       "4": makespec(OptSpec, HERE / "hw12/ok4/", "-O1"),
       "5": makespec(OptSpec, HERE / "hw12/ok5/", "-O1"),
   },
   "13": {
       "1": makespec(OptSpec, HERE / "hw13/ok1/", "-O2"),
       "2": makespec(OptSpec, HERE / "hw13/ok2/", "-O2"),
       "3": makespec(OptSpec, HERE / "hw13/ok-fuzzer/", "-O2"),
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
                failures += test_all(name, tests, grade=True, threads=args.threads)
            elif args.tool == "test":
                failures += test_all(name, tests, threads=args.threads)
            elif args.tool == "regen":
                failures += regen_all(tests)
            elif args.tool == "run":
                failures += test_all(name, [RunSpec(test.in_file, test.flags) for test in tests], threads=args.threads, grade=True)
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
    parser.add_argument("--threads", type=int, default=None,
                        help="When passed, run the compiler in parallel for more speed")
    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        print("interrupted")
        sys.exit(1)
    except Exception as e:
        total_since = 0
        print("X")
        print(f"The auto-grader encountered a fatal error")
        print("Please report this to the instructors")
        print("======= Traceback: =======")
        traceback.print_exc()
        sys.exit(127)
