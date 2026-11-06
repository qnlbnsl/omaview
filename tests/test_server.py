import asyncio
import json
import os
import pathlib
import tempfile
import unittest
from omaview import server


class Script:
    def __init__(self):
        self.calls = []

    def sample(self, detail):
        self.calls.append(detail)
        return {"detail": detail, "n": len(self.calls)}


class Server(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(pathlib.Path(self.tmp.name) / "omaview.sock")
        self.sampler = Script()
        self.srv = server.Server(self.path, self.sampler, interval=0.02)
        self.assertTrue(self.srv.acquire())
        self.task = asyncio.create_task(self.srv.run())
        await asyncio.sleep(0.01)

    async def asyncTearDown(self):
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        self.srv.release()

    async def next_message(self, reader):
        return json.loads(await asyncio.wait_for(reader.readline(), 2))

    async def test_client_receives_json_lines(self):
        reader, writer = await asyncio.open_unix_connection(self.path)
        self.assertIn("n", await self.next_message(reader))
        writer.close()

    async def test_detail_on_switches_samples_to_detail(self):
        reader, writer = await asyncio.open_unix_connection(self.path)
        writer.write(b"detail on\n")
        await writer.drain()
        for _ in range(20):
            if (await self.next_message(reader))["detail"]:
                break
        else:
            self.fail("detail never turned on")
        writer.close()

    async def test_detail_turns_off_when_requesting_client_disconnects(self):
        reader, writer = await asyncio.open_unix_connection(self.path)
        writer.write(b"detail on\n")
        await writer.drain()
        await self.next_message(reader)
        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.08)
        self.assertFalse(self.sampler.calls[-1])

    async def test_second_instance_cannot_acquire(self):
        other = server.Server(self.path, self.sampler, interval=1)
        self.assertFalse(other.acquire())


if __name__ == "__main__":
    unittest.main()
