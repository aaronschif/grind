import asyncio
import asyncssh
from subprocess import PIPE
from .connection import SSHConnection, LocalConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def vagrant_connect():
    ssh_config = await asyncio.create_subprocess_exec('vagrant', 'ssh-config', stdout=PIPE)
    config_text, _ = await ssh_config.communicate()

    config = {}
    for line in config_text.decode().split('\n'):
        key_value = line.strip().split(' ', 1)
        if len(key_value) is 2:
            key, value = key_value
            config[key] = value

    return config


async def rsync(local, conn, file_a, file_b):
    await local.run('rsync -e "ssh {}" {} {}'.format(
        ' '.join(['-o {}={}'.format(k, v) for k, v in conn.config.items() if k != 'host']),
        file_a.format(host=conn.config['hostname']),
        file_b.format(host=conn.config['hostname'])
    ))


class DownloadCache(object):
    def __init__(self, path):
        self.path = path
        self.cache = '~/.cache/grind/downloads/'

    def name_from_path(self):
        import os
        from urllib.parse import urlparse
        import hashlib
        return hashlib.md5(self.path.encode()).hexdigest() + '_' + os.path.basename(urlparse(self.path).path)

    def download_location(self):
        return '{}/{}'.format(self.cache, self.name_from_path())

    async def require_cache(self, runner):
        await runner.run('mkdir -p {}'.format(self.cache))

    async def require(self, runner):
        await self.require_cache(runner)
        download_location = self.download_location()
        if not await runner.test('test -r {}'.format(download_location)):
            logger.info('downloading {}'.format(self.path))
            await runner.run('curl {} -o {}'.format(self.path, download_location))
            logger.info('downloaded {}'.format(self.path))
            return True
        else:
            logger.info('already downloaded {}'.format(self.path))
            return False


class Virtualenv(object):
    def __init__(self, location, python='python3'):
        self.location = location
        self.python = python

    def prefix(self):
        return 'source {}/bin/activate'.format(self.location)

    async def create(self, runner):
        logger.info('virtualenv created')
        await runner.run('{} -m venv {}'.format(self.python, self.location))

    async def delete(self, runner):
        logger.info('virtualenv deleted')
        await runner.run('rm -rf {}'.format(self.location))

    async def require(self, runner):
        test = 'test -r {loc}/bin/python \
            && which {py} \
            && test "$({py} --version)" = "$({loc}/bin/python --version)"'
        if not await runner.test(test.format(loc=self.location, py=self.python)):
            await self.delete(runner)
            await self.create(runner)
            return True
        else:
            logger.info('virtuelenv exists')
        return False


async def main():
    virtualenv = Virtualenv('/tmp/somevirtualenv', python='python3.5')
    python_tar = DownloadCache('https://www.python.org/ftp/python/3.5.0/Python-3.5.0.tar.xz')

    c = SSHConnection(await vagrant_connect())
    l = LocalConnection()

    print(await c.run('echo bar'))
    await python_tar.require(c)
    await c.run('mkdir -p ~/.cache/grind/build/python3.5')
    if not await c.test('test -d ~/.cache/grind/build/python3.5.0'):
        await c.run('cd ~/.cache/grind/build/python3.5 && tar afvx {}'.format(python_tar.download_location()))
        await c.run('cd ~/.cache/grind/build/python3.5/Python-3.5.0/ && ./configure && make && sudo make install')

    await rsync(l, c, "./config", "{host}:/tmp/foo_config")
    # await virtualenv.require(l)
    # await virtualenv.require(c)
    print(await l.run('echo foo'))

loop = asyncio.get_event_loop()

loop.run_until_complete(main())

loop.close()
