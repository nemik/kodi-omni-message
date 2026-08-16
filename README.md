# Kodi Omni Message

A Kodi service add-on that blocks playback. Whenever anything is played — video, music, a plugin
stream, live TV — it stops immediately and shows a message you configure instead. An optional PIN
unlocks playback for a while.

Useful for parental controls, or for explaining why a library is unavailable.

Targets **Kodi 19 (Matrix) and newer** (`xbmc.python` 3.0.0).

## Install

Build the zip and install it the normal Kodi way:

```bash
bash scripts/package.sh          # -> dist/service.omnimessage-1.0.0.zip
```

On the Kodi box: **Settings → System → Add-ons → Unknown sources** (once), then
**Settings → Add-ons → Install from zip file** and pick the zip. See
[Getting builds onto a test PC](#getting-builds-onto-a-test-pc) for the quick ways to get the file
there.

The service starts as soon as the add-on is installed and enabled.

## Settings

**Settings → Add-ons → My add-ons → Services → Omni Message → Configure**

| Setting | Default | What it does |
| --- | --- | --- |
| Block playback | on | Master switch. Off means the add-on does nothing. |
| Title | `Playback blocked` | Dialog/notification heading. |
| Message text | `Playback is currently disabled.` | **The message shown instead of the media.** |
| Show as | Dialog | `Dialog` is a modal you must dismiss; `Notification` is a corner toast (no PIN prompt — a toast has nowhere to put one). |
| Notification duration | 5s | Only used in notification mode. |
| PIN | empty | Digits. Empty means no unlock is offered at all. |
| Unlock for | 30 min | How long playback is allowed after a correct PIN. `0` allows only the blocked item. |
| Debug logging | off | Extra detail in the Kodi log. |

With a PIN set, the block dialog offers **Enter PIN**; a correct entry replays the item that was
blocked and keeps playback open for the configured window. `Unlock for = 0` opens a 60-second
window instead — just long enough for the blocked item to start — then locks again.

Settings changes take effect immediately; no restart needed.

## Development

Dev tooling is managed with [uv](https://docs.astral.sh/uv/). The add-on itself has **no runtime
dependencies** — Kodi ships its own Python and the `xbmc*` modules are built in.

```bash
uv run pytest                                    # 38 tests, no Kodi required
uv run python -m compileall service.omnimessage  # syntax check
uv run python scripts/make_icon.py               # regenerate resources/icon.png
```

`tests/stubs/` contains minimal stand-ins for `xbmc`, `xbmcgui`, `xbmcaddon` and `xbmcvfs`, wired up
through `pythonpath` in `pyproject.toml`, so the real add-on code imports and runs on a machine with
no Kodi installed.

Layout:

```
service.omnimessage/
  service.py                  entry point; the loop that shows the message
  resources/lib/policy.py     all decision logic — pure Python, no Kodi imports
  resources/lib/blocker.py    xbmc.Player / xbmc.Monitor subclasses
  resources/lib/settings.py   typed settings snapshot
  resources/lib/ui.py         dialogs and notifications
  resources/settings.xml      settings definition
```

Kodi has no pre-playback hook, so interception works by stopping playback the instant it starts:
`onPlayBackStarted` (with `onAVStarted` as a backstop) captures the path, calls `stop()`, and hands
off to the service thread — Kodi's player thread must not be blocked with modal UI.

## Getting builds onto a test PC

Two paths. The first is for iterating, the second is for verifying a real install.

### 1. SSH deploy (fast loop)

```bash
cp scripts/deploy.env.example scripts/deploy.env   # once: fill in host, user, RPC creds
ssh-copy-id kodi@192.168.1.50                      # once: passwordless rsync
bash scripts/deploy.sh
```

`deploy.sh` rsyncs `service.omnimessage/` straight into Kodi's add-on directory, then restarts the
service over Kodi's JSON-RPC API (disable + re-enable), so new Python is live in a couple of
seconds without touching the TV.

Prerequisites on the Kodi box:

- **Settings → Services → Control → Allow remote control via HTTP** (port 8080 by default; set a
  username/password and put them in `deploy.env`).
- `KODI_ADDON_DIR` must be Kodi's real add-on directory. A path without a leading `/` is resolved
  against the remote user's home. **Don't use `~`** — `deploy.env` is sourced locally, so a tilde
  would expand to your own machine's home and rsync would aim at a path that doesn't exist there.

Two caveats, both about when Kodi notices things:

- **A brand-new add-on is unknown to Kodi until it restarts** — Kodi only scans the add-on
  directory at startup, so the first `deploy.sh` copies the files but can't start the service. Do
  one of these once: restart Kodi, or install the zip (below). After that, `deploy.sh` restarts the
  service by itself. If Kodi runs as a systemd service you can set `KODI_RESTART_CMD` in
  `deploy.env` and the script will handle even that; leave it unset if Kodi is launched by your
  desktop session, where there's nothing sensible to restart.
- **The service restart only reloads Python.** Changes to `addon.xml` or `resources/settings.xml`
  need a full Kodi restart before Kodi re-reads them.

### 2. HTTP install from zip (clean install)

No SSH needed, and it exercises the same path an end user takes.

```bash
bash scripts/serve.sh          # packages, prints this Mac's LAN IP, serves dist/ on :8000
```

On the Kodi box:

1. **Settings → System → Add-ons → Unknown sources** → on.
2. **Settings → File manager → Add source** → `http://<mac-ip>:8000/` → name it e.g. `omni`.
3. **Settings → Add-ons → Install from zip file** → `omni` → pick the `.zip`.

Re-run `serve.sh` after each build; step 3 picks up the new file (the source from step 2 stays).

Alternatively, just copy the zip over and install it from local storage:

```bash
scp dist/service.omnimessage-*.zip kodi@192.168.1.50:~/
```

### Debugging

Turn on **Debug logging** in the add-on settings, then watch the log while you test:

```bash
ssh kodi@192.168.1.50 'tail -f ~/.kodi/temp/kodi.log' | grep -i omnimessage
```

Add-on directories, for reference:

| Platform | Path |
| --- | --- |
| Linux desktop | `~/.kodi/addons` |
| LibreELEC / CoreELEC | `/storage/.kodi/addons` |
| Windows | `%APPDATA%\Kodi\addons` |
| macOS | `~/Library/Application Support/Kodi/addons` |

## Limitations

Worth knowing before relying on this:

- **Kodi has no pre-playback veto.** Playback is stopped as fast as an add-on can, but a fraction of
  a second of audio or video may register before the stop lands.
- **It is not tamper-proof.** The PIN and the master switch live in add-on settings, so anyone who
  can reach Kodi's settings screen can disable the add-on. For a real lockdown, pair it with Kodi's
  own master lock (**Settings → Interface → Master lock**), which can gate the settings and add-on
  screens.
- **Unlock state is in memory.** Restarting Kodi clears any active unlock window, which fails
  closed.

## License

MIT — see [LICENSE](service.omnimessage/LICENSE).
