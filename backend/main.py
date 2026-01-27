# -*- coding: utf-8 -*-
import asyncio
import threading

import blivedm
import blivedm.models.open_live as open_models

from config.config import load_config, create_default_config, validate_config
from apis.api_server import set_api_spotify_controller, start_api_server
from core.spotify_controller import SpotifyController
from handler.danmaku_handler import handle_danmaku
from core.player_loop import set_player_spotify_controller, player_loop
from handler.permission_handler import PermissionHandler
from handler.request_handler import set_request_spotify_controller, set_permission_handler
from utils.log_timer import timestamp

# ACCESS_KEY_ID, ACCESS_KEY_SECRET需要去 B 站开放平台申请
# https://open-live.bilibili.com/open-manage
# ACCESS_KEY_ID 和 ACCESS_KEY_SECRET 请妥善保管，避免泄露
# APP_ID 需要创建应用后获取
# ROOM_OWNER_AUTH_CODE 是主播身份码

ACCESS_KEY_ID = ''
ACCESS_KEY_SECRET = ''
APP_ID = '' 
ROOM_OWNER_AUTH_CODE = ''

bilibili_client = None
room_id = None
spotify_ctrl = None
perm_handler = None

def start_api():
    t = threading.Thread(target=start_api_server, daemon=True)
    t.start()

async def run_bilibili_client():
    """专门负责管理 blivedm 生命周期的函数"""
    global bilibili_client, room_id, spotify_ctrl
    try:
        bilibili_client.start()
        await bilibili_client.join()
    finally:
        await bilibili_client.stop_and_close()

async def main():
    global bilibili_client , room_id, spotify_ctrl, perm_handler

    print("-----------------------------------")
    print("欢迎使用 Bili-Spotilive！")
    print("当前版本：1.0.6")
    print("仓库地址：https://github.com/jo4rchy/Bilibili-Spotilive")
    print("-----------------------------------")

    config = load_config()

    if not config:
        print(f"{timestamp()}[config] 配置文件加载失败，正在创建默认配置...")
        create_default_config()
        config = load_config()
        print(f"{timestamp()}[config] 默认配置文件已创建，请根据进行配置后重新运行程序。")
        print(f"{timestamp()}[config] 前往 https://open-live.bilibili.com/open-manage 申请Access Key ID，Access Key Secret，App ID。")
        print(f"{timestamp()}[config] 程序将在10秒后退出...")
        await asyncio.sleep(10)
        return
    
    config_valid = validate_config(config)
    if not config_valid:
        print(f"{timestamp()}[config] 配置文件验证失败，请检查配置文件中的必填项是否已正确填写。")
        print(f"{timestamp()}[config] 前往 https://open-live.bilibili.com/open-manage 申请Access Key ID，Access Key Secret，App ID。")
        print(f"{timestamp()}[config] 程序将在10秒后退出...")
        await asyncio.sleep(10)
        return
    print(f"{timestamp()}[config] 配置文件加载并验证通过。")
    
    ACCESS_KEY_ID = config["bilibili"]["credential"]["access_key_id"]
    ACCESS_KEY_SECRET = config["bilibili"]["credential"]["access_key_secret"]
    APP_ID = config["bilibili"]["credential"]["app_id"]
    ROOM_OWNER_AUTH_CODE = config["bilibili"]["credential"]["auth_code"]

    bilibili_client = blivedm.OpenLiveClient(
        access_key_id=ACCESS_KEY_ID,
        access_key_secret=ACCESS_KEY_SECRET,
        app_id=APP_ID,
        room_owner_auth_code=ROOM_OWNER_AUTH_CODE,
    )
    handler = MyHandler()
    bilibili_client.set_handler(handler)

    perm_handler = PermissionHandler(config)
    set_permission_handler(perm_handler)

    spotify_ctrl = SpotifyController(config)
    set_api_spotify_controller(spotify_ctrl)
    set_player_spotify_controller(spotify_ctrl)
    set_request_spotify_controller(spotify_ctrl)

    start_api()

    await asyncio.sleep(1)

    print("-----------------------------------")
    print("控制面板地址：http://localhost:5001/app/")
    print("正在播放地址：http://localhost:5001/nowplaying_widget/")
    print("点歌队列地址：http://localhost:5001/queue_widget/")
    print("-----------------------------------")

    try:
        await asyncio.gather(
            run_bilibili_client(),
            player_loop(room_id=room_id),
        )
    except Exception as e:
        print(f"系统运行中发生异常: {e}")


class MyHandler(blivedm.BaseHandler):
    # def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
    #     print(f'[{client.room_id}] 心跳')
    #     print(f'[{client.room_id}] 主播uid {client.room_owner_uid}')

    def _on_open_live_danmaku(self, client: blivedm.OpenLiveClient, message: open_models.DanmakuMessage):
        print("-----------------------------------")
        if message.open_id == client.room_owner_open_id:
            print(f'[{message.room_id}]{timestamp()}[弹幕] [主播] {message.uname}({message.fans_medal_level})：{message.msg}')
        elif message.is_admin == 1:
            print(f'[{message.room_id}]{timestamp()}[弹幕] [房管] {message.uname}({message.fans_medal_level})：{message.msg}')
        else:
            print(f'[{message.room_id}]{timestamp()}[弹幕] [观众] {message.uname}({message.fans_medal_level})：{message.msg}')
        asyncio.create_task(self.async_handle_danmaku(client, message))

    async def async_handle_danmaku(self, client, message):
        try:
            await handle_danmaku(message, client.room_id, client.room_owner_open_id)
        except Exception as e:
            print(f"处理弹幕任务时崩溃: {e}")

    def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):
        print("-----------------------------------")
        print(f'[{message.room_id}]{timestamp()}[上舰] {message.user_info.uname} 购买 大航海等级={message.guard_level}')

    def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):
        print("-----------------------------------")
        coin_type = '金瓜子' if message.paid else '银瓜子'
        total_coin = message.price * message.gift_num
        print(f'[{message.room_id}]{timestamp()}[礼物] {message.uname} 赠送{message.gift_name}x{message.gift_num}'
              f' （{coin_type}x{total_coin}）')

    def _on_open_live_super_chat(self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage):
        print("-----------------------------------")
        print(f'[{message.room_id}]{timestamp()}[醒目留言] ¥{message.rmb} {message.uname}：{message.message}')

    # 进房欢迎，自动放歌，开发中。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。
    # def _on_open_live_enter_room(self, client: blivedm.OpenLiveClient, message: open_models.RoomEnterMessage):
    #     print("-----------------------------------")
    #     print(f'[{message.room_id}]{timestamp()}[进房] {message.uname} 进入房间')
    #     if message.open_id == client.room_owner_open_id:
    #         asyncio.create_task(self.async_handle_room_enter_song(client, message))

    # async def async_handle_room_enter_song(self, client, message):
    #     try:
    #         await handle_enter_room(message, client.room_id, client.room_owner_open_id)
    #     except Exception as e:
    #         print(f"处理进入房间任务时崩溃: {e}")
    # 进房欢迎，自动放歌，开发中。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。



    # def _on_open_live_super_chat_delete(self, client: blivedm.OpenLiveClient, message: open_models.SuperChatDeleteMessage):
    #     print(f'[{message.room_id}] 删除醒目留言 message_ids={message.message_ids}')

    # def _on_open_live_like(self, client: blivedm.OpenLiveClient, message: open_models.LikeMessage):
    #     print(f'[{message.room_id}] {message.uname} 点赞')

    # def _on_open_live_start_live(self, client: blivedm.OpenLiveClient, message: open_models.LiveStartMessage):
    #     print(f'[{message.room_id}] 开始直播')

    # def _on_open_live_end_live(self, client: blivedm.OpenLiveClient, message: open_models.LiveEndMessage):
    #     print(f'[{message.room_id}] 结束直播')

if __name__ == '__main__':
    asyncio.run(main())
