from shared.slug import unique_slug_generator


class TestSlugHelpers:

    def test_slug_helper(self):

        existing_slugs = {'hola', 'test', 'test-2', 'adios', 'adios-2', 'adios-3'}
        def checker(x):
            return x in existing_slugs

        assert unique_slug_generator('example', checker) == 'example'
        assert unique_slug_generator('hola', checker) == 'hola-2'
        assert unique_slug_generator('test', checker) == 'test-3'
        assert unique_slug_generator('adios', checker) == 'adios-4'
