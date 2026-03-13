import os
import platform
import shutil
import subprocess


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return 0, out.strip()
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output.strip()


def start_hotspot(ssid: str = "PineWoodDerby") -> tuple[bool, str]:
    system = platform.system().lower()

    if system == "linux":
        nmcli = shutil.which("nmcli")
        if not nmcli:
            return False, "nmcli not found. Install NetworkManager or start hotspot manually."
        code, out = _run([nmcli, "device", "wifi", "hotspot", "ssid", ssid, "password", ""])
        if code == 0:
            return True, f"Linux hotspot started: {ssid}"
        return False, f"Could not start Linux hotspot automatically.\n{out}"

    if system == "windows":
        netsh = shutil.which("netsh")
        if not netsh:
            return False, "netsh not found. Start hotspot manually from Windows Settings."
        code1, out1 = _run([netsh, "wlan", "set", "hostednetwork", "mode=allow", f"ssid={ssid}", "key="])
        code2, out2 = _run([netsh, "wlan", "start", "hostednetwork"])
        if code1 == 0 and code2 == 0:
            return True, f"Windows hotspot started: {ssid}"
        return False, "Automatic hotspot setup failed. Use Windows Mobile Hotspot manually."

    return False, f"Hotspot automation is not supported on {platform.system()} yet."
