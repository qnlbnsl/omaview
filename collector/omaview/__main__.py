import argparse
import asyncio
import ctypes
import os
import signal
import sys
import time

from . import mock, nvml, sampler, sensors, server, system


def live_sampler():
    gpu = nvml.Nvml.open(names=system.process_name)
    return sampler.Sampler(
        read=system.read_text, clock=time.monotonic, physical_ifaces=system.physical_interfaces,
        whole_disks=system.whole_disks, hwmon=sensors.read_hwmon, gpu=gpu, rapl=system.rapl_energy,
        topology=sensors.read_topology, passthrough=system.passthrough_gpus,
        processes=system.FreshProcesses(system.ProcessTable()), volumes=system.volumes,
        disk_models=system.disk_models, interfaces=system.interfaces,
    )


def default_socket():
    return os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "omaview.sock")


def main():
    parser = argparse.ArgumentParser(prog="omaview-collector")
    parser.add_argument("--socket", default=default_socket())
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--mock", action="store_true", help="serve fake data for UI work")
    parser.add_argument("--once", action="store_true", help="print one detailed sample and exit")
    args = parser.parse_args()

    if args.once:
        import json
        source = mock.Sampler() if args.mock else live_sampler()
        source.sample(True)
        time.sleep(1)
        print(json.dumps(source.sample(True), indent=1))
        return 0

    # Die with the shell even if it crashes before it can stop us.
    ctypes.CDLL(None).prctl(1, signal.SIGTERM)
    srv = server.Server(args.socket, mock.Sampler() if args.mock else live_sampler(), args.interval)
    if not srv.acquire():
        return 0
    try:
        asyncio.run(srv.run())
    finally:
        srv.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
