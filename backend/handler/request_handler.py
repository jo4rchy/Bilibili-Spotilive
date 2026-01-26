from typing import Optional, Dict
from core.player_loop import next_song, request_song

spotify_controller = None
perm_handler = None

def set_request_spotify_controller(controller):
    global spotify_controller
    spotify_controller = controller

def set_permission_handler(handler):
    global perm_handler
    perm_handler = handler

def is_song_request(text: str) -> bool:
    return text.strip().startswith("点歌")

def is_next_song_request(text: str) -> bool:
    return text.strip() == "下一首" or text.strip() == "切歌"

def parse_request(danmaku, is_streamer: int) -> Optional[Dict]:
    """
    统一解析弹幕命令，返回标准结构:
    {
        "type": "song",    # 或 "next"
        "keyword": "歌名关键词",  # 如果是 song 请求
    }
    """
    text = danmaku.msg.strip()
    is_streamer = is_streamer

    if is_song_request(text):
        keyword = text[2:].strip()
        if keyword:
            return {
                "user": {
                    "uname": getattr(danmaku, "uname"),
                    "uid": getattr(danmaku, "open_id"),
                    "face": getattr(danmaku, "uface", None),
                    "is_streamer": is_streamer,
                    "admin": getattr(danmaku, "is_admin"),
                    "medal_is_light": getattr(danmaku, "fans_medal_level", 0) > 0,
                    "medal_level": getattr(danmaku, "fans_medal_level", 0),
                    "privilege_type": getattr(danmaku, "guard_level", 0),
                },
                "request": {
                    "type": "song",
                    "keyword": keyword,
                }
            }

    elif is_next_song_request(text):
        return {
            "user": {
                "uname": getattr(danmaku, "uname"),
                "uid": getattr(danmaku, "open_id"),
                "face": getattr(danmaku, "uface", None),
                "is_streamer": is_streamer,
                "admin": getattr(danmaku, "is_admin"),
                "medal_is_light": getattr(danmaku, "fans_medal_level", 0) > 0,
                "medal_level": getattr(danmaku, "fans_medal_level", 0),
                "privilege_type": getattr(danmaku, "guard_level", 0),
            },
            "request": {
                "type": "next"
            }
        }

    return None

async def request_song_handler(request):
    """
    从请求中提取歌曲关键词并搜索歌曲
    :param request: 请求字典
    :return: 歌曲信息或 None
    """
    request_perm = perm_handler.is_allowed(request)
    return await request_song(request, request_perm)


async def request_next_handler(request):
    """
    处理下一首歌曲请求
    :param request: 请求字典
    :return: True=已发起切歌/恢复默认；False=权限不足
    """
    next_perm = perm_handler.is_allowed(request)
    return await next_song(request, next_perm)