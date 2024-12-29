# main script to run the parser engine

import sys
from pathlib import Path
import argparse
from parser_engine.parser_engine.core.main_parser import MainParser

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_path", type=str, help="The path to the repository to parse", required=True)
    parser.add_argument("--entry_function", type=str, help="The entry function to parse", required=True)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    parser = MainParser(Path(args.repo_path))
    parser.parse_repo()
    parser.build_call_graph()
    parser.display_function_source_and_calls(args.entry_function)