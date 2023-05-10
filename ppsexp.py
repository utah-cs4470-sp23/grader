
def parse(s):
    i = 0
    stack = [[]]
    while i < len(s):
        if s[i] == '"':
            current = ''
            i += 1
            while i < len(s) and s[i] != '"':
                current += s[i]
                i += 1
            i += 1
            stack[-1].append('"' + current + '"')
        elif s[i].isspace():
            i += 1
        elif s[i] == '(':
            i += 1
            stack.append([])
        elif s[i] == ')':
            i += 1
            if len(stack) > 1:
                sexp = stack.pop()
                stack[-1].append(sexp)
            else:
                stack[-1].append(')')
        else:
            current = ''
            while i < len(s) and s[i] != '"' and not s[i].isspace():
                current += s[i]
                i += 1
            stack[-1].append(current)
    return stack[0]

def p(s):
    if isinstance(s, list):
        return "(" + " ".join(p(i) for i in s) + ")"
    else:
        return s
    
WIDTH = 80

def pp(s, i):
    a = p(s)
    if not isinstance(s, list) or len(a) + i < WIDTH:
        return a
    else:
        lines = ["(" + pp(s[0], i + 1)]
        for a in s[1:]:
            lines.append(" " * (i + 1) + pp(a, i + 1))
        lines[-1] += ")"
        return "\n".join(lines)

def ppsexp(lines):
    t = "\n".join(lines)
    s = parse(t)
    out = ""
    for term in s:
        out += pp(term, 0) + "\n"
    return out.split("\n")
            
