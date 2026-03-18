from __future__ import annotations

import datetime as dt


def main() -> None:
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print("[deploy] simulated deployment started")
    print(f"[deploy] timestamp={now}")
    print("[deploy] step=build-images status=ok")
    print("[deploy] step=push-registry status=ok")
    print("[deploy] step=helm-upgrade-canary status=ok")
    print("[deploy] step=smoke-tests status=ok")
    print("[deploy] step=promote-stable status=ok")
    print("[deploy] simulated deployment finished")


if __name__ == "__main__":
    main()
