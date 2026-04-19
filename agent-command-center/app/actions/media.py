from ._base import run_applescript, escape, app_running, ok, fail
from .browser import youtube_play

_SPOTIFY_OPS = {
    "play": "play", "pause": "pause", "play_pause": "playpause",
    "next": "next track", "prev": "previous track", "previous": "previous track",
}
_MUSIC_OPS = {
    "play": "play", "pause": "pause", "play_pause": "playpause",
    "next": "next track", "prev": "previous track",
}


def spotify(operation: str, query: str = "") -> dict:
    if not app_running("Spotify"):
        return youtube_play(query + " song") if query \
               else fail("Spotify", "Spotify not running. Try: 'play [song] on YouTube'")

    if operation in _SPOTIFY_OPS:
        r = run_applescript(f'tell application "Spotify" to {_SPOTIFY_OPS[operation]}')
        return ok(f"Spotify: {operation}", operation) if r["ok"] else fail("Spotify", r["err"])

    if operation in ("search", "play_song") and query:
        q = escape(query)
        r = run_applescript(f'''
tell application "Spotify" to activate
delay 0.5
tell application "System Events"
    keystroke "l" using command down
    delay 0.4
    keystroke "{q}"
    key code 36
end tell''')
        return ok(f'Spotify: "{query}"', f"Playing {query}") if r["ok"] \
               else fail("Spotify", r["err"])

    return fail("Spotify", f"Unknown operation: {operation}")


def apple_music(operation: str, query: str = "") -> dict:
    if operation in _MUSIC_OPS:
        r = run_applescript(f'tell application "Music" to {_MUSIC_OPS[operation]}')
        return ok(f"Apple Music: {operation}", operation) if r["ok"] \
               else fail("Apple Music", r["err"])

    if operation in ("search", "play_song") and query:
        q = escape(query)
        r = run_applescript(
            f'tell application "Music" to activate\n'
            f'tell application "Music" to search playlist "Library" for "{q}"'
        )
        return ok(f'Apple Music: "{query}"', f"Playing {query}") if r["ok"] \
               else youtube_play(query + " song")

    return fail("Apple Music", f"Unknown: {operation}")
