import random

a = open("ok/all.jpl").read()
cmds, both, stmt, fns = [b.split("\n") for b in a.split("\n\n")]

num = 0
for line in cmds:
    with open("ok/{:03}.jpl".format(num), "w") as f:
        f.write(line + "\n")
        num += 1

for line in both:
    with open("ok/{:03}.jpl".format(num), "w") as f:
        f.write(line + "\n")
        num += 1

for header in fns:
    body = random.choice(both + stmt)
    with open("ok/{:03}.jpl".format(num), "w") as f:
        f.write(header + "\n")
        f.write(body + "\n")
        f.write("}" + "\n")
        num += 1

