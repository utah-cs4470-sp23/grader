
#pip install fuzzingbook
import fuzzingbook.Grammars as fb

from fuzzingbook.MutationFuzzer import MutationFuzzer

import argparse
import random
from datetime import datetime
from pathlib import Path
import string
import sys

sys.path.append("/Users/pavpan/jpl/pavpan/src/")

import lexer, parse

JPL_EBNF_GRAMMAR = {
    "<start>": ["<cmd>"],
    "<cmd>": ["read image <string> to <argument>",
              "write image <expr> to <string>",
              "type <variable> = <type>",
              "let <lvalue> = <expr>",
              "assert <expr>, <string>",
              "print <string>",
              "show <expr>",
              "time <cmd>",
              "fn <variable> ( <bindings> ) : <type> { <newline> <stmts> <newline> }",
              ],

    "<types>": [ "", "<type>", "<type> , <types>" ],
    "<type>": [ "int", "float", "bool", "<variable>",
                "<type> [ <commas> ]", "{ <types> }"
               ],
    
    "<bindings>": ["", "<binding>", "<binding> , <bindings>"],
    "<binding>": ["<argument> : <type>",
                  "{ <bindings> }"
                  ],

    "<stmts>": ["", "<stmt>", "<stmt> <newline> <stmts>"],
    "<stmt>": [
        "let <lvalue> = <expr>",
        "assert <expr>, <string>",
        "return <expr>"],

    "<newline>": ["\n"],

    "<exprs>": ["", "<expr>", "<expr> , <exprs>"],
    "<expr>": [
        "<integer>", "<float>", "true", "false", "<variable>",
        "{ <exprs> }", "[ <exprs> ]", "( <expr> )",
        "<expr> { <integer> }", "<expr> [ <exprs> ]",
        "if <expr> then <expr> else <expr>",
        "<variable> ( <exprs> )",
        "array [ <bounds> ] <expr>",
        "sum [ <bounds> ] <expr>",
    ],
    
    "<bounds>": ["",
                 "<variable> : <expr>",
                 "<variable> : <expr>, <bounds>"],
    "<commas>": ["", ", <commas>"],

    "<argument>": ["<variable>", "<variable> [ <variables> ]" ],

    "<lvalues>": ["", "<lvalue>", "<lvalue> , <lvalue>"],
    "<lvalue>": ["<argument>", "{ <lvalues> }"],

    "<float>": ["<integer>+.<integer>*", ".<integer>+"],
    "<integer>": ["<digit>+"],
    "<variables>": ["<variable>", "<variable> , <variables>"],
    #"<variable>": ["<letter>(<digit><letter><var_spec_char>)*"],
    "<variable>": ["<letter>"],
    "<string>": ['"<str_char>*"'],

    #"<var_spec_char>": ["_", "."],
    "<digit>": fb.srange(string.digits),
    "<letter>": fb.srange(string.ascii_letters),
    "<str_char>": [' ', '!', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~']
}

JPL_GRAMMAR = fb.convert_ebnf_grammar(JPL_EBNF_GRAMMAR)

def generate(test_num, min_test_len, max_test_len, out_dir, max_non_terminals, do_fuzz):
    assert fb.is_valid_grammar(JPL_GRAMMAR)

    seed = datetime.now().timestamp()
    print ("Seed is ", seed)
    random.seed(seed)

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    test_id = 0
    while test_id < test_num:
        print("Test #", test_id)
        test_len = int(random.uniform(min_test_len, max_test_len))
        content = "\n".join([fb.simple_grammar_fuzzer(JPL_GRAMMAR, max_nonterminals=max_non_terminals) for i in range(test_len)]) + "\n"

        if do_fuzz:
            try:
                tokens = lexer.lex(content)
            except AssertionError as e:
                continue
            else:
                p = random.random()
                if p < .25:
                    i = random.randint(0, len(tokens) - 1)
                    del tokens[i]
                elif p < .5:
                    i = random.randint(0, len(tokens) - 1)
                    tokens.insert(i, tokens[i])
                else:
                    i = random.randint(0, len(tokens) - 1)
                    j = random.randint(0, len(tokens) - 1)
                    t = tokens[i]
                    tokens[i] = tokens[j]
                    tokens[j] = t

                try:
                    parse.parse(tokens, 0)
                except AssertionError as e:
                    print(e)
                    pass
                else:
                    continue

                content = " ".join(t.contents() for t in tokens).replace(" \n ", "\n")
        
        with Path(out_dir, "{:03}.jpl".format(test_id + 1)).open("w") as out_file:
            out_file.write(content)
        test_id += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate tests for JPL',\
                                     epilog="You can run it with python3.8 fuzzer.py 2 1 20 --max-non-terminals 200 --out-dir out")
    parser.add_argument('test_num', type=int, default=1,
                        help='Number of tests to generate')
    parser.add_argument('min_test_len', type=int, default=1,
                        help='minimal test length')
    parser.add_argument('max_test_len', type=int, default=10,
                        help='maximal test length')
    parser.add_argument('--out-dir', type=Path, default="out",
                        help='Output directory')
    parser.add_argument('--max-non-terminals', type=int, default=5,
                        help='Maximal number of non-terminals in production chain')
    parser.add_argument('--fuzz', action="store_true", default=False,
                        help='Fuzz to get stuff that doesn\'t parse')

    args = parser.parse_args()
    generate(args.test_num, args.min_test_len, args.max_test_len, args.out_dir, args.max_non_terminals, args.fuzz)
