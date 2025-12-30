import argparse

# Argparser
PARSER = argparse.ArgumentParser(description="Application Startup")
PARSER.set_defaults(debug=False, no_conn=False)

PARSER.add_argument(
    "-d", "--debug", action="store_true", help="Enable debug mode and expose more debugging information."
)

PARSER.add_argument("--no-conn", action="store_true", help="Prevent all external connections.")

try:
    ARGUMENTS = PARSER.parse_args()
except Exception as e:
    print(f"Error parsing arguments: {e}")
    ARGUMENTS = PARSER.parse_args([])
