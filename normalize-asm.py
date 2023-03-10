#!/usr/bin/env python3
import re
MATH_RE = re.compile(r"(\d)+\s*([-+])\s*(\d)+")

def domath(m):
    lhs, op, rhs = m.group(1, 2, 3)
    if op == "+":
        return str(int(lhs) + int(rhs))
    elif op == "-":
        return str(int(lhs) - int(rhs))
    else:
        raise ValueError("Invalid operand " + op)

def normalize(line):
    if ";" in line:
        line = line.split(";", 1)[0]
    line = MATH_RE.sub(domath, line)
    line = line.strip()
    return line

if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        line2 = normalize(line)
        if line2 and not line2.isspace(): print(line2)
