import time


class Timer:

    def __init__(self, name=''):
        self.start = time.time()
        self.name = name

    def __enter__(self):
        pass

    def __exit__(self, *args):
        elapsed = time.time()-self.start
        name = f' for {self.name}' if self.name else ''
        print(f'Time elapsed{name}: {elapsed}s')
