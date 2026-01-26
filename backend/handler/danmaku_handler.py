from handler.request_handler import parse_request, request_song_handler, request_next_handler
from apis.api_server import emit_danmaku

async def handle_danmaku(danmaku, room_id=None, streamer_open_id=None):
    """处理弹幕消息的主入口"""

    parsed_danmaku = parse_danmaku(danmaku)
    emit_danmaku(parsed_danmaku)

    is_streamer = int(danmaku.open_id == streamer_open_id)
    request = parse_request(danmaku, is_streamer=is_streamer)
    if not request:
        return
    else:
        if request['request']['type'] == 'song':
            await request_song_handler(request)
        elif request['request']['type'] == 'next':
            await request_next_handler(request)

def parse_danmaku(danmaku):
    """解析弹幕数据"""

    return {
        'uname': danmaku.uname,
        'uid': danmaku.open_id,
        'face': danmaku.uface,
        'msg': danmaku.msg,
        'medal_level': danmaku.fans_medal_level,
        'medal_name': danmaku.fans_medal_name,
        'medal_is_light': danmaku.fans_medal_level > 0,
        'privilege_type': danmaku.guard_level,
        'timestamp': danmaku.timestamp,
    }

async def handle_enter_room(roomenter, room_id=None, streamer_open_id=None):
    """处理进入房间消息的主入口"""
    parsed_enter_room = parse_enter_room(roomenter)
    # print(f"处理进入房间点歌: {parsed_enter_room}")

    is_streamer = int(roomenter.open_id == streamer_open_id)

    request = {
                "user": {
                    "uname": parsed_enter_room.get("uname"),
                    "uid": parsed_enter_room.get("uid"),
                    "face": parsed_enter_room.get("face", None),
                    "is_streamer": is_streamer,
                    "admin": parsed_enter_room.get("is_admin", 0),
                    "medal_is_light": parsed_enter_room.get("medal_level", 0) > 0,
                    "medal_level": parsed_enter_room.get("medal_level", 0),
                    "privilege_type": parsed_enter_room.get("privilege_type", 0),
                },
                "request": {
                    "type": "song",
                    "keyword": "大东北我的家乡 DJ版",
                    "start_ms": 65500
                }
            }
    # print(f"构造进入房间点歌请求: {request}")

    await request_song_handler(request)

def parse_enter_room(roomenter):
    """解析进入房间数据"""

    return {
        'uname': roomenter.uname,
        'uid': roomenter.open_id,
        'face': roomenter.uface,
        'medal_level': 1,
        'medal_name': None,
        'medal_is_light': 0,
        'privilege_type': 0,
        'timestamp': roomenter.timestamp,
        'is_admin': 0,
    }