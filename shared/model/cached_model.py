

class CachedModelMixin:

    def update_cached_data(self):
        pass

    def cached_data_get(self, key, **kwargs):
        if self.cached_data and key in self.cached_data:
            return self.cached_data[key]
        # We do that to prevent updating modified date
        before_update = self.before_update
        self.before_update = lambda x=1: None
        self.update_cached_data(**kwargs)
        self.before_update = before_update
        return self.cached_data[key]