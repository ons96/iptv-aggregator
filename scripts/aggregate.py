#!/usr/bin/env python3
"""Fetch all M3U sources from sources.yaml, merge, dedupe by stream URL, write playlist.m3u.

Usage: python3 scripts/aggregate.py [--sources sources.yaml] [--out playlist.m3u]

M3U format: each channel = #EXTINF line + URL line. We dedupe by stream URL
(keep first occurrence). Output is a valid M3U playlist consumable by VLC /
Android TV IPTV apps.
"""
import argparse
import os
import sys
import urllib.request

try:
    import yaml
except ImportError:
    yaml = None


def load_sources(path):
    """Load sources.yaml, return list of URLs. Stdlib fallback if pyyaml missing."""
    if yaml:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data.get("sources", [])
    # ponytail: stdlib fallback - crude YAML parse if pyyaml not installed
    urls = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                url = line[2:].strip().strip('"').strip("'")
                if url.startswith("http"):
                    urls.append(url)
    return urls


def fetch_m3u(url, timeout=30):
    """Fetch an M3U playlist URL, return list of (extinf, url) tuples."""
    req = urllib.request.Request(url, headers={"User-Agent": "iptv-aggregator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"WARN: failed to fetch {url}: {e}", file=sys.stderr)
        return []
    return parse_m3u(data)


def parse_m3u(text):
    """Parse M3U text into list of (extinf_line, url) tuples."""
    channels = []
    extinf = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            extinf = line
        elif line.startswith("#"):
            # other directives (#EXTGRP, #EXTVLCOPT, etc.) - attach to current extinf
            if extinf:
                extinf += "\n" + line
        elif line.startswith("http") or line.startswith("rtmp") or line.startswith("rtsp"):
            channels.append((extinf or "#EXTINF:-1", line))
            extinf = None
        else:
            extinf = None
    return channels


def merge(channels_lists):
    """Merge multiple channel lists, dedupe by stream URL (keep first)."""
    seen = set()
    merged = []
    for channels in channels_lists:
        for extinf, url in channels:
            if url not in seen:
                seen.add(url)
                merged.append((extinf, url))
    return merged


def write_m3u(channels, path):
    """Write channels list to M3U file."""
    with open(path, "w") as f:
        f.write("#EXTM3U\n")
        for extinf, url in channels:
            f.write(extinf + "\n")
            f.write(url + "\n")
    return len(channels)


def main():
    ap = argparse.ArgumentParser(description="Aggregate IPTV M3U sources into one playlist")
    ap.add_argument("--sources", default="sources.yaml", help="sources.yaml path")
    ap.add_argument("--out", default="playlist.m3u", help="output playlist path")
    args = ap.parse_args()

    sources = load_sources(args.sources)
    if not sources:
        print("ERROR: no sources found in config", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching {len(sources)} sources...")
    all_channels = []
    for url in sources:
        print(f"  {url}")
        ch = fetch_m3u(url)
        print(f"    -> {len(ch)} channels")
        all_channels.append(ch)

    merged = merge(all_channels)
    count = write_m3u(merged, args.out)
    print(f"Wrote {count} unique channels to {args.out}")


if __name__ == "__main__":
    main()
