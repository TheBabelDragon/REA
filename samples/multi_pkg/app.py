"""Entry point using the package."""

from multi_pkg.core.calc import Calculator


def main() -> None:
    calc = Calculator()
    print(calc.compute("+", 2, 3))
    print(calc.compute("*", 4, 5))


if __name__ == "__main__":
    main()
