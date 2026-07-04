# IPTV Aggregator

Free self-hosted IPTV aggregator. Merges multiple public M3U playlist sources into one validated playlist, auto-refreshed via GitHub Actions. One stable URL for your Android TV / VLC / IPTV app.

## How it works

1. `sources.yaml` lists M3U playlist URLs (iptv-org + extras).
2. GitHub Actions runs every 6 hours:
   - `scripts/aggregate.py` fetches all sources, parses, dedupes by stream URL.
   - `scripts/validate.py` probes each stream for liveness (concurrent HEAD/GET), drops dead channels.
   - Result committed as `playlist.m3u`.
3. Your IPTV app subscribes to the raw GitHub URL (always current).

## Playlist URL

```
https://raw.githubusercontent.com/ons96/iptv-aggregator/main/playlist.m3u
```

## Setup for your Android TV box

1. Open your IPTV app (TiviMate, IPTV Smarters, OTT Navigator, etc.).
2. Add a new playlist via URL.
3. Paste the playlist URL above.
4. Done. The playlist auto-refreshes every 6 hours; your app may cache so re-load periodically.

## Test in VLC

```bash
vlc https://raw.githubusercontent.com/ons96/iptv-aggregator/main/playlist.m3u
```

## Add/remove sources

Edit `sources.yaml` in the repo. Each entry is a URL to an M3U/M3U8 playlist:

```yaml
sources:
  - https://iptv-org.github.io/iptv/index.m3u
  - https://example.com/your-source.m3u
```

Commit the change; the next scheduled Actions run picks it up.

## Run locally

```bash
pip install pyyaml
python3 scripts/aggregate.py --sources sources.yaml --out playlist.m3u
python3 scripts/validate.py --in playlist.m3u --out playlist.m3u
```

## Manual refresh

Trigger the workflow manually: Actions tab -> "Update Playlist" -> "Run workflow".

## Sources

Default sources are public-domain (iptv-org, CC0) or publicly available playlists. Only aggregate legitimately accessible public sources. Do not add streams that bypass paid services.

## License

MIT (scripts + config). Playlist data inherits source licenses (iptv-org = CC0).
