#!/bin/sh
set -x -e

DIR="$1"

sed -i bak "s/ReadImageCmd/ReadCmd/g" "$DIR"/*.jpl.expected
sed -i bak "s/WriteImageCmd/WriteCmd/g" "$DIR"/*.jpl.expected
