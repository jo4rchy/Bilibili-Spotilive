from typing import Optional
from handler.queue_manager import song_queue, song_queue_streamer, song_queue_guard

def create_message_message(message, result, track: Optional[dict] = None):
    """创建一个消息字典"""
    return {
            "message": message,
            "result": result,
            "albumCover": track.get('album',{}).get('images',[{}])[0].get('url','') if track else './images/Spotify.png'
        }

async def create_queue_message():
    """
    按照优先级创建一个完整的点歌队列
    顺序：streamer -> guard -> normal
    queue_item 结构:
        {
            "song": {...},           # Spotify 返回的 track dict
            "request": {             # parse_request 返回的那个 dict
                "user": {...},
                "request": {...}
        }
        }
    """
    streamer_queue = await song_queue_streamer.list_songs()
    guard_queue = await song_queue_guard.list_songs()
    normal_queue = await song_queue.list_songs()

    combined = streamer_queue + guard_queue + normal_queue

    playlist_data = [{
        "name": f"{item['song'].get('name','未知歌曲')} - {item['song'].get('artists',[{'name':'未知'}])[0]['name']}",
        "albumCover": item['song'].get('album',{}).get('images',[{}])[0].get('url',''),
        "request": item.get('request', {})
    } for item in combined]

    return playlist_data




