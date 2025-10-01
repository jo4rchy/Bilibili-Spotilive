# New-Bilibili-Spotilive v1.0.0 Pre-Release
当前为预览版，轻度测试后无显著bug

**点歌机需要Spotify正式会员**

下载：[New-Bilibili-Spotilive v1.0.0 Pre-Release](https://github.com/jo4rchy/Bilibili-Spotilive/releases/tag/r-v1.0.0)

## 点歌机后端
- 在原有的基础上优化点歌逻辑
- 开放API端点，允许前端调用并控制点歌机
- 旧版本config无痛转移到新版本使用
- 独立于前端运行
- 使用5001端口

## 点歌机前端
- 使用 React + Vite + Electron 构建前端图形界面
- 现代化简洁UI，高效控制点歌机
- 实时展示历史弹幕和历史点歌机请求，方便主播抓是谁在点整活歌
- 添加快速搜索页面，一键添加到指定队列，或一键立即播放想听的歌曲
- 快速删除队列中不合适的点歌
- 浅色/深色模式可用
- 使用5173端口

| 弹幕点歌历史 | 歌曲快速搜索 | 队列快速修改 |
| - | - | - |
| ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/frontend-0.png) | ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/frontend-1.png) | ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/frontend-2.png) |

## 如何使用点歌机
- 下载 [New-Bilibili-Spotilive v1.0.0 Pre-Release](https://github.com/jo4rchy/Bilibili-Spotilive/releases/tag/r-v1.0.0)
- 解压缩后有两个 exe 文件

后端使用说明：
- 复制你原本的config文件到解压目录，或者运行一次 `BiliBili-Spotilive-Backend-v1.0.0.exe` 会自动创建新的config文件
- 直接运行 `BiliBili-Spotilive-Backend-v1.0.0.exe` 即可开启弹幕点歌监听

| B站cookies获取 | Spotify API 密钥获取 |
| - | - |
| ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/bilibili_cookies.png) | ![](https://github.com/jo4rchy/Bilibili-Spotilive/blob/main/resources/spotify_api.png) |

前端使用说明：
- 运行 `BiliBili-Spotilive-Frontend-Setup-1.0.0.exe` 会自动安装前端，并在桌面创建快捷方式
- 双击桌面的 `Bilibili Spotilive` 即可开启点歌机前端控制

其他说明：
- 后端独立运行，不开启前端也可以和老版本一样处理点歌请求
- 前端运行前必须先运行后端，不然无法请求
- OBS中nowplaying和队列展示请下载 [Now_Playing](https://github.com/jo4rchy/Bilibili-Spotilive/tree/main/backend/static/nowplaying_widget) 和 [Queue(队列)](https://github.com/jo4rchy/Bilibili-Spotilive/tree/main/backend/static/queue_widget) ，将对应 `index.html` 作为静态文件让OBS读取即可，会自动监听点歌机发送的更新

## 注意，此版本为测试版
稳定版本：
- [下载Bilibili-Spotilive v3.1.0 Stable Release](https://github.com/jo4rchy/Bilibili-Spotilive/releases/tag/v3.1.0-Stable)
- [教程](https://github.com/jo4rchy/Bilibili-Spotilive/tree/legacy)
