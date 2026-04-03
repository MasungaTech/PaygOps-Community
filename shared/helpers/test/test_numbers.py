from shared.helpers.numbers import format_thousands


def test_does_not_format_numbers_less_than_one_thousand():
    numbers = [0, 1, 13, 156, 999, -1, -10, 1.2]
    for n in numbers:
        res = format_thousands(n)
        assert res == str(n)


def test_does_format_numbers_more_than_one_thousand():
    numbers = [(1000, '1,000'), (9999, '9,999'), (1239485, '1,239,485')]

    for num_set in numbers:
        res = format_thousands(num_set[0])
        assert res == num_set[1]
