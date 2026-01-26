import { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import './assets/index.css';
import './assets/Rainbow.css';

const socket = io('http://localhost:5001');
const defaultCover = './images/Spotify.png'; // 默认封面图片

// --- Apple Music 风格流体动画 CSS (与播放器组件完全一致) ---
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

/* 内层画布：向外扩张，给光斑足够的移动空间 */
.apple-bg-container {
  position: absolute;
  top: -150px; left: -150px; right: -150px; bottom: -150px; 
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
  // --- 状态定义 ---
  const [queueText, setQueueText] = useState({
    queue1: '点歌队列空',
    queue2: '点歌发送：点歌 歌名(+歌手)'
  });

  const [cover, setCover] = useState(defaultCover);

  const [theme, setTheme] = useState({
    background: '#111111',
    titleColor: '#ffffff',
    artistColor: '#aaaaaa',
    timeColor: '#ffffff',
    progressColor: '#1db954',
    // 默认备用颜色组
    bgColors: ['#333', '#444', '#555', '#222', '#666', '#111']
  });

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

  // --- Socket 监听逻辑 (保持不变) ---
  useEffect(() => {
    socket.on('playlist_update', (data) => {
      console.log('Received playlist update:', data);
      if (data && data.length > 0) {
        setCover(data[0].albumCover);
        updateDisplayText('playlist', data);
      } else {
        setCover(defaultCover);
        updateDisplayText('playlist', []);
      }
    });

    socket.on('message_update', (data) => {
      console.log('Received message update:', data);
      if (data.result !== '没有找到匹配歌曲' && data.albumCover) {
        setCover(data.albumCover);
      }
      updateDisplayText('message', data);
    });
  }, []);

  const updateDisplayText = (type, data) => {
    if (type === 'message') {
      const queue1 = data.message || '点歌队列空';
      const queue2 = data.result || '点歌发送：点歌 歌名(+歌手)';
      setQueueText({ queue1, queue2 });
    } else if (type === 'playlist') {
      const now = data[0];
      const next = data[1];
      const queue1 = now ? `列队1: ${now.name}` : '点歌队列空';
      const queue2 = next ? `列队2: ${next.name}` : '点歌发送：点歌 歌名(+歌手)';
      setQueueText({ queue1, queue2 });
    }
  };

  // --- 颜色提取逻辑 (更新为提取6种颜色) ---
  useEffect(() => {
    if (!cover) return;

    Vibrant.from(cover).getPalette()
      .then(palette => {
        setTheme({
          background: palette.DarkMuted?.getHex() || '#111111',
          titleColor: palette.LightVibrant?.getHex() || '#ffffff',
          artistColor: palette.LightMuted?.getHex() || '#aaaaaa',
          timeColor: palette.LightVibrant?.getHex() || '#ffffff',
          progressColor: palette.Vibrant?.getHex() || '#1db954',
          // 提取全部 6 种颜色用于光斑
          bgColors: [
            palette.Vibrant?.getHex() || '#c0392b',      // 1
            palette.DarkVibrant?.getHex() || '#8e44ad',  // 2
            palette.LightVibrant?.getHex() || '#e67e22', // 3
            palette.Muted?.getHex() || '#2980b9',        // 4
            palette.DarkMuted?.getHex() || '#2c3e50',    // 5
            palette.LightMuted?.getHex() || '#27ae60'    // 6
          ]
        });
      })
      .catch(error => {
        console.error("调色板提取失败：", error);
        // 保持之前的颜色或重置
      });
  }, [cover]);

  return (
    <div className="wrapper">
      <style>{styles}</style>
      <div
        id="root"
        className="container playing" // 这里的 playing 类控制显示动画，保持原样
      >
        {/* Layer 1: Base Background Color (纯色打底) */}
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            borderRadius: '30px',
            backgroundColor: theme.background,
            transition: 'background-color 2.5s ease',
            boxShadow: `0 0px 15px ${hexToRgba(theme.artistColor, 0.5)}`,
                // 添加过渡效果，让阴影颜色随封面切换平滑改变
                transition: 'box-shadow 2.5s ease-in-out, opacity 0.4s ease',
            zIndex: 0
        }}></div>

        {/* Layer 2: Animated Blobs (6个光斑) */}
        {/* 外层 Mask：限制显示区域 */}
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            borderRadius: '30px',
            overflow: 'hidden',
            zIndex: 1
        }}>
            {/* 内层 Canvas：提供活动空间 */}
            <div className="apple-bg-container">
                {/* 1. 左上: Vibrant */}
                <div className="apple-blob" style={{
                    top: '-10%', left: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[0],
                    animationDuration: '25s',
                    animationDelay: '0s'
                }}></div>

                {/* 2. 中上: LightVibrant */}
                <div className="apple-blob" style={{
                    top: '-20%', left: '25%', width: '50%', height: '50%',
                    background: theme.bgColors[2],
                    animationDuration: '32s',
                    animationDelay: '-6s',
                    animationDirection: 'reverse'
                }}></div>

                {/* 3. 右上: Muted */}
                <div className="apple-blob" style={{
                    top: '-10%', right: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[3],
                    animationDuration: '28s',
                    animationDelay: '-12s'
                }}></div>

                {/* 4. 左下: DarkVibrant */}
                <div className="apple-blob" style={{
                    bottom: '-10%', left: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[1],
                    animationDuration: '22s',
                    animationDelay: '-4s',
                    animationDirection: 'reverse'
                }}></div>

                {/* 5. 中下: LightMuted */}
                <div className="apple-blob" style={{
                    bottom: '-20%', right: '25%', width: '50%', height: '50%',
                    background: theme.bgColors[5],
                    animationDuration: '30s',
                    animationDelay: '-8s'
                }}></div>

                {/* 6. 右下: DarkMuted */}
                <div className="apple-blob" style={{
                    bottom: '-10%', right: '-10%', width: '55%', height: '55%',
                    background: theme.bgColors[4],
                    animationDuration: '26s',
                    animationDelay: '-16s',
                    animationDirection: 'reverse'
                }}></div>
            </div>
        </div>

        {/* Layer 3: Glass Overlay (磨砂玻璃) */}
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            borderRadius: '30px',
            backgroundColor: hexToRgba('#000000', 0.2), // 稍微调低遮罩浓度
            backdropFilter: 'blur(30px)',
            zIndex: 2
        }}></div>

        {/* Layer 4: Content (封面 & 文字) - 确保 zIndex 高于背景 */}
        <div className="cover" style={{ zIndex: 10 }}>
          <img
            className="img"
            src={cover}
            alt="专辑封面"
            crossOrigin="anonymous"
            style={{
                // 使用 theme.artistColor (即 LightMuted)，并设置 50% 透明度
                boxShadow: `0 0px 15px ${hexToRgba(theme.artistColor, 0.5)}`,
                // 添加过渡效果，让阴影颜色随封面切换平滑改变
                transition: 'box-shadow 2.5s ease-in-out, opacity 0.4s ease'
            }}
          />
        </div>
        <div className="main hide-progress-bar scrolling" style={{ zIndex: 10 }}>
          <ScrollingText
            text={queueText.queue1}
            color={theme.titleColor}
            extraClass="name"
          />
          <ScrollingText
            text={queueText.queue2}
            color={theme.artistColor}
            extraClass="artist"
          />
        </div>
      </div>
    </div>
  );
}

// 跑马灯组件保持不变
function ScrollingText({ text, color, extraClass = '' }) {
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