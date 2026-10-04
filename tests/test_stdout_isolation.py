"""Library prints must never reach the protocol stream."""
import subprocess
import sys

SCRIPT = """
import os, sys, anyio
from ask_another.server import _isolate_stdout
out = _isolate_stdout()
print("LiteLLM noise")
os.write(1, b"raw noise\\n")
async def write():
    await out.write("protocol\\n")
    await out.flush()
anyio.run(write)
"""


def test_prints_go_to_stderr_and_protocol_keeps_stdout():
    r = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "protocol\n"
    assert "LiteLLM noise" in r.stderr and "raw noise" in r.stderr
