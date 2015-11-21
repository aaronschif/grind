

class BaseProvider(object):
    async def require(self, runner):
        pass

    async def exists(self, runner):
        pass

    async def delete(self, runner):
        pass

    async def create(self, runner):
        pass

    async def delete_after(self, runner):
        pass


class DownloadProvider(BaseProvider):
    pass


class AptProvider(BaseProvider):
    def __init__(self):
        self._cache = {}

    async def fetch_cache(self, runner):
        await runner.run('dpkg --list')

    def clear_cache(self):
        pass



# class CompileBuildInstallProvider
