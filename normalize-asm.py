#!/usr/bin/env python3
import re
MATH_RE = re.compile(r"([-+])\s*(\d)+\s*([-+])\s*(\d)+")

def domath(m):
    op1, lhs, op2, rhs = m.group(1, 2, 3, 4)
    v1 = -int(lhs) if op1 == "-" else int(lhs)
    v2 = -int(rhs) if op2 == "-" else int(rhs)
    v = v1 + v2
    if v < 0:
        return "- " + str(abs(v))
    elif v == 0:
        return ""
    elif v > 0:
        return "- " + str(abs(v))

FLOAT_RE = re.compile(r"^(const[0-9]+:\s*dq\s*[0-9]*)[\.eE].*")

def normalize(line):
    if ";" in line:
        line = line.split(";", 1)[0]
    line = MATH_RE.sub(domath, line)
    line = FLOAT_RE.sub(r"\1", line)
    line = line.strip()
    line = " ".join(line.split())
    return line

if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        line2 = normalize(line)
        if line2 and not line2.isspace(): print(line2)
