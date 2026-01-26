import asyncio
from utils.log_timer import timestamp

class SongQueue:
    def __init__(self):
        # 使用 asyncio.Queue 实现异步队列
        self._queue = asyncio.Queue()

    async def add_song(self, queue_item: dict) -> None:
        """
        将一个 queue_item 添加到队列中。

        queue_item 格式:
        {
            "song": {...},          # Spotify track dict
            "request": {
                "user": {...},      # 你的 parse_request 里的 user 字段
                "request": {...}    # type/keyword
            }
        }
        """
        await self._queue.put(queue_item)

        song = queue_item["song"]
        user = queue_item["request"]["user"]

        # 根据 user 字段推断队列角色
        if user.get("is_streamer", 0) == 1:
            role = "streamer"
        elif user.get("privilege_type", 0) > 0:
            role = "guard"
        else:
            role = "normal"

        # 打日志
        name = song.get("name", "Unknown")
        artists = ", ".join(a.get("name", "") for a in song.get("artists", []))
        info = f"{name} - {artists}" if artists else name
        print(f"[{self.__class__.__name__}]{timestamp()}[队列] 点歌成功，加入{role}队列：'{info}'")

    async def remove_at(self, index: int) -> bool:
        """
        删除指定索引的 queue_item。
        返回 True 表示删除成功，False 表示索引无效。
        """
        if index < 0 or index >= self._queue.qsize():
            print(f"[{self.__class__.__name__}]{timestamp()}[队列] 删除失败，索引 {index} 无效。")
            return False

        temp_queue = asyncio.Queue()
        removed = False

        for i in range(self._queue.qsize()):
            item = await self._queue.get()
            if i == index:
                removed = True
                # 打日志
                song = item.get("song", {})
                name = song.get("name", "Unknown")
                artists = ", ".join(a.get("name", "") for a in song.get("artists", []))
                info = f"{name} - {artists}" if artists else name
                print(f"[{self.__class__.__name__}]{timestamp()}[队列] 已删除队列中第 {index} 首歌曲：'{info}'")
                continue
            await temp_queue.put(item)

        # 还原队列
        self._queue = temp_queue
        return removed

    async def get_next_song(self) -> dict:
        """
        从队列中取出并返回下一个 queue_item。
        返回 None 表示队列空。
        """
        if self._queue.empty():
            return None
        queue_item = await self._queue.get()
        return queue_item
    
    async def reorder_queue(self, new_order: list) -> bool:
        """
        重新排序队列。
        new_order 是一个索引列表，表示新的顺序。
        返回 True 表示排序成功，False 表示失败（如索引无效）。
        """
        if not isinstance(new_order, list):
            print(f"[{self.__class__.__name__}]{timestamp()}[队列] 重新排序失败，参数不是列表。")
            return False

        temp_queue = asyncio.Queue()
        for item in new_order:
            await temp_queue.put(item)
        self._queue = temp_queue
        print(f"[{self.__class__.__name__}]{timestamp()}[队列] 重新排序成功。")
        return True

    def is_empty(self) -> bool:
        """
        True 表示队列空
        """
        return self._queue.empty()

    def qsize(self) -> int:
        """
        队列长度
        """
        return self._queue.qsize()

    async def list_songs(self) -> list:
        """
        返回当前所有待播 queue_item 列表，仅供调试。
        """
        return list(self._queue._queue)

    def clear(self) -> None:
        """
        清空队列
        """
        while not self._queue.empty():
            self._queue.get_nowait()
        print(f"[{self.__class__.__name__}]{timestamp()}[队列] 已清空所有待播歌曲。")
