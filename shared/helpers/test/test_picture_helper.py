from shared.helpers.picture_helper import allowed_file



def test_allowed_file_with_proper_extension():
    file_names = ['a.jpg', 'a.jpeg', 'a.JPEG', 'a.JPG']
    for f in file_names:
        res = allowed_file(f)
        assert res


def test_file_without_proper_extension():
    file_names = ['a.png', 'a.', 'a.svg', 'a.123', 'a']

    for f in file_names:
        res = allowed_file(f)
        assert not res


