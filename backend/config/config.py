# config.py
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """
    从配置文件中加载数据，如果不存在则返回空字典。
    """

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            return config_data
    else:
        return {}
    
def validate_config(config_data):
    """
    验证配置数据的完整性和正确性
    如果配置不完整或不正确，返回 False，否则返回 True
    """

    bilibili_keys = [
        "credential", "song_request_permission", "next_request_permission"
    ]

    for key in bilibili_keys:
        value = config_data.get("bilibili", {}).get(key)
        if value is None or value == "" or value == {}:
            return False

    # Check nested keys in credential
    credential_keys = ["auth_code", "access_key_id", "access_key_secret", "app_id"]
    
    credential = config_data.get("bilibili", {}).get("credential", {})
    for key in credential_keys:
        value = credential.get(key)
        if value is None or value == "":
            return False

    # Check nested keys in song_request_permission
    song_request_permission_keys = ["streamer", "room_admin", "guard", "medal_light", "medal_level"]
    song_request_permission = config_data.get("bilibili", {}).get("song_request_permission", {})
    for key in song_request_permission_keys:
        value = song_request_permission.get(key)
        if value is None or value == "":
            return False

    # Check nested keys in next_request_permission
    next_request_permission_keys = ["streamer", "room_admin", "guard", "medal_light", "medal_level"]
    next_request_permission = config_data.get("bilibili", {}).get("next_request_permission", {})
    for key in next_request_permission_keys:
        value = next_request_permission.get(key)
        if value is None or value == "":
            return False

    spotify_keys = [
        "client_id", "client_secret", "redirect_uri", "scope", "default_playlist"
    ]
    
    for key in spotify_keys:
        value = config_data.get("spotify", {}).get(key)
        if value is None or value == "":
            return False

    return True

def save_config(config_data):
    """
    将传入的配置数据保存到配置文件中
    """

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def create_default_config():
    """
    创建默认配置文件
    """

    default_config = {
        "room_id": "",
        "bilibili": {
            "credential": {
                "access_key_id": "",
                "access_key_secret": "",
                "app_id": "",
                "auth_code": "",
            },
            "song_request_permission": {
                "streamer": True,
                "room_admin": True,
                "guard": True,
                "medal_light": True,
                "medal_level": "1"
            },
            "next_request_permission": {
                "streamer": True,
                "room_admin": True,
                "guard": True,
                "medal_light": False,
                "medal_level": "100"
            }
        },
        "spotify": {
            "client_id": "",
            "client_secret": "",
            "redirect_uri": "http://127.0.0.1:8888/callback",
            "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private",
            "default_playlist": "https://open.spotify.com/playlist/2sOt8rRBaecTxgc7LFidrm?si=80e4759b8eeb43b2"
        }
    }
    
    save_config(default_config)

# Debug-----------------------
def main():
    """
    主函数，用于测试配置加载和保存功能
    """
    create_default_config()  # 创建默认配置文件
    config = load_config()
    print(f"加载的配置: {config}")
    config_status = validate_config(config)
    print(f"{config_status}")

if __name__ == "__main__":
    main()