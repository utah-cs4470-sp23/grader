#!/bin/sh
i=1
cat "$1" | while read l; do
    printf "%s\n" "$l" > hw5/ok/$i.jpl
    i=$((i + 1))
done
