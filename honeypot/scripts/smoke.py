#!/usr/bin/env python3
"""Run the HP_TESTING image in fresh QEMU sessions; keep serial evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]


class Guest:
    def __init__(self, qemu, log_path, cpus):
        self.log = log_path.open("wb")
        self.output = bytearray()
        self.position = 0
        self.queue = queue.Queue()
        args = [qemu, "-accel", "tcg", "-smp", str(cpus), "-m", "256",
                "-nic", "none", "-display", "none", "-monitor", "none",
                "-serial", "stdio", "-snapshot", "-no-reboot",
                "-drive", "file=fs.img,index=1,media=disk,format=raw",
                "-drive", "file=xv6.img,index=0,media=disk,format=raw"]
        try:
            self.process = subprocess.Popen(
                args, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except BaseException:
            self.log.close()
            raise
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        while chunk := self.process.stdout.read(1):
            self.queue.put(chunk)
        self.queue.put(None)

    def expect(self, pattern, timeout=90):
        deadline = time.monotonic() + timeout
        while True:
            text = bytes(self.output)
            if b"FAIL" in text or b"panic:" in text:
                raise AssertionError(text[-2000:].decode(errors="replace"))
            match = re.search(pattern, text[self.position:])
            if match:
                self.position += match.end()
                return
            try:
                chunk = self.queue.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                raise AssertionError(f"Timed out waiting for {pattern!r}: "
                                     + text[-1000:].decode(errors="replace"))
            if chunk is None:
                raise AssertionError("QEMU exited before expected output: "
                                     + text[-1000:].decode(errors="replace"))
            self.output.extend(chunk)
            self.log.write(chunk)
            if b"\n" in chunk:
                self.log.flush()  # Keep diagnostics readable while a guest is running.

    def boot(self):
        self.expect(rb"hpagent: registered")
        self.expect(rb"init: starting sh")
        self.expect(rb"\$ ")

    def command(self, command, expected, timeout=90):
        # Windows QEMU drops CR on piped stdin and can overrun the emulated
        # UART when a whole command is pasted. Pace input; LF works on both.
        for byte in command.encode() + b"\n":
            self.process.stdin.write(bytes([byte]))
            self.process.stdin.flush()
            time.sleep(0.004)
        self.expect(expected, timeout=timeout)
        self.expect(rb"\$ ")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
        self.thread.join(timeout=5)
        self.process.stdin.close()
        self.process.stdout.close()
        self.log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qemu", default=os.environ.get("QEMU", "qemu-system-i386"))
    parser.add_argument("--cpus", type=int, choices=(1, 2), default=1)
    parser.add_argument("--basic-only", action="store_true",
                        help="Validate a normal image without fault injections")
    parser.add_argument("--upstream", action="store_true",
                        help="Also run xv6 forktest/usertests and check channel recovery")
    args = parser.parse_args()
    artifacts = ROOT / "honeypot" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {"passed": [], "cpus": args.cpus, "status": "running",
              "basic_only": args.basic_only,
              "upstream": args.upstream,
              "started_at": datetime.now(timezone.utc).isoformat()}
    variant = "basic" if args.basic_only else "acceptance"
    if args.upstream:
        variant += "-upstream"
    report_path = artifacts / f"results-{variant}-{args.cpus}cpu.json"
    try:
        report["qemu"] = subprocess.check_output(
            [args.qemu, "--version"], text=True).splitlines()[0]
        report["images"] = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("kernel", "xv6.img", "fs.img")}
        groups = [("main", ["basic", "stress"])]
        if not args.basic_only:
            groups[0][1].extend(["replies", "timeout", "busy", "interrupted", "agentfork"])
            groups.extend((mode, [mode, "absent"]) for mode in ("exit", "exec", "readonly"))
        for group, modes in groups:
            guest = Guest(args.qemu, artifacts / f"{variant}-{group}-{args.cpus}cpu.log", args.cpus)
            try:
                guest.boot()
                guest.command("hpagent", rb"hpagent: registration denied")
                for mode in modes:
                    guest.command("hptest " + mode,
                                  re.escape(("hptest: PASS " + mode).encode()))
                    report["passed"].append(group + ":" + mode)
                    print("PASS", group + ":" + mode, flush=True)
                if group == "main" and args.upstream:
                    for command, expected in (
                            ("forktest", rb"fork test OK"),
                            ("usertests", rb"ALL TESTS PASSED"),
                            ("hptest basic", rb"hptest: PASS basic")):
                        start = len(guest.output)
                        guest.command(command, expected, timeout=300)
                        # Some upstream child tests print lowercase failures
                        # without stopping their parent from reaching the end.
                        output = bytes(guest.output[start:])
                        if re.search(rb"\b(failed|error)\b", output, re.IGNORECASE):
                            raise AssertionError("Upstream test reported failure: "
                                                 + output.decode(errors="replace"))
                        report["passed"].append("upstream:" + command)
                        print("PASS", "upstream:" + command, flush=True)
            finally:
                guest.close()
        report["images_unchanged"] = all(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
            for name, digest in report["images"].items())
        if not report["images_unchanged"]:
            raise AssertionError("QEMU changed a baseline image despite snapshot mode")
        report["status"] = "passed"
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: M1 guest acceptance ({len(report['passed'])} checks); {report_path}")


if __name__ == "__main__":
    main()
