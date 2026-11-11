"""生成 6 款 PPT 模板背景图(1920x1080, 16:9)。

设计原则: 装饰元素集中分布(边角/对角/边缘), 中心区域只做很淡的底色+光晕,
保证叠加标题/要点文字后依然清晰可读。
运行: python make_backgrounds.py
输出: assets/ppt_bg/<模板key>.png + preview_grid.png(6 张拼图预览)
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
OUT = BASE / "assets" / "ppt_bg"

# 每款背景 = 一个完整 SVG(1920x1080)。
DESIGNS: dict[str, str] = {
    # ---------- 1. 简约商务: 几何网格 + 交错圆环 + 对角光带 + 装饰角标 ----------
    "business": """
<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="b" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="0.6" stop-color="#f5f8fe"/><stop offset="1" stop-color="#e9effa"/>
    </linearGradient>
    <radialGradient id="bg1" cx="0.86" cy="0.16" r="0.55">
      <stop offset="0" stop-color="#2f6feb" stop-opacity="0.14"/><stop offset="1" stop-color="#2f6feb" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="bg2" cx="0.1" cy="0.92" r="0.5">
      <stop offset="0" stop-color="#2f6feb" stop-opacity="0.11"/><stop offset="1" stop-color="#2f6feb" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="bband" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#2f6feb" stop-opacity="0.11"/><stop offset="0.5" stop-color="#5a90ff" stop-opacity="0.05"/><stop offset="1" stop-color="#2f6feb" stop-opacity="0"/>
    </linearGradient>
    <pattern id="bgrid" width="90" height="90" patternUnits="userSpaceOnUse">
      <path d="M90 0H0V90" fill="none" stroke="#2f6feb" stroke-opacity="0.055" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="1920" height="1080" fill="url(#b)"/>
  <rect width="1920" height="1080" fill="url(#bg1)"/>
  <rect width="1920" height="1080" fill="url(#bg2)"/>
  <rect width="1920" height="1080" fill="url(#bgrid)"/>
  <path d="M0 990 L1920 190 L1920 430 L0 1230 Z" fill="url(#bband)"/>
  <g stroke="#2f6feb" fill="none">
    <circle cx="1740" cy="170" r="240" stroke-opacity="0.22" stroke-width="2"/>
    <circle cx="1740" cy="170" r="175" stroke-opacity="0.15" stroke-width="1.5"/>
    <circle cx="1740" cy="170" r="112" stroke-opacity="0.10" stroke-width="1"/>
    <circle cx="1740" cy="170" r="240" stroke-opacity="0.32" stroke-width="3" stroke-dasharray="60 42"/>
  </g>
  <circle cx="1740" cy="170" r="112" fill="#2f6feb" fill-opacity="0.05"/>
  <g stroke="#2f6feb" fill="none"><path d="M60 60 H260" stroke-opacity="0.30" stroke-width="2"/><path d="M60 60 V170" stroke-opacity="0.30" stroke-width="2"/></g>
  <circle cx="60" cy="60" r="6" fill="#2f6feb" fill-opacity="0.4"/>
  <rect x="110" y="880" width="80" height="80" fill="#2f6feb" fill-opacity="0.08" transform="rotate(18 150 920)"/>
  <rect x="214" y="928" width="46" height="46" fill="#2f6feb" fill-opacity="0.14" transform="rotate(-12 237 951)"/>
  <circle cx="332" cy="972" r="18" fill="#2f6feb" fill-opacity="0.20"/>
  <circle cx="394" cy="930" r="9" fill="#2f6feb" fill-opacity="0.34"/>
  <g stroke="#2f6feb"><line x1="640" y1="70" x2="1180" y2="70" stroke-opacity="0.18" stroke-width="1.5"/>
  <line x1="700" y1="58" x2="700" y2="82" stroke-opacity="0.30" stroke-width="2"/>
  <line x1="900" y1="56" x2="900" y2="84" stroke-opacity="0.22" stroke-width="2"/>
  <line x1="1100" y1="58" x2="1100" y2="82" stroke-opacity="0.30" stroke-width="2"/></g>
  <circle cx="1450" cy="770" r="6" fill="#2f6feb" fill-opacity="0.30"/>
  <circle cx="1520" cy="836" r="4" fill="#2f6feb" fill-opacity="0.22"/>
  <circle cx="1378" cy="826" r="3" fill="#2f6feb" fill-opacity="0.26"/>
</svg>""",

    # ---------- 2. 科技深蓝: 辉光 + 透视网格 + 电路走线 + 数据弧 + 光束 ----------
    "tech": """
<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="t" cx="0.5" cy="0.42" r="0.85">
      <stop offset="0" stop-color="#152a45"/><stop offset="0.55" stop-color="#0e1c33"/><stop offset="1" stop-color="#070f1e"/>
    </radialGradient>
    <radialGradient id="tg1" cx="0.85" cy="0.14" r="0.5"><stop offset="0" stop-color="#4fc3f7" stop-opacity="0.20"/><stop offset="1" stop-color="#4fc3f7" stop-opacity="0"/></radialGradient>
    <radialGradient id="tg2" cx="0.12" cy="0.94" r="0.5"><stop offset="0" stop-color="#1e6fd8" stop-opacity="0.16"/><stop offset="1" stop-color="#1e6fd8" stop-opacity="0"/></radialGradient>
    <linearGradient id="tbeam" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#4fc3f7" stop-opacity="0"/><stop offset="0.5" stop-color="#4fc3f7" stop-opacity="0.22"/><stop offset="1" stop-color="#4fc3f7" stop-opacity="0"/>
    </linearGradient>
    <pattern id="thex" width="90" height="156" patternUnits="userSpaceOnUse">
      <path d="M45 0 L90 27 L90 81 L45 108 L0 81 L0 27 Z" fill="none" stroke="#4fc3f7" stroke-opacity="0.06" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="1920" height="1080" fill="url(#t)"/>
  <rect width="1920" height="1080" fill="url(#tg1)"/>
  <rect width="1920" height="1080" fill="url(#tg2)"/>
  <g stroke="#4fc3f7" stroke-opacity="0.06" stroke-width="1">
    <line x1="0" y1="800" x2="1920" y2="800"/><line x1="0" y1="880" x2="1920" y2="880"/><line x1="0" y1="980" x2="1920" y2="980"/>
    <line x1="960" y1="720" x2="0" y2="1080"/><line x1="960" y1="720" x2="480" y2="1080"/><line x1="960" y1="720" x2="1440" y2="1080"/><line x1="960" y1="720" x2="1920" y2="1080"/>
  </g>
  <line x1="0" y1="1080" x2="1500" y2="0" stroke="url(#tbeam)" stroke-width="70" opacity="0.30"/>
  <line x1="120" y1="1080" x2="1650" y2="0" stroke="url(#tbeam)" stroke-width="14" opacity="0.34"/>
  <rect x="1380" y="40" width="480" height="400" fill="url(#thex)"/>
  <g stroke="#4fc3f7" fill="none">
    <path d="M1560 130 H1720 V270 H1880" stroke-opacity="0.42" stroke-width="2"/>
    <path d="M1500 210 H1620 V370 H1780" stroke-opacity="0.24" stroke-width="1.5"/>
    <path d="M1600 80 V250" stroke-opacity="0.30" stroke-width="2"/>
    <circle cx="1780" cy="150" r="120" stroke-opacity="0.14" stroke-width="1"/>
    <circle cx="1780" cy="150" r="120" stroke-opacity="0.55" stroke-width="3" stroke-dasharray="320 440"/>
    <circle cx="1780" cy="150" r="80" stroke-opacity="0.20" stroke-width="1"/>
  </g>
  <g fill="#4fc3f7">
    <circle cx="1560" cy="130" r="5" fill-opacity="0.85"/><circle cx="1880" cy="270" r="5" fill-opacity="0.85"/>
    <circle cx="1780" cy="370" r="4" fill-opacity="0.6"/><rect x="1716" y="266" width="9" height="9" fill-opacity="0.7"/>
    <circle cx="1600" cy="80" r="4" fill-opacity="0.7"/><circle cx="1900" cy="150" r="3" fill-opacity="0.5"/>
  </g>
  <g stroke="#4fc3f7" fill="none"><line x1="0" y1="700" x2="60" y2="700" stroke-opacity="0.3" stroke-width="2"/><line x1="0" y1="1010" x2="120" y2="1010" stroke-opacity="0.2" stroke-width="2"/></g>
  <circle cx="90" cy="700" r="6" fill="#4fc3f7" fill-opacity="0.6"/><circle cx="160" cy="1010" r="4" fill="#4fc3f7" fill-opacity="0.45"/>
  <circle cx="1120" cy="980" r="5" fill="#4fc3f7" fill-opacity="0.4"/>
</svg>""",

    # ---------- 3. 活力橙: 放射太阳光 + 色块切割 + 波浪 + 气泡 + 半圆 ----------
    "orange": """
<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="o" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fffaf3"/><stop offset="1" stop-color="#fff1e3"/></linearGradient>
    <radialGradient id="osun" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#ffb27a" stop-opacity="0.6"/><stop offset="0.45" stop-color="#ff8a4c" stop-opacity="0.26"/><stop offset="1" stop-color="#ff8a4c" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#o)"/>
  <path d="M1920 0 L1920 540 L1560 0 Z" fill="#ff8a4c" fill-opacity="0.13"/>
  <path d="M1920 0 L1920 380 L1740 0 Z" fill="#e8613c" fill-opacity="0.15"/>
  <circle cx="1720" cy="180" r="190" fill="url(#osun)"/>
  <circle cx="1720" cy="180" r="72" fill="#ff8a4c" fill-opacity="0.30"/>
  <g stroke="#e8613c" stroke-opacity="0.22" stroke-width="3" transform="translate(1720,180)">
    <line x1="150" y1="0" x2="210" y2="0"/><line x1="150" y1="0" x2="210" y2="0" transform="rotate(30)"/>
    <line x1="150" y1="0" x2="210" y2="0" transform="rotate(60)"/><line x1="150" y1="0" x2="210" y2="0" transform="rotate(90)"/>
    <line x1="150" y1="0" x2="210" y2="0" transform="rotate(150)"/><line x1="150" y1="0" x2="210" y2="0" transform="rotate(210)"/>
    <line x1="150" y1="0" x2="210" y2="0" transform="rotate(300)"/>
  </g>
  <g fill="none" stroke="#e8613c">
    <path d="M0 900 Q 300 838 600 900 T 1200 900" stroke-opacity="0.18" stroke-width="3"/>
    <path d="M0 958 Q 300 898 600 958 T 1200 958" stroke-opacity="0.11" stroke-width="2.5"/>
  </g>
  <path d="M1700 1080 A 230 230 0 0 1 1920 1080 Z" fill="#e8613c" fill-opacity="0.10"/>
  <circle cx="220" cy="250" r="42" fill="#ff8a4c" fill-opacity="0.14"/>
  <circle cx="330" cy="185" r="18" fill="#e8613c" fill-opacity="0.20"/>
  <circle cx="1500" cy="830" r="62" fill="#ffb27a" fill-opacity="0.18"/>
  <circle cx="1500" cy="830" r="62" fill="none" stroke="#e8613c" stroke-opacity="0.22" stroke-width="2"/>
  <circle cx="1630" cy="770" r="22" fill="#e8613c" fill-opacity="0.24"/>
  <circle cx="470" cy="820" r="30" fill="#ff8a4c" fill-opacity="0.12"/>
  <g fill="#e8613c"><polygon points="1420,520 1432,548 1408,548" fill-opacity="0.30"/><polygon points="560,300 572,328 548,328" fill-opacity="0.24"/></g>
</svg>""",

    # ---------- 4. 清新绿: 多层山峦 + 太阳 + 植物 + 飞鸟 + 水波 ----------
    "green": """
<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6fbf7"/><stop offset="1" stop-color="#e7f3ea"/></linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#g)"/>
  <circle cx="250" cy="230" r="96" fill="#2e9e5b" fill-opacity="0.10"/>
  <circle cx="250" cy="230" r="58" fill="#2e9e5b" fill-opacity="0.18"/>
  <g stroke="#2e9e5b" stroke-opacity="0.22" stroke-width="2.5" transform="translate(250,230)">
    <line x1="80" y1="0" x2="112" y2="0"/><line x1="80" y1="0" x2="112" y2="0" transform="rotate(45)"/>
    <line x1="80" y1="0" x2="112" y2="0" transform="rotate(90)"/><line x1="80" y1="0" x2="112" y2="0" transform="rotate(135)"/>
    <line x1="80" y1="0" x2="112" y2="0" transform="rotate(225)"/><line x1="80" y1="0" x2="112" y2="0" transform="rotate(315)"/>
  </g>
  <path d="M0 900 L300 740 L560 870 L820 730 L1100 860 L1400 700 L1700 840 L1920 760 L1920 1080 L0 1080 Z" fill="#2e9e5b" fill-opacity="0.08"/>
  <path d="M0 980 L360 840 L680 960 L1040 830 L1360 950 L1720 840 L1920 930 L1920 1080 L0 1080 Z" fill="#2e9e5b" fill-opacity="0.14"/>
  <path d="M0 1040 L420 950 L820 1030 L1240 940 L1660 1040 L1920 990 L1920 1080 L0 1080 Z" fill="#2e9e5b" fill-opacity="0.22"/>
  <g stroke="#2e9e5b" fill="none" stroke-width="2.5">
    <path d="M1650 520 C 1650 620 1690 700 1760 780" stroke-opacity="0.30"/>
    <path d="M1700 540 C 1700 600 1670 640 1640 660" stroke-opacity="0.22"/>
  </g>
  <g fill="#2e9e5b"><ellipse cx="1764" cy="780" rx="46" ry="20" fill-opacity="0.20" transform="rotate(30 1764 780)"/>
    <ellipse cx="1640" cy="650" rx="38" ry="16" fill-opacity="0.16" transform="rotate(-40 1640 650)"/></g>
  <g stroke="#2e9e5b" fill="none" stroke-width="2" stroke-opacity="0.30">
    <path d="M470 300 q 18 -16 36 0 q 18 -16 36 0"/><path d="M560 360 q 15 -14 30 0 q 15 -14 30 0"/>
    <path d="M640 320 q 14 -13 28 0 q 14 -13 28 0"/>
  </g>
  <g fill="none" stroke="#2e9e5b"><path d="M60 470 q 120 -24 240 0 t 240 0" stroke-opacity="0.16" stroke-width="2"/></g>
  <circle cx="1450" cy="430" r="8" fill="#2e9e5b" fill-opacity="0.26"/><circle cx="1500" cy="470" r="5" fill="#2e9e5b" fill-opacity="0.20"/>
</svg>""",

    # ---------- 5. 黑金尊享: Art Deco 放射 + 拱形 + 钻石切面 + 四角金框 ----------
    "blackgold": """
<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="k" cx="0.5" cy="0.5" r="0.85"><stop offset="0" stop-color="#1d1a12"/><stop offset="0.6" stop-color="#14120c"/><stop offset="1" stop-color="#0b0a07"/></radialGradient>
    <linearGradient id="kbeam" x1="0" y1="0.5" x2="1" y2="0.5">
      <stop offset="0" stop-color="#d4af37" stop-opacity="0"/><stop offset="0.5" stop-color="#d4af37" stop-opacity="0.55"/><stop offset="1" stop-color="#d4af37" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#k)"/>
  <g stroke="#d4af37" stroke-opacity="0.10" stroke-width="1" transform="translate(960,1080)">
    <line x1="0" y1="0" x2="-900" y2="-640"/><line x1="0" y1="0" x2="-600" y2="-820"/>
    <line x1="0" y1="0" x2="-300" y2="-940"/><line x1="0" y1="0" x2="0" y2="-980"/>
    <line x1="0" y1="0" x2="300" y2="-940"/><line x1="0" y1="0" x2="600" y2="-820"/><line x1="0" y1="0" x2="900" y2="-640"/>
  </g>
  <g stroke="#d4af37" fill="none">
    <circle cx="1560" cy="440" r="180" stroke-opacity="0.28" stroke-width="1.5"/>
    <circle cx="1560" cy="440" r="146" stroke-opacity="0.16" stroke-width="1"/>
  </g>
  <polygon points="1560,330 1650,440 1560,550 1470,440" fill="#d4af37" fill-opacity="0.05" stroke="#d4af37" stroke-opacity="0.40" stroke-width="1.5"/>
  <polygon points="1560,330 1560,550 1470,440" fill="#d4af37" fill-opacity="0.10"/>
  <g stroke="#d4af37" fill="none"><path d="M1560 330 L1560 550 M1470 440 L1650 440" stroke-opacity="0.22" stroke-width="1"/></g>
  <g stroke="#d4af37" fill="none">
    <path d="M70 70 H210" stroke-opacity="0.5" stroke-width="1.5"/><path d="M70 70 V210" stroke-opacity="0.5" stroke-width="1.5"/>
    <path d="M1850 70 H1710" stroke-opacity="0.35" stroke-width="1.5"/><path d="M1850 70 V210" stroke-opacity="0.35" stroke-width="1.5"/>
    <path d="M70 1010 H210" stroke-opacity="0.35" stroke-width="1.5"/><path d="M70 1010 V870" stroke-opacity="0.35" stroke-width="1.5"/>
    <path d="M1850 1010 H1710" stroke-opacity="0.5" stroke-width="1.5"/><path d="M1850 1010 V870" stroke-opacity="0.5" stroke-width="1.5"/>
  </g>
  <g fill="#d4af37"><rect x="64" y="64" width="12" height="12" transform="rotate(45 70 70)" fill-opacity="0.7"/></g>
  <line x1="0" y1="1010" x2="1920" y2="1010" stroke="url(#kbeam)" stroke-width="2"/>
  <g fill="#d4af37"><rect x="1500" y="1042" width="9" height="9" transform="rotate(45 1504 1046)" fill-opacity="0.9"/>
  <rect x="1470" y="1042" width="7" height="7" transform="rotate(45 1473 1045)" fill-opacity="0.6"/>
  <rect x="1534" y="1042" width="5" height="5" transform="rotate(45 1536 1044)" fill-opacity="0.4"/></g>
  <g stroke="#d4af37" fill="none" transform="translate(240,880)"><path d="M-120 0 A120 120 0 0 1 120 0" stroke-opacity="0.28" stroke-width="1.5"/>
  <path d="M-84 0 A84 84 0 0 1 84 0" stroke-opacity="0.40" stroke-width="1.5"/><line x1="0" y1="0" x2="0" y2="-120" stroke-opacity="0.2" stroke-width="1"/></g>
</svg>""",

    # ---------- 6. 创意紫: 流体柔光 + 悬浮块 + 星轨曲线 + 流星 + 星点 ----------
    "purple": """
<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="p" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fbfaff"/><stop offset="0.5" stop-color="#f5eefe"/><stop offset="1" stop-color="#ece0ff"/></linearGradient>
    <radialGradient id="pa" cx="0.85" cy="0.2" r="0.45"><stop offset="0" stop-color="#c9a8ff" stop-opacity="0.55"/><stop offset="1" stop-color="#c9a8ff" stop-opacity="0"/></radialGradient>
    <radialGradient id="pb" cx="0.12" cy="0.9" r="0.45"><stop offset="0" stop-color="#a47aff" stop-opacity="0.45"/><stop offset="1" stop-color="#a47aff" stop-opacity="0"/></radialGradient>
    <linearGradient id="pm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c4dff" stop-opacity="0"/><stop offset="1" stop-color="#7c4dff" stop-opacity="0.55"/></linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#p)"/>
  <rect width="1920" height="1080" fill="url(#pa)"/>
  <rect width="1920" height="1080" fill="url(#pb)"/>
  <g fill="none" stroke="#7c4dff">
    <path d="M-40 800 C 400 640, 900 920, 1360 540 S 1960 320, 2010 430" stroke-opacity="0.16" stroke-width="3"/>
    <path d="M-40 880 C 420 740, 920 1000, 1400 640 S 1960 440, 2010 540" stroke-opacity="0.10" stroke-width="2.5"/>
    <path d="M-40 720 C 380 560, 860 820, 1300 480 S 1900 260, 1990 360" stroke-opacity="0.12" stroke-width="2"/>
  </g>
  <g fill="none" stroke="#7c4dff"><circle cx="1450" cy="640" r="96" stroke-opacity="0.22" stroke-width="2"/><circle cx="1450" cy="640" r="60" stroke-opacity="0.16" stroke-width="1.5"/></g>
  <g fill="#7c4dff">
    <rect x="1520" y="300" width="150" height="150" rx="30" fill-opacity="0.10" transform="rotate(16 1595 375)"/>
    <rect x="1640" y="380" width="90" height="90" rx="22" fill-opacity="0.14" transform="rotate(28 1685 425)"/>
    <rect x="300" y="640" width="110" height="110" rx="26" fill-opacity="0.09" transform="rotate(-18 355 695)"/>
  </g>
  <line x1="1740" y1="120" x2="1500" y2="300" stroke="url(#pm)" stroke-width="4"/>
  <circle cx="1500" cy="300" r="9" fill="#7c4dff" fill-opacity="0.55"/><circle cx="1500" cy="300" r="4" fill="#ffffff" fill-opacity="0.8"/>
  <g fill="#7c4dff">
    <path d="M470 180 l4 12 12 4 -12 4 -4 12 -4 -12 -12 -4 12 -4 Z" fill-opacity="0.45"/>
    <path d="M1330 240 l3 9 9 3 -9 3 -3 9 -3 -9 -9 -3 9 -3 Z" fill-opacity="0.35"/>
    <circle cx="1180" cy="760" r="5" fill-opacity="0.30"/><circle cx="1240" cy="700" r="3" fill-opacity="0.24"/>
  </g>
  <g stroke="#a47aff" fill="none"><path d="M520 900 q 60 -30 120 0" stroke-opacity="0.20" stroke-width="2"/></g>
</svg>""",
}

_LABELS = [
    ("简约商务", "#2F6FEB"), ("科技深蓝", "#4FC3F7"), ("活力橙", "#E8613C"),
    ("清新绿", "#2E9E5B"), ("黑金尊享", "#D4AF37"), ("创意紫", "#7C4DFF"),
]

_PAGE_HEAD = "<!DOCTYPE html><html><head><meta charset=utf-8><style>html,body{margin:0}</style></head><body>"
_PAGE_TAIL = "</body></html>"


def _launch(p):
    try:
        return p.chromium.launch(channel="msedge")
    except Exception:
        return p.chromium.launch()


def main() -> None:
    import base64
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        imgs: dict[str, bytes] = {}
        for key, svg in DESIGNS.items():
            page.set_content(_PAGE_HEAD + svg + _PAGE_TAIL)
            page.wait_for_timeout(150)
            img = page.screenshot(type="png")
            assert img.startswith(b"\x89PNG")
            (OUT / f"{key}.png").write_bytes(img)
            imgs[key] = img
            print(f"[OK] {key:9s} -> assets/ppt_bg/{key}.png ({len(img)} 字节)")
        # 6 张拼图预览(带标签, 3x2)
        cells = []
        for i, (key, (cname, accent)) in enumerate(zip(DESIGNS, _LABELS), start=1):
            b64 = base64.b64encode(imgs[key]).decode()
            img_tag = f'<img src="data:image/png;base64,{b64}" style="width:600px;height:337px;display:block;object-fit:cover">'
            cells.append(
                f'<div style="width:600px"><div style="border:1px solid #ccc;width:600px;height:337px;overflow:hidden;background:#fff">{img_tag}</div>'
                f'<div style="font:14px/1 sans-serif;color:#333;margin-top:8px">{i}. {cname}　·　强调色 {accent}</div></div>'
            )
        grid_html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;background:#f4f6f8;font-family:sans-serif}"
            ".wrap{display:flex;flex-wrap:wrap;gap:20px;padding:20px}"
            "</style></head><body><div class='wrap'>" + "".join(cells) + "</div></body></html>"
        )
        page2 = browser.new_page(viewport={"width": 1860, "height": 1500})
        page2.set_content(grid_html)
        page2.wait_for_timeout(300)
        page2.screenshot(path=str(OUT / "preview_grid.png"), full_page=True)
        browser.close()
    print(f"\n预览拼图: {OUT / 'preview_grid.png'}")


if __name__ == "__main__":
    main()
