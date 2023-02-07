#!/bin/sh
i=1
cat "$1" | while read l; do
    printf "%s\n" "$l" > "$2"/"$i".jpl
    i=$((i + 1))
done
