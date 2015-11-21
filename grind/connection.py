import asyncssh
import asyncio
from subprocess import PIPE


class BaseResult(object):
    def __init__(self):
        pass

    async def wait(self):
        pass

    async def recv_stdin(self):
        pass

    def return_code(self):
        pass

class BaseConnection(object):
    def __init__(self, config=None, prefixes=None):
        self.config = {} if config is None else config
        self.prefixes = [] if prefixes is None else prefixes

    async def run_result(self, command):
        raise NotImplemented()

    async def run(self, command):
        result = await self.run_result(command)
        return_code = await result.return_code()
        if return_code != 0:
            print(await result.stdout())
            print(await result.stderr())
            raise Exception()

        return await result.stdout()

    async def test(self, command):
        result = await self.run_result(command)

        return await result.return_code() == 0

    def prefix(self, *cmd):
        return type(self)(config=self.config, prefixes=self.prefixes+cmd)


class SSHResult(object):
    def __init__(self, stdin, stdout, stderr):
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr

    async def wait(self):
        await self._stdin.channel.wait_closed()

    async def return_code(self):
        await self.wait()
        return self._stdin.channel.get_exit_status()

    async def stdout(self):
        return await self._stdout.read()

    async def stderr(self):
        return await self._stderr.read()


class SSHConnection(BaseConnection):
    def __init__(self, config):
        self.config = {k.lower(): v for k, v in config.items()}
        self.conn = None

    async def get_connection(self):
        if self.conn is None:
            config = self.config
            key = asyncssh.read_private_key(config['identityfile'])
            self.conn = await asyncssh.connect(
                config['hostname'],
                username=config['user'],
                port=int(config['port']),
                known_hosts=None,
                client_keys=(key,))
        return self.conn

    async def run_result(self, command):
        command = '&&'.join(self.prefixes) + command
        stdin, stdout, stderr = await (await self.get_connection()).open_session(command)
        return SSHResult(stdin, stdout, stderr)

    def file_name(self, file_name):
        return "{}@{}:{}".format(self.config['user'], self.config['hostname'], file_name)


class LocalResult(BaseResult):
    def __init__(self, process):
        self.process = process

    async def wait(self):
        await self.process.wait()

    async def return_code(self):
        await self.wait()
        return self.process.returncode

    async def stdout(self):
        return (await self.process.stdout.read()).decode()

    async def stderr(self):
        return (await self.process.stderr.read()).decode()


class LocalConnection(BaseConnection):
    async def run_result(self, command):
        command = '&&'.join(self.prefixes) + command
        result = await asyncio.create_subprocess_shell(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        return LocalResult(result)

    def file_name(self, file_name):
        return file_name
