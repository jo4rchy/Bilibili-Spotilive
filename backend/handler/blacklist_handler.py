# backend/handler/blacklist_handler.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from config.config import load_config

try:
    # 可选：如果你项目里已经装了 opencc，就自动启用繁->简
    from opencc import OpenCC  # type: ignore
    _t2s = OpenCC("t2s")
except Exception:
    _t2s = None


# 去掉各种括号内容： (Live) 【原版】（现场）[Remastered] ...
_BRACKET_RE = re.compile(r"\(.*?\)|（.*?）|\[.*?\]|【.*?】|{.*?}|〖.*?〗")
# 统一分隔符：/ : - _ · • 等
_SEP_RE = re.compile(r"[\/:\-|_|·•]+")
# 压缩空白
_SPACE_RE = re.compile(r"\s+")


def normalize(text: Optional[str]) -> str:
    """把文本清洗成可稳定比对的 key。"""
    if not text:
        return ""
    s = text.strip().lower()
    if _t2s:
        s = _t2s.convert(s)
    s = _BRACKET_RE.sub(" ", s)
    s = _SEP_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


@dataclass(frozen=True)
class BlacklistHit:
    ok: bool
    reason: str = ""
    hit_type: str = ""   # artist | track | spotify_uri
    hit_value: str = ""  # 命中的配置项（或解析后的信息）


class Blacklist:
    """
    config.json 结构建议：
    "blacklist": {
        "enabled": true,
        "artists": [...],
        "tracks": [...],
        "spotify_uris": [...]
    }
    """

    def __init__(self) -> None:
        self.enabled: bool = True
        self.artist_keys: Set[str] = set()
        self.track_keys: Set[str] = set()
        self.spotify_uris: Set[str] = set()

    def reload(self) -> None:
        """从 config.json 重新加载黑名单到内存。"""
        cfg = load_config() or {}
        bl = (cfg.get("blacklist") or {}) if isinstance(cfg, dict) else {}
        print("正在加载黑名单配置...")

        self.enabled = bool(bl.get("enabled", True))

        artists = bl.get("artists", []) or []
        tracks = bl.get("tracks", []) or []
        uris = bl.get("spotify_uris", []) or []

        self.artist_keys = {normalize(x) for x in artists if isinstance(x, str) and normalize(x)}
        self.track_keys = {normalize(x) for x in tracks if isinstance(x, str) and normalize(x)}
        self.spotify_uris = {str(x).strip().lower() for x in uris if isinstance(x, str) and x.strip()}

    def _get_song_main_artist(self, song: Dict[str, Any]) -> str:
        artists = song.get("artists") or []
        if isinstance(artists, list) and artists:
            a0 = artists[0] or {}
            if isinstance(a0, dict):
                return str(a0.get("name") or "")
        return ""

    def check_song(self, song: Dict[str, Any]) -> BlacklistHit:
        """
        song 期望结构（来自 Spotify search 结果）：
        {
          "name": "...",
          "uri": "spotify:track:...",
          "artists": [{"name": "..."}]
        }
        """
        if not self.enabled:
            return BlacklistHit(ok=False)

        if not isinstance(song, dict):
            return BlacklistHit(ok=False)

        uri = str(song.get("uri") or "").strip().lower()
        if uri and uri in self.spotify_uris:
            return BlacklistHit(
                ok=True,
                reason="黑名单拦截：歌曲 URI 被封禁",
                hit_type="spotify_uri",
                hit_value=uri,
            )

        name = str(song.get("name") or "")
        main_artist = self._get_song_main_artist(song)

        n_artist = normalize(main_artist)
        if n_artist and n_artist in self.artist_keys:
            return BlacklistHit(
                ok=True,
                reason=f"黑名单拦截：歌手被封禁（{main_artist}）",
                hit_type="artist",
                hit_value=main_artist,
            )

        n_name = normalize(name)
        n_combo = normalize(f"{name} - {main_artist}") if main_artist else ""

        # tracks 支持两种写法：
        # 1) 只写歌名： "Numb"
        # 2) 写 "歌名 - 歌手"： "Numb - Linkin Park"
        if (n_name and n_name in self.track_keys) or (n_combo and n_combo in self.track_keys):
            pretty = f"{name} - {main_artist}".strip(" -")
            return BlacklistHit(
                ok=True,
                reason=f"黑名单拦截：歌曲被封禁（{pretty}）",
                hit_type="track",
                hit_value=pretty,
            )

        return BlacklistHit(ok=False)

    def check_keyword(self, keyword: str) -> BlacklistHit:
        """
        可选：在 Spotify 搜索前就做一次关键词拦截（更省 API 调用）。
        注意：这只能拦截你在 tracks 里写的条目；不能靠它识别歌手/URI。
        """
        if not self.enabled:
            return BlacklistHit(ok=False)

        n_kw = normalize(keyword)
        if n_kw and n_kw in self.track_keys:
            return BlacklistHit(
                ok=True,
                reason=f"黑名单拦截：关键词被封禁（{keyword}）",
                hit_type="track",
                hit_value=keyword,
            )
        return BlacklistHit(ok=False)


# 建议用全局单例，启动时 reload 一次
blacklist = Blacklist()