from core.song_queue import SongQueue
from utils.log_timer import timestamp

song_queue = SongQueue()
song_queue_guard = SongQueue()
song_queue_streamer = SongQueue()

async def print_queue_states():
    """打印当前各队列状态"""
    print(f"\n[SongQueue]{timestamp()} ======= 当前全站队列概览 =======")
    
    # 定义队列与标签的对应关系
    queues = [
        ("主播队列", song_queue_streamer),
        ("守护队列", song_queue_guard),
        ("普通队列", song_queue)
    ]
    
    for label, q in queues:
        size = q.qsize()
        if size == 0:
            print(f"[SongQueue]{timestamp()} {label}: (空)")
        else:
            # 访问 asyncio.Queue 内部的 deque (非阻塞获取快照)
            items = list(q._queue._queue)
            print(f"[SongQueue]{timestamp()} {label} ({size}首):")
            for idx, item in enumerate(items):
                song = item.get("song", {})
                name = song.get("name", "未知歌名")
                artist = ", ".join(a.get("name", "") for a in song.get("artists", []))
                user_name = item.get("request", {}).get("user", {}).get("uname", "匿名")
                print(f"    └─ [{idx}] {name} - {artist} (点歌人: {user_name})")
    
    print(f"[SongQueue]{timestamp()} ===================================\n")