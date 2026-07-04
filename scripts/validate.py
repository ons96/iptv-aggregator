#!/usr/bin/env python3
"""Validate stream liveness in an M3U playlist. Drop dead channels.

Usage: python3 scripts/validate.py [--in playlist.m3u] [--out playlist.m3u] [--timeout 10] [--workers 20]

Probes each stream URL with a bounded HEAD/GET request. Streams that time out
or return 4xx/5xx are dropped. Concurrent via stdlib ThreadPoolExecutor.
"""
import argparse
import concurrent.futures
import sys
import urllib.request
import urllib.error

from aggregate import parse_m3u


def probe_url(url, timeout=10):
    """Return True if URL responds with 2xx/3xx, False on timeout/error. rtsp/rtmp skipped (assume live)."""
    if url.startswith("rtsp") or url.startswith("rtmp"):
        return True  # ponytail: can't HTTP-probe rtsp/rtmp; assume live
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "iptv-aggregator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as e:
        # Some servers reject HEAD; try GET with range to minimize download
        if e.code in (405, 403, 501):
            req2 = urllib.request.Request(url, headers={"User-Agent": "iptv-aggregator/1.0", "Range": "bytes=0-1023"})
            try:
                with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                    return 200 <= resp2.status < 400
            except Exception:
                return False
        return False
    except Exception:
        return False


def validate_playlist(in_path, out_path, timeout, workers):
    """Read playlist, probe all streams concurrently, write live channels back."""
    with open(in_path) as f:
        text = f.read()
    channels = parse_m3u(text)
    print(f"Validating {len(channels)} streams (timeout={timeout}s, workers={workers})...")

    live = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(probe_url, url, timeout): (extinf, url) for extinf, url in channels}
        for i, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            extinf, url = future_map[future]
            alive = future.result()
            if alive:
                live.append((extinf, url))
            if i % 100 == 0:
                print(f"  {i}/{len(channels)} probed, {len(live)} live")

    with open(out_path, "w") as f:
        f.write("#EXTM3U\n")
        for extinf, url in live:
            f.write(extinf + "\n")
            f.write(url + "\n")
    dropped = len(channels) - len(live)
    print(f"Done: {len(live)} live, {dropped} dropped -> {out_path}")
    return len(live)


def main():
    ap = argparse.ArgumentParser(description="Validate IPTV stream liveness")
    ap.add_argument("--in", dest="inp", default="playlist.m3u")
    ap.add_argument("--out", default="playlist.m3u")
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()
    validate_playlist(args.inp, args.out, args.timeout, args.workers)


if __name__ == "__main__":
    main()
