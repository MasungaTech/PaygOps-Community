from slugify import slugify


def unique_slug_generator(base, checker):
    original_slug = slugify(base)
    slug = original_slug
    i = 2
    while checker(slug):
        slug = f"{original_slug}-{i}"
        i += 1
    return slug
