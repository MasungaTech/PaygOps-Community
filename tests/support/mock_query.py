from shared.cache.redis_config import key_exists


class MockQuery:

    idx = 0

    def __init__(self, results=None):
        if not results:
            results = []
        self.results = results
        self.length = len(results)

    def __iter__(self):
        self.idx = 0
        return self

    def __getitem__(self, idx):
        return self.results[idx]

    def __next__(self):
        idx = self.idx
        if idx < self.length:
            self.idx += 1
            return self.results[idx]
        raise StopIteration

    def __len__(self):
        return self.length

    def count(self):
        return self.length

    def page(self, page_number, page_size=10):
        start = min(page_size*(page_number-1), self.length)
        end = min(page_size*page_number, self.length)
        return self.results[start:end]

    def first(self):
        return self.results[0] if self.length else None

    def without_distinct(self):
        return self

    def filter(self, criteria=None):
        return MockQuery([result for result in self.results if not criteria or criteria(result)])

    def order_by(self, criteria=None):
        return self
    
    def select(self, criteria=None):
        return self
    
    def exists(self, **kwargs):
        return False
    
    def get(self, **kwargs):
        for result in self.results:
            match = True
            for k in kwargs:
                if not hasattr(result, k) or getattr(result, k) != kwargs[k]:
                    match = False
                    break
            if match:
                return result
