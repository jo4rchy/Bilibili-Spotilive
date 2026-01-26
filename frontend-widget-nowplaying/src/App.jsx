import { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import './assets/index.css';
import './assets/Rainbow.css';

const socket = io('http://localhost:5001'); // 根据你的后端端口调整

const styles = `
@keyframes moveBlob {
  0% { 
    transform: translate(0, 0) scale(1) rotate(0deg);
    border-radius: 24% 76% 35% 65% / 27% 36% 64% 73%;
  }
  33% { 
    transform: translate(200px, -150px) scale(1.4) rotate(120deg);
    border-radius: 76% 24% 33% 67% / 68% 55% 45% 32%;
  }
  66% { 
    transform: translate(-180px, 150px) scale(0.8) rotate(240deg);
    border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%;
  }
  100% { 
    transform: translate(0, 0) scale(1) rotate(360deg);
    border-radius: 24% 76% 35% 65% / 27% 36% 64% 73%;
  }
}

/* 注意：这里去掉了 overflow 和 border-radius，这些交给外层包裹容器处理 */
.apple-bg-container {
  position: absolute;
  top: -150px; left: -150px; right: -150px; bottom: -150px; 
  /* z-index 不需要在这里设了，外层会处理 */
}

.apple-blob {
  position: absolute;
  filter: blur(80px);
  opacity: 0.65;
  animation-name: moveBlob;
  animation-iteration-count: infinite;
  animation-timing-function: cubic-bezier(0.45, 0.05, 0.55, 0.95);
  transition: background 2.5s ease-in-out, opacity 2.5s ease-in-out;
  will-change: transform, background;
}
`;

export default function App() {
  const [playback, setPlayback] = useState(null);
  const [theme, setTheme] = useState({
    background: '#111',
    titleColor: '#fff',
    artistColor: '#ccc',
    bgColors: ['#444', '#333', '#222'] 
  });

  const imgRef = useRef();

  const hexToRgba = (hex, alpha) => {
    if (!hex || !/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
      return `rgba(0, 0, 0, ${alpha})`;
    }
    let c = hex.substring(1).split('');
    if (c.length === 3) {
      c = [c[0], c[0], c[1], c[1], c[2], c[2]];
    }
    c = '0x' + c.join('');
    return `rgba(${[(c >> 16) & 255, (c >> 8) & 255, c & 255].join(',')}, ${alpha})`;
  };

  // Socket 连接
  useEffect(() => {
    socket.on('connect', () => {
      console.log('[Socket] 已连接');
    });

    socket.on('nowplaying_update', (data) => {
      setPlayback(data);
    });

    socket.on('disconnect', () => {
      console.log('[Socket] 已断开连接');
    });
  }, []);

  // 提取颜色
  useEffect(() => {
    const url = playback?.item?.album?.images?.[0]?.url;
    if (!url) return;

    Vibrant.from(url).getPalette()
      .then(p => {
        setTheme({
          background: p.DarkMuted?.getHex() || '#111',
          titleColor: p.LightVibrant?.getHex() || '#fff',
          artistColor: p.LightMuted?.getHex() || '#ccc',
          timeColor: p.LightVibrant?.getHex() || '#fff',
          progressColor: p.Vibrant?.getHex() || '#1db954',
          // 提取全部 6 种颜色，如果没有提取到则给一个默认备用色
          bgColors: [
            p.Vibrant?.getHex() || '#c0392b',      // 1. 鲜艳
            p.DarkVibrant?.getHex() || '#8e44ad',  // 2. 深鲜艳
            p.LightVibrant?.getHex() || '#e67e22', // 3. 亮鲜艳
            p.Muted?.getHex() || '#2980b9',        // 4. 柔和
            p.DarkMuted?.getHex() || '#2c3e50',    // 5. 深柔和
            p.LightMuted?.getHex() || '#27ae60'    // 6. 亮柔和
          ]
        });
      })
      .catch(err => {
        console.error('颜色提取失败:', err);
        setTheme(prev => ({ ...prev, background: '#111' }));
      });
  }, [playback?.item?.album?.images]);

  if (!playback || !playback.item) {
    return (
      <div style={{ color: '#fff', fontSize: '24px', padding: '20px' }}>
      </div>
    );
  }

  const { is_playing, progress_ms, item } = playback;
  const duration_ms = item.duration_ms;
  const progressRatio = duration_ms ? progress_ms / duration_ms : 0;

  const trackName = item.name;
  const artistName = item.artists.map(a => a.name).join(', ');
  const coverUrl = item.album.images[1]?.url || item.album.images[0]?.url;

  const formatTime = (ms) => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  return (
    <div className="wrapper">
      <style>{styles}</style>
      <div
        id="root"
        className={`container ${
          playback && is_playing === false
            ? 'closed'
            : playback && is_playing
            ? 'playing'
            : 'closed'
        }`}
      >
        {/* Layer 1: Base Background */}
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            borderRadius: '30px',
            backgroundColor: theme.background,
            transition: 'background-color 1s ease',
            boxShadow: `0 0px 15px ${hexToRgba(theme.artistColor, 0.5)}`,
                // 添加过渡效果，让阴影颜色随封面切换平滑改变
            transition: 'box-shadow 2.5s ease-in-out, opacity 0.4s ease',
            zIndex: 0
        }}></div>

        {/* Layer 2: Animated Blobs (6个平均分布) */}
        {/* 新增的外层包裹器：负责剪裁 (Mask) */}
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0, // 严格对齐卡片边缘
            borderRadius: '30px',                 // 圆角
            overflow: 'hidden',                   // 真正的剪裁发生在这里
            zIndex: 1                             // 层级控制
        }}>
            <div className="apple-bg-container">
                {/* --- 上层区域 --- */}
                <div className="apple-blob" style={{
                    top: '-10%', left: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[0],
                    animationDuration: '25s',
                    animationDelay: '0s'
                }}></div>

                <div className="apple-blob" style={{
                    top: '-20%', left: '25%', width: '50%', height: '50%',
                    background: theme.bgColors[2],
                    animationDuration: '32s',
                    animationDelay: '-6s',
                    animationDirection: 'reverse'
                }}></div>

                <div className="apple-blob" style={{
                    top: '-10%', right: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[3],
                    animationDuration: '28s',
                    animationDelay: '-12s'
                }}></div>

                {/* --- 下层区域 --- */}
                <div className="apple-blob" style={{
                    bottom: '-10%', left: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[1],
                    animationDuration: '22s',
                    animationDelay: '-4s',
                    animationDirection: 'reverse'
                }}></div>

                <div className="apple-blob" style={{
                    bottom: '-20%', right: '25%', width: '50%', height: '50%',
                    background: theme.bgColors[5],
                    animationDuration: '30s',
                    animationDelay: '-8s'
                }}></div>

                <div className="apple-blob" style={{
                    bottom: '-10%', right: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[4],
                    animationDuration: '26s',
                    animationDelay: '-16s',
                    animationDirection: 'reverse'
                }}></div>
            </div>
        </div>

        {/* Layer 3: Glass Overlay (zIndex: 2) */}
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            borderRadius: '30px',
            backgroundColor: hexToRgba('#000000', 0.2), 
            backdropFilter: 'blur(30px)', 
            zIndex: 2 
        }}></div>
        
        {/* Layer 4: Content (zIndex: 10 - 确保最高) */}
        
        {/* 封面区域 */}
        <div className="cover" style={{ zIndex: 10 }}>
          <img
            ref={imgRef} 
            src={coverUrl} 
            alt="封面" 
            crossOrigin="anonymous"
            style={{
                // 使用 theme.artistColor (即 LightMuted)，并设置 50% 透明度
                boxShadow: `0 0px 15px ${hexToRgba(theme.artistColor, 0.5)}`,
                // 添加过渡效果，让阴影颜色随封面切换平滑改变
                transition: 'box-shadow 2.5s ease-in-out, opacity 0.4s ease'
            }}
          />
        </div>

        {/* 文字和进度条区域 */}
        <div className="main show-progress-bar scrolling" style={{ zIndex: 10 }}>
          <ScrollingText text={trackName} color={theme.titleColor} extraClass="name" />
          <ScrollingText text={artistName} color={theme.artistColor} extraClass="artist" />

          <div className="progress-container show">
            <div className="time-left" style={{ color: theme.timeColor }}>
              {formatTime(progress_ms)}
            </div>
            <div className="progress-bar">
              <div className="progress" style={{ width: `${progressRatio * 100}%`, background: theme.progressColor }}></div>
            </div>
            <div className="time" style={{ color: theme.timeColor }}>
              {formatTime(duration_ms)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 跑马灯组件
function ScrollingText({ text, color, extraClass }) {
  const wrapperRef = useRef();
  const textRef = useRef();
  const scrollRef = useRef();

  useEffect(() => {
    const el = textRef.current;
    const wrapper = wrapperRef.current;
    if (!el || !wrapper) return;

    cancelAnimationFrame(scrollRef.current);
    el.style.transform = 'translateX(0)';

    const needsScroll = el.scrollWidth > wrapper.offsetWidth;
    if (!needsScroll) return;

    let offset = 0;
    let dir = -1;

    const scroll = () => {
      offset += dir;
      el.style.transform = `translateX(${offset}px)`;
      if (offset <= -el.scrollWidth) dir = 1;
      if (offset >= wrapper.offsetWidth) dir = -1;
      scrollRef.current = requestAnimationFrame(scroll);
    };

    const delayTimer = setTimeout(() => {
      scrollRef.current = requestAnimationFrame(scroll);
    }, 3000);

    return () => {
      clearTimeout(delayTimer);
      cancelAnimationFrame(scrollRef.current);
    };
  }, [text]);

  return (
    <div ref={wrapperRef} className={`scroll-wrapper ${extraClass}`}>
      <div
        ref={textRef}
        className="scroll-text"
        style={{ color }}
      >
        {text}
      </div>
    </div>
  );
}