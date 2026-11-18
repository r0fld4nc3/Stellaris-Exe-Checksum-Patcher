import argparse


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Generate Achievements Number")
    p.add_argument("to", type=int, help="Last number to generate (included)")

    return p.parse_args(argv)


def gen(to: int) -> str:
    l = [str(i) for i in range(1, to + 1)]
    return " ".join(l)


def main():
    args = parse_args()

    to_n = args.to

    num_str = gen(to_n)
    print(num_str)


if __name__ == "__main__":
    main()
