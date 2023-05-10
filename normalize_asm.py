#!/usr/bin/env python3
import re
ADDRESS_RE = re.compile(r"\[([a-z][a-z0-9]+)([- +0-9]*)\]")

def domath(m):
    reg, rest = m.group(1, 2)
    ctr = 0
    cur_num = ""
    for char in rest:
        if char in "+-":
            val = cur_num.replace(" ", "")
            if not val:
                cur_num = char
            elif val in "-+":
                cur_num = {
                    "++": "+", "--": "+", "+-": "-", "-+": "-",
                }[val + char]
            else:
                ctr += int(val)
                cur_num = char
        else:
            cur_num += char
    val = cur_num.replace(" ", "")
    if val: ctr += int(val)

    if ctr == 0:
        return "[" + reg + "]"
    elif ctr < 0:
        return "[" + reg + " - " + str(abs(ctr)) + "]"
    elif ctr > 0:
        return "[" + reg + " + " + str(abs(ctr)) + "]"
    
def redo_float(m):
    name, val, rest = m.group(1, 2, 3)
    if "." in val or "e" in val or "E" in val:
        val = str(float(val))
    return name + val + rest

FLOAT_RE = re.compile(r"^(const[0-9]+:\s*dq\s*)([0-9\.eE+-]+)(.*)$")

def normalize_line(line):
    if ";" in line:
        line = line.split(";", 1)[0]
    line = ADDRESS_RE.sub(domath, line)
    line = FLOAT_RE.sub(redo_float, line)
    line = line.strip()
    line = " ".join(line.split())
    return line

def normalize(lines):
    for line in lines:
        line2 = normalize_line(line)
        if line2 and not line2.isspace():
            yield line2

if __name__ == "__main__":
    import sys
    for line in normalize(sys.stdin):
        print(line2)
