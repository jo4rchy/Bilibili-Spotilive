import asyncio
import re
import random
import difflib
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from utils.log_timer import timestamp
from opencc import OpenCC
import requests

# 创建自定义 Session，加入 Accept-Language Header
session = requests.Session()
session.headers["Accept-Language"] = "zh-CN,zh;q=0.9"

def normalize_text(text: str) -> str:
    """
    将文本转换为简体，然后统一替换常见异体字。
    """
    t2s_converter = OpenCC('t2s')
    return t2s_converter.convert(text)


class SpotifyController:
    def __init__(self, config):
        spotify_config = config.get('spotify', {})
        self.client_id = spotify_config.get('client_id')
        self.client_secret = spotify_config.get('client_secret')
        self.redirect_uri = spotify_config.get('redirect_uri')
        self.scope = spotify_config.get('scope')
        self.default_playlist = spotify_config.get('default_playlist')
        self.room_id = config.get('bilibili', {}).get('room_id')

        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = Spotify(auth_manager=self.sp_oauth, requests_session=session)
        
    def _search_song(self, song_name, limit):
        """
        高度优化的 Spotify 搜索逻辑
        支持：歌手拆分、版本动态加权、错误匹配拦截
        """
        try:
            # 1. 关键词预处理
            song_name = song_name.strip()
            if not song_name:
                return None

            # 检查并拆分歌手 (支持 +, |, / 分隔符)
            if '+' in song_name or '|' in song_name or '/' in song_name:
                # 使用正则匹配分隔符，但只拆分一次，确保第一个分隔符后面才是歌手
                parts = re.split(r'\s*[+|/]\s*', song_name, maxsplit=1)
                song_query = parts[0].strip()
                artist_query = parts[1].strip() if len(parts) > 1 else None
                search_query = f"track:{song_query} artist:{artist_query}"
            else:
                # 没有分隔符，整体作为歌名（适合 "k歌之王 live" 这种输入）
                song_query = song_name
                artist_query = None
                search_query = song_name

            query_normalized = normalize_text(song_query).lower()
            artist_normalized = normalize_text(artist_query).lower() if artist_query else None

            print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 关键词: {song_query} | 歌手: {artist_query or '未提供'}")

            # 2. 执行 Spotify 搜索
            results = self.sp.search(q=search_query, type='track', limit=limit)
            tracks = results.get('tracks', {}).get('items', [])

            for track in tracks:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] {track['name']} - {track['artists'][0]['name']} (流行度: {track.get('popularity', 0)})") 
            
            if not tracks:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] Spotify 未返回任何结果。")
                return None

            # 3. 动态打分与过滤机制
            # 负面关键词列表：这些词在歌名中出现通常意味着“非原版”
            negative_keywords = ['live', 'version', 'air', 'remaster', 'instrumental', 'karaoke', 'edit', 'remix', 'piano', 'dj']
            
            # 核心：动态调整惩罚/奖励（如果用户搜了这些词，就转罚为奖）
            current_negatives = [w for w in negative_keywords if w not in query_normalized]
            positive_boosts = [w for w in negative_keywords if w in query_normalized]

            scored_tracks = []
            for track in tracks:
                t_name = track.get('name', '')
                t_name_norm = normalize_text(t_name).lower()
                t_artists = [normalize_text(a['name']).lower() for a in track.get('artists', [])]
                
                # --- 硬性过滤 A: 歌手校验 ---
                if artist_normalized and not any(artist_normalized in a for a in t_artists):
                    continue

                # --- 计算基础分 (Spotify 流行度 0-100) ---
                score = track.get('popularity', 0)
                
                # --- 算法 1: 文本相似度校验 (防止“k哥之王”变“淘汰”) ---
                # 计算搜索词与结果歌名的相似度比例 (0.0 - 1.0)
                similarity = difflib.SequenceMatcher(None, query_normalized, t_name_norm).ratio()
                
                # 如果相似度极低且关键词未包含，直接大幅扣分
                if similarity < 0.3 and query_normalized not in t_name_norm:
                    score -= 100 

                # --- 算法 2: 惩罚/奖励加权 ---
                # 惩罚：未请求的特殊版本 (如 AIR, Version)
                if any(word in t_name_norm for word in current_negatives):
                    score -= 60
                
                # 奖励：用户主动索要的版本 (如搜了live给live加分)
                if any(word in t_name_norm for word in positive_boosts):
                    score += 50

                # 奖励：纯净度奖励 (原版通常没有括号后缀，长度与查询词最接近)
                len_diff = abs(len(t_name_norm) - len(query_normalized))
                if len_diff <= 2:
                    score += 40
                
                # 奖励：关键词覆盖
                if query_normalized in t_name_norm:
                    score += 20

                scored_tracks.append((track, score))
                # print(f"DEBUG: {t_name} | Score: {score} | Similarity: {similarity:.2f}")

            # 4. 最终评估 (设置及格线)
            if scored_tracks:
                scored_tracks.sort(key=lambda x: x[1], reverse=True)
                best_track, best_score = scored_tracks[0]
                
                # 及格线阈值：设定为 55 分
                # 一个普通的热门歌曲 (50分) + 长度奖励 (40分) 通常有 90 分左右
                # 如果分数低于 55，说明相似度极低或是被重罚的版本
                if best_score < 55:
                    print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 最佳匹配 '{best_track['name']}' 分数过低({best_score})，已拦截无效匹配。")
                    return None

                print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 最终选中: {best_track['name']} - {best_track['artists'][0]['name']} (Score: {best_score})")
                return best_track
            
            print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 找到 {len(tracks)} 个结果，但均未通过评分。")
            return None

        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 搜索逻辑崩溃: {e}")
            return None

    async def search_song(self, song_name: str, limit: int = 5):
        return await asyncio.to_thread(self._search_song, song_name, limit)
    
    def _api_search_song(self, song_name: str, limit):
        """
        使用 API 搜索歌曲，返回结果为字典格式。
        """
        try:
            results = self.sp.search(q=song_name, type='track', limit=limit)
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                return None
            
            track_list = []
            for track in tracks:
                track_list.append(track)
            
            print(f"[{self.room_id}]{timestamp()}[SPOT] [API搜索] 找到 {len(track_list)} 首歌曲")
            return track_list
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] API 搜索歌曲出错: {e}")
            return None
        
    async def api_search_song(self, song_name: str, limit: int = 3):
        return await asyncio.to_thread(self._api_search_song, song_name, limit)
        

    def _play_song(self, track, start_ms=0):
        try:
            uri = track['uri']
            name = track['name']
            artist = track['artists'][0]['name']
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 正在播放: {name} - {artist}")
            self.sp.start_playback(uris=[uri], position_ms=start_ms)
        except Exception as e:
            error_msg = str(e)
            if "No active device found" in error_msg:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: 未检测到活跃的播放设备，请先在 Spotify 客户端播放任意歌曲后重试。")
            else:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: {error_msg}")

    async def play_song(self, track: dict):
        await asyncio.to_thread(self._play_song, track)

    def _next_song(self):
        try:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 播放下一首歌曲")
            self.sp.next_track()
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放下一首歌曲出错: {e}")

    async def next_song(self):
        await asyncio.to_thread(self._next_song)

    def _restore_default_playlist(self):
        try:
            if not self.default_playlist:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 默认歌单未设置。")
                return
            playlist = self.sp.playlist(self.default_playlist)
            total = playlist['tracks']['total']
            if total <= 0:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 默认歌单为空。")
                return
            random_index = random.randint(0, total - 1)
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 播放默认歌单，从随机位置 {random_index} 开始播放。")
            self.sp.start_playback(context_uri=self.default_playlist, offset={"position": random_index})
        except Exception as e:
            error_msg = str(e)
            if "No active device found" in error_msg:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: 未检测到活跃的播放设备，请先在 Spotify 客户端播放任意歌曲后重试。")
            else:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: {error_msg}")

    async def restore_default_playlist(self):
        await asyncio.to_thread(self._restore_default_playlist)

    def _get_current_playback(self):
        try:
            return self.sp.currently_playing(market='HK') or None
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 获取当前播放信息出错: {e}")
            return None

    async def get_current_playback(self):
        return await asyncio.to_thread(self._get_current_playback)
