"""Single-instance Unix socket server. Every connected bar shares one collector."""
import asyncio
import fcntl
import json
import os


class Server:
    def __init__(self, path, sampler, interval=2.0):
        self._path = path
        self._sampler = sampler
        self._interval = interval
        self._lock = None
        self._clients = {}

    def acquire(self):
        """True when this process becomes the collector. Another live collector makes it False."""
        handle = open(self._path + ".lock", "w")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self._lock = handle
        return True

    def release(self):
        if self._lock:
            self._lock.close()
            self._lock = None

    @property
    def _detail(self):
        return any(self._clients.values())

    async def _handle(self, reader, writer):
        self._clients[writer] = False
        try:
            while line := await reader.readline():
                command = line.decode(errors="ignore").strip()
                if command in ("detail on", "detail off"):
                    self._clients[writer] = command == "detail on"
                    if command == "detail on":
                        self._wake.set()
        except OSError:
            pass
        finally:
            self._clients.pop(writer, None)
            writer.close()

    def _broadcast(self, message):
        payload = (json.dumps(message, separators=(",", ":")) + "\n").encode()
        for writer in list(self._clients):
            try:
                writer.write(payload)
            except OSError:
                self._clients.pop(writer, None)

    async def run(self):
        self._wake = asyncio.Event()
        if os.path.exists(self._path):
            os.unlink(self._path)
        server = await asyncio.start_unix_server(self._handle, path=self._path)
        async with server:
            while True:
                self._broadcast(self._sampler.sample(self._detail))
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), self._interval)
                except TimeoutError:
                    pass
