# Bilibili-Spotilive v1.0.6

[v1.0.6-下载地址](https://github.com/jo4rchy/Bilibili-Spotilive/releases/tag/v1.0.6-Stable)

**点歌机需要Spotify正式会员**

## 点歌机使用说明：
### 使用之前
- 前往[bilibili开放平台](https://open-live.bilibili.com/open-manage)，申请开放平台Access Key ID，secret
- 前往[创建直播app项目](https://open-live.bilibili.com/miniapp/create)，创建并获取App ID

### 配置点歌机
- 第一次运行会自动在exe目录生成一个config.json
- 填入：
  - room_id: 直播间号
  - access_key_id：b站开放平台accesskeyid
  - access_key_secret：b站开放平台accesskeysecret
  - app_id：直播appid
  - auth_code：b站直播身份码
  - spotify client_id：Spotify api client_id
  - spotify client_secret：Spotify api client_secret
 
### 点歌/切歌指令
- 发送 “点歌 歌名” 即可立即点歌
- 发送 “点歌 歌名+歌手” 即可精准匹配歌名歌手点歌
- 发送 “下一首”/“切歌” 即可跳过当前歌曲

### 点歌/切歌权限
- 点歌权限 (song_request_permission)：
  - 主播 (streamer)：默认可以（true），点歌加入最高优先级主播队列
  - 房管 (room_admin)：默认可以（true），点歌加入普通队列
  - 大航海 (guard)：默认可以（true），点歌加入大航海队列
  - 是否点亮灯牌 (medal_light) / 已弃用
  - 灯牌等级 (medal_level)：默认 一级牌子（1）即可点歌，点歌加入普通队列
 
- 切歌权限 (next_request_permission)：
  - 主播 (streamer)：默认可以（true），切一切歌曲
  - 房管 (room_admin)：默认可以（true），切非主播和大航海的一切歌曲
  - 大航海 (guard)：默认可以（true），切非主播和其他大航海的一切歌曲
  - 是否点亮灯牌 (medal_light) / 已弃用
  - 灯牌等级 (medal_level)：默认 一百级牌子（100），切非主播和其他大航海的一切歌曲

### 如何获取spotify api：
- Spotify API
  - 前往[Spotify Developer](https://developer.spotify.com/dashboard) 如图页面创建Spotify 的API
  - Redirect Url填写 `http://127.0.0.1:8888/callback`,api和sdk不需要勾选
  - 创建好后可以获得Spotify 的client ID和secret 

![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/spotify_api.png)

## 前端使用说明：
- 控制面板地址：http://localhost:5001/app/
- OBS添加浏览器采集-正在播放小组件：http://localhost:5001/nowplaying_widget/ 
- OBS添加浏览器采集-点歌队列小组件：http://localhost:5001/queue_widget/

| 弹幕点歌历史 | 歌曲快速搜索 | 队列快速修改 |
| - | - | - |
| ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/frontend-0.png) | ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/frontend-1.png) | ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/frontend-2.png) |

## 点歌机后端
- 在原有的基础上优化点歌逻辑
- 开放API端点，允许前端调用并控制点歌机
- 停止使用bilibili-api库
- 使用blivedm库，通过身份码链接bilibili open live获取直播间信息

## 点歌机前端
- 使用 React + Vite + Electron 构建前端图形界面
- 现代化简洁UI，高效控制点歌机
- 实时展示历史弹幕和历史点歌机请求，方便主播抓是谁在点整活歌
- 添加快速搜索页面，一键添加到指定队列，或一键立即播放想听的歌曲
- 快速删除队列中不合适的点歌
- 浅色/深色模式可用
- 使用5173端口
