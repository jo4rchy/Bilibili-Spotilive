import asyncio
import re
import time
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

def normalize_text(text):
    if not text: return ""
    # 移除括号内容及特殊符号
    text = re.sub(r'\(.*?\)|\[.*?\]|【.*?】', '', text)
    # 统一分隔符为空格
    text = text.replace('/', ' ').replace(':', ' ').replace('-', ' ').replace('|', ' ')
    return " ".join(text.split()).strip()

s2t = OpenCC('s2t')  # 简体转繁体
t2s = OpenCC('t2s')  # 繁体转简体


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
        
    def _search_song(self, song_name, limit=5):
        try:
            raw_input = song_name.strip()
            if not raw_input: return None
            # 统一转简体用于比对
            raw_query_s = t2s.convert(raw_input.lower())
            
            # 1. 解析歌手与歌名
            if '+' in raw_input:
                parts = re.split(r'\s*\+\s*', raw_input, maxsplit=1)
                song_query = parts[0].strip()
                artist_query = parts[1].strip() if len(parts) > 1 else None
            else:
                song_query, artist_query = raw_input, None

            # 2. 阶梯搜索策略
            search_steps = []
            if any(w in raw_input.lower() for w in ['live', '现场', 'remix']):
                search_steps.append({"q": f"{song_query} {artist_query}" if artist_query else song_query, "desc": "版本组合搜索"})
            search_steps.append({"q": f"track:{song_query} artist:{artist_query}" if artist_query else song_query, "desc": "高级精确搜索"})
            
            print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 输入: {raw_input}")

            tracks = []
            hit_desc = "无"
            for step in search_steps:
                results = self.sp.search(q=step['q'], type='track', limit=limit)
                items = results.get('tracks', {}).get('items', [])
                if items:
                    tracks = items
                    hit_desc = step['desc']
                    break

            if not tracks: 
                print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 未找到匹配的歌曲")
                return None

            # 3. 评分逻辑 (重点修正歌手权重与覆盖判定)
            # 提取干净的关键词列表，排除 '+' 等符号
            query_words = [t2s.convert(w.lower()) for w in re.split(r'[\s\+]+', raw_input) if len(w) > 0]
            q_artist_s = t2s.convert(artist_query.lower()) if artist_query else None
            wants_live = any(word in raw_input.lower() for word in ['live', '现场'])

            scored_tracks = []
            for idx, track in enumerate(tracks):
                t_raw_name = track.get('name', '')
                t_main_artist = track['artists'][0]['name']
                
                # 归一化处理
                t_full_name_s = t2s.convert(t_raw_name.lower())
                t_pure_name_s = t2s.convert(normalize_text(t_raw_name).lower())
                t_artist_s = t2s.convert(t_main_artist.lower())
                t_all_metadata = f"{t_full_name_s} {t_artist_s}"

                # A. 歌手匹配 (这是最高优先级)
                artist_match = False
                if q_artist_s:
                    # 只要歌手名字包含或者被包含，就判定匹配
                    if q_artist_s in t_artist_s or t_artist_s in q_artist_s:
                        artist_match = True

                # B. 相似度计算
                combined_s = f"{t_pure_name_s} {t_artist_s}"
                sim_pure = difflib.SequenceMatcher(None, raw_query_s, t_pure_name_s).ratio()
                sim_comb = difflib.SequenceMatcher(None, raw_query_s, combined_s).ratio()
                best_sim = max(sim_pure, sim_comb)

                # C. 全词覆盖检测
                all_covered = all(word in t_all_metadata for word in query_words)

                # D. 评分计算
                score = track.get('popularity', 0) + (best_sim * 100)
                
                # 歌手匹配加权 (大幅提升，确保压过版本分)
                if artist_match:
                    score += 300 
                elif q_artist_s:
                    score -= 100

                # 全词覆盖加权
                if all_covered: score += 200
                
                # 版本偏好分
                res_has_live = any(word in t_raw_name.lower() for word in ['live', '现场'])
                if wants_live:
                    if res_has_live: score += 100
                    else: score -= 50 # 如果要live结果没live，小扣分
                else:
                    if res_has_live: score -= 100 # 不要live结果有live，重扣

                scored_tracks.append({"track": track, "score": score, "sim": best_sim, "covered": all_covered, "artist_match": artist_match})
                print(f"  {idx+1}. [{t_main_artist}] {t_raw_name} | Score:{score:.1f} | Sim:{best_sim:.2f} | Match:{artist_match}")

            # 4. 判定
            scored_tracks.sort(key=lambda x: x['score'], reverse=True)
            best = scored_tracks[0]
            
            # 及格线判定：歌手对上或者是全词覆盖
            if best['artist_match'] or best['covered'] or best['sim'] > 0.75:
                target = best['track']
                print(f"[{self.room_id}]{timestamp()}[SPOT] [选中] {target['name']} - {target['artists'][0]['name']} (分值:{best['score']:.1f})")
                return target
            
            print(f"[{self.room_id}]{timestamp()}[SPOT] [拦截] 最佳匹配匹配度不足")
            return None
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] {e}")
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
        max_retries = 3
        retry_delay = 1  # 重试间隔秒数
        
        for attempt in range(1, max_retries + 1):
            try:
                # 尝试调用 Spotify API
                return self.sp.currently_playing(market='HK') or None
            except Exception as e:
                # 如果是最后一次尝试也失败了
                if attempt == max_retries:
                    print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 获取当前播放信息持续超时，重试 {max_retries} 次均失败: {e}")
                    return None
                
                # 打印重试提示并等待
                print(f"[{self.room_id}]{timestamp()}[SPOT] [WARN] 获取播放信息超时 (第 {attempt} 次)，正在重试...")
                time.sleep(retry_delay)

    async def get_current_playback(self):
        return await asyncio.to_thread(self._get_current_playback)
