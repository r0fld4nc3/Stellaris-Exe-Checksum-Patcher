import argparse


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Application Startup")
    p.set_defaults(debug=False, no_conn=False)

    p.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug mode and expose more debugging information."
    )
    p.add_argument("--no-conn", action="store_true", help="Prevent all external connections.")

    return p.parse_args()
