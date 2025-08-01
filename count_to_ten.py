import time


def count_to_ten():
    """Print numbers from 1 to 10 with a one second pause."""
    for i in range(1, 11):
        print(i)
        time.sleep(1)


if __name__ == "__main__":
    count_to_ten()

