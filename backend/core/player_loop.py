import asyncio
import time
from utils.log_timer import timestamp
from handler.queue_manager import song_queue, song_queue_guard, song_queue_streamer, print_queue_states
from apis.obs_widget import create_message_message, create_queue_message
from apis.api_server import emit_message, emit_queue, clear_queue, emit_request
from typing import Optional, Dict

spotify_ctrl = None
current_request: Optional[Dict] = None
_last_print_log_time = 0.0

def set_player_spotify_controller(controller):
    global spotify_ctrl
    spotify_ctrl = controller

# Emit functions ------------------------------------------------------------
async def emit_message_to_widget(message_data):
    emit_message(message_data)

async def emit_queue_to_widget(playlist_data):
    emit_queue(playlist_data)

async def emit_request_to_electron(message: Dict):
    emit_request(message)

async def _emit_simple(text: str, subtext: str = "", song: Optional[Dict] = None):
    msg = create_message_message(text, subtext, song)
    await emit_message_to_widget(msg)

async def _emit_queue_status():
    global _last_print_log_time
    queue_msg = await create_queue_message()

    if queue_msg:
        await emit_queue_to_widget(queue_msg)
    else:
        guide_msg = create_message_message("点歌队列空", "点歌发送：点歌 歌名(+歌手)")
        clear_queue()
        await emit_message_to_widget(guide_msg)

    # now = time.time()
    # if now - _last_print_log_time > 3.0:  # 设置 3 秒冷却，可根据需求调整
    #     await print_queue_states()
    #     _last_print_log_time = now

async def _feedback_and_update(text: str, subtext: str = "", song: Optional[Dict] = None, delay: float = 3.0):
    await _emit_simple(text, subtext, song)
    await asyncio.sleep(delay)
    await _emit_queue_status()

# Emit functions ------------------------------------------------------------

async def get_next_item() -> Optional[Dict]:
    for queue in (song_queue_streamer, song_queue_guard, song_queue):
        if not queue.is_empty():
            return await queue.get_next_song()
    return None

async def _play_song_item(item: Dict, room_id: str = ""):
    global current_request
    current_request = item
    song = item["song"]
    user = item["request"]["user"]
    await spotify_ctrl.play_song(song)
    await _emit_queue_status()

async def player_loop(room_id: str):
    global current_request
    if spotify_ctrl is None:
        raise RuntimeError("请先调用 set_player_spotify_controller() 注入控制器")

    while True:
        try:
            status = await spotify_ctrl.get_current_playback()
            is_playing = bool(status and status.get("is_playing"))

            if not is_playing and current_request is None:
                pass
            elif not is_playing and current_request is not None:
                current_request = None
                next_item = await get_next_item()
                if next_item:
                    await _play_song_item(next_item, room_id)
                else:
                    await spotify_ctrl.restore_default_playlist()
                    await _emit_queue_status()
            
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[{room_id}]{timestamp()} LOOP 错误：{e}")
            await asyncio.sleep(2)

async def play_next_song() -> bool:
    global current_request
    if spotify_ctrl is None:
        raise RuntimeError("play_next_song: spotify_ctrl 未设置")

    next_item = await get_next_item()
    if next_item:
        song = next_item["song"]
        user = next_item["request"]["user"]
        await _feedback_and_update(
            f"切歌成功",
            f"即将播放: {song.get('name', '')} - {song.get('artists', [{}])[0].get('name', '')}",
            song
        )
        await _play_song_item(next_item)
    else:
        current_request = None
        await _feedback_and_update(
            "切歌成功",
            "点歌列表空，播放默认歌单"
        )
        await spotify_ctrl.restore_default_playlist()
    return True

async def next_song(request: Dict, next_perm: bool) -> bool:
    global current_request
    user = request["user"]

    if current_request is None:
        if next_perm:
            success_message = {
                "user": f"请求者: {user.get('uname', '未知用户')}",
                "face": user.get("face", None),
                "message": "切歌成功: 下一首"
            }
            await emit_request_to_electron(success_message)
            return await play_next_song()

        else:
            failure_message = {
                "user": f"请求者: {user.get('uname', '未知用户')}",
                "face": user.get("face", None),
                "message": "切歌失败: 权限不足"
            }
            await emit_request_to_electron(failure_message)
            await _feedback_and_update("切歌权限不足", "切歌失败")
            return False

    requester = current_request["request"]["user"]
    has_perm = (
        user["uid"] == requester["uid"]
        or user.get("is_streamer")
        or (
            user.get("privilege_type", 0) > 0
            and not requester.get("is_streamer")
            and requester.get("privilege_type", 0) == 0
        )
    )
    if has_perm:
        success_message = {
            "user": f"请求者: {user.get('uname', '未知用户')}",
            "face": user.get("face", None),
            "message": "下一首成功: 下一首",
        }
        await emit_request_to_electron(success_message)
        return await play_next_song()

    if requester.get("privilege_type", 0) > 0:
        failure_message = {
            "user": f"请求者: {user.get('uname', '未知用户')}",
            "face": user.get("face", None),
            "message": "下一首失败: 当前其他大航海点歌"
        }
        await emit_request_to_electron(failure_message)
        await _feedback_and_update("无法跳过其他大航海点歌", "切歌失败")
        return False
    elif requester.get("is_streamer"):
        failure_message = {
            "user": f"请求者: {user.get('uname', '未知用户')}",
            "face": user.get("face", None),
            "message": "下一首失败: 当前主播点歌"
        }
        await emit_request_to_electron(failure_message)
        await _feedback_and_update("无法跳过主播点歌", "切歌失败")
        return False
    else:
        failure_message = {
            "user": f"请求者: {user.get('uname', '未知用户')}",
            "face": user.get("face", None),
            "message": "下一首失败: 非本人点歌"
        }
        await emit_request_to_electron(failure_message)
        await _feedback_and_update("无法跳过非本人点歌", "切歌失败")
        return False

async def request_song(request: Dict, request_perm: bool) -> bool:
    global current_request
    user = request["user"]
    keyword = request.get("request", {}).get("keyword", "")

    if not request_perm:
        failure_message = {
            "user": f"请求者: {user.get('uname', '未知用户')}",
            "face": user.get("face", None),
            "message": "点歌失败: 权限不足"
        }
        await emit_request_to_electron(failure_message)
        await _feedback_and_update("点歌失败", "权限不足，点亮灯牌即可点歌")
        return False

    try:
        song = await spotify_ctrl.search_song(keyword)
        if not song:
            failure_message = {
                "user": f"请求者: {user.get('uname', '未知用户')}",
                "face": user.get("face", None),
                "message": f"点歌失败: 未找到 {keyword}",
            }
            await emit_request_to_electron(failure_message)
            await _feedback_and_update("点歌失败", "未找到匹配的歌曲")
            return False

        artist = song.get("artists", [{}])[0].get("name", "")
        text = f"点歌成功: {song.get('name', 'Unknown')} - {artist}"

        # if request.get("request", {}).get("start_ms") is not None:
        #     start_ms = request["request"]["start_ms"]
        #     spotify_ctrl._play_song(song, start_ms=start_ms)
        #     return True

        if current_request is None:
            success_message = {
                "user": f"请求者: {user.get('uname', '未知用户')}",
                "face": song.get("album", {}).get("images", [{}])[0].get("url", None),
                "message": f"点歌: {song.get('name', '')} - {song.get('artists', [{}])[0].get('name', '')}"
            }
            await emit_request_to_electron(success_message)
            await _feedback_and_update(text, "立即播放", song)
            await _play_song_item({"song": song, "request": request})
        else:
            success_message = {
                "user": f"请求者: {user.get('uname', '未知用户')}",
                "face": song.get("album", {}).get("images", [{}])[0].get("url", None),
                "message": f"点歌: {song.get('name', '')} - {song.get('artists', [{}])[0].get('name', '')}"
            }
            await emit_request_to_electron(success_message)

            queue_item = {"song": song, "request": request}
            if user.get("is_streamer"):
                await song_queue_streamer.add_song(queue_item)
                btn = "加入主播队列"
            elif user.get("privilege_type", 0) > 0:
                await song_queue_guard.add_song(queue_item)
                btn = "加入大航海队列"
            else:
                await song_queue.add_song(queue_item)
                btn = "加入普通队列"
            await _feedback_and_update(text, btn, song)
        return True
    except Exception as e:
        await _feedback_and_update("点歌失败", f"搜索错误: {e}")
        return False


#for frontend calls ------------------------------------------------------------
async def request_song_frontend(song: Dict, queue: str) -> bool:
    """
    前端调用的点歌接口
    :param song: 歌曲信息字典
    :return: True=点歌成功；False=点歌失败
    """
    global current_request
    if spotify_ctrl is None:
        raise RuntimeError("request_song_frontend: spotify_ctrl 未设置")
    
    request = {
        "user": {
            "uname": "主播",
            "uid": "主播",
            "face": None,
            "is_streamer": 1,
            "admin": 1,
            "medal_is_light": 1,
            "medal_level": 100,
            "privilege_type": 0,
        },
        "request": {
            "type": "song",
            "keyword": song.get("name", "")
        }
    }

    success_message = {
        "user": f"请求者: {request['user'].get('uname', '未知用户')}",
        "face": song.get("album", {}).get("images", [{}])[0].get("url", None),
        "message": f"点歌: {song.get('name', '')} - {song.get('artists', [{}])[0].get('name', '')}"
    }
    await emit_request_to_electron(success_message)

    queue_item = {"song": song, "request": request}

    if current_request is None:
        current_request = queue_item
        await _play_song_item(queue_item)
        print(f"前端点歌 → {song.get('name')} (立即播放)")
    else:
        if queue == "streamer":
            await song_queue_streamer.add_song(queue_item)
        elif queue == "guard":
            await song_queue_guard.add_song(queue_item)
        elif queue == "normal":
            await song_queue.add_song(queue_item)

        print(f"前端点歌 → {song.get('name')} (队列: {queue})")
        await _emit_queue_status()
    
    return True

async def play_song_frontend(song: Dict) -> bool:
    """
    前端调用的播放歌曲接口
    :param song: 歌曲信息字典
    :return: True=播放成功；False=播放失败
    """
    global current_request
    if spotify_ctrl is None:
        raise RuntimeError("play_song_frontend: spotify_ctrl 未设置")
    
    request = {
        "user": {
            "uname": "主播",
            "uid": "主播",
            "face": None,
            "is_streamer": 1,
            "admin": 1,
            "medal_is_light": 1,
            "medal_level": 100,
            "privilege_type": 0,
        },
        "request": {
            "type": "song",
            "keyword": song.get("name", "")
        }
    }

    success_message = {
        "user": f"请求者: {request['user'].get('uname', '未知用户')}",
        "face": song.get("album", {}).get("images", [{}])[0].get("url", None),
        "message": f"立即播放: {song.get('name', '')} - {song.get('artists', [{}])[0].get('name', '')}"
    }
    await emit_request_to_electron(success_message)

    item = {"song": song, "request": request}
    current_request = item

    await _play_song_item({"song": song, "request": request})
    await _emit_queue_status()
    return True

async def delete_song_frontend(queue: str, index: int) -> bool:
    """
    前端调用的删除歌曲接口
    :param song: 歌曲信息字典
    :return: True=删除成功；False=删除失败
    """
    print(f"前端删除歌曲 → 队列: {queue}, 索引: {index}")
    if queue == "streamer":
        await song_queue_streamer.remove_at(index)
    elif queue == "guard":
        await song_queue_guard.remove_at(index)
    elif queue == "normal":
        await song_queue.remove_at(index)

    await _emit_queue_status()
    return True

async def reorder_song_frontend(queue: str, new_order: list) -> bool:
    """
    前端调用的重新排序歌曲接口
    :param queue: 队列类型
    :param new_order: 新的歌曲顺序列表
    :return: True=排序成功；False=排序失败
    """
    print(f"前端重新排序 → 队列: {queue}, 新顺序: {new_order}")
    if queue == "streamer":
        await song_queue_streamer.reorder(new_order)
    elif queue == "guard":
        await song_queue_guard.reorder(new_order)
    elif queue == "normal":
        await song_queue.reorder(new_order)

    await _emit_queue_status()
    return True

async def reorder_queue_frontend(queue: str, new_order: list) -> bool:
    """
    前端调用的重新排序队列接口
    :param queue: 队列类型
    :param new_order: 新的队列顺序列表
    :return: True=排序成功；False=排序失败
    """ 
    print(f"前端重新排序 → 队列: {queue}, 新顺序: {new_order}")
    if queue == "streamer":
        await song_queue_streamer.reorder_queue(new_order)
    elif queue == "guard":
        await song_queue_guard.reorder_queue(new_order)
    elif queue == "normal":
        await song_queue.reorder_queue(new_order)

    await _emit_queue_status()
    return True