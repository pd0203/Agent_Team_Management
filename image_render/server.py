#!/usr/bin/env python3
"""
Image Render Service
--------------------
에이전트(openclaw-gateway)가 내부 Docker 네트워크를 통해
POST /render 를 호출하면 matplotlib으로 PNG 이미지를 생성하고
Telegram Bot API sendPhoto로 CEO에게 직접 전송합니다.

Port: 7779 (내부 Docker 네트워크 전용 — 인터넷 노출 금지)
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import io, json, os, logging, urllib.request, warnings

# matplotlib color-font glyph warning 억제 (NotoColorEmoji 미지원 — 이모지는 박스로 표시되나 기능 정상)
warnings.filterwarnings("ignore", message="Glyph .* missing from font")

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CEO_TELEGRAM_ID    = os.environ.get("CEO_TELEGRAM_ID", "")
TELEGRAM_API       = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ── 폰트 스택 설정 (한국어 + 이모지 fallback) ─────────────────────────
def _setup_fonts():
    available = {f.name for f in fm.fontManager.ttflist}

    # 1) 한국어 폰트 선택
    cjk_font = next(
        (n for n in ['Noto Sans CJK KR', 'NotoSansCJKkr', 'Noto Sans CJK JP',
                     'NotoSansCJK', 'UnDotum', 'NanumGothic', 'Malgun Gothic']
         if n in available),
        None,
    )
    # 2) 이모지 폰트 선택
    emoji_font = next(
        (n for n in ['Noto Color Emoji', 'Noto Emoji', 'Segoe UI Emoji']
         if n in available),
        None,
    )
    # 3) 폰트 스택 구성 (CJK → Emoji → DejaVu 순서로 fallback)
    stack = [f for f in [cjk_font, emoji_font, 'DejaVu Sans'] if f]
    plt.rcParams['font.family'] = stack
    logging.info("Font stack: %s", stack)

_setup_fonts()

# ── 색상 테이블 ──────────────────────────────────────────────────────
_COLORS = {
    "blue": "#a8d8ea",    "darkblue": "#4a90d9",
    "green": "#b8e0b8",   "darkgreen": "#4caf50",
    "orange": "#f5d5a0",  "darkorange": "#e8a000",
    "red": "#f5a0a0",     "darkred": "#e74c3c",
    "purple": "#d0d0ff",  "darkpurple": "#6666cc",
    "gray": "#d0d0d0",    "darkgray": "#777777",
    "brown": "#8b6f5a",   "darkbrown": "#5a3e28",
    "yellow": "#fff5b0",  "lightblue": "#c8e8f8",
    "white": "#f5f5f5",   "cream": "#f5f0e8",
}

def _color(c: str) -> str:
    return _COLORS.get(c, c)

BG    = '#1a1a2e'
PANEL = '#2a2a3e'

# ── 렌더러: 막대 차트 ────────────────────────────────────────────────
def render_bar(data: dict, title: str) -> io.BytesIO:
    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = [_color(c) for c in data.get("colors", ["#4a90d9"] * len(values))]
    unit   = data.get("unit", "")

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)

    bars = ax.bar(labels, values, color=colors, edgecolor='#555', linewidth=0.8, width=0.6)
    max_v = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_v * 0.015,
                f'{val:,}{unit}', ha='center', va='bottom', color='white', fontsize=10)

    ax.set_title(title, color='white', fontsize=14, pad=15)
    ax.tick_params(colors='white', labelsize=10)
    ax.spines['top'].set_visible(False);  ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444'); ax.spines['left'].set_color('#444')
    ax.grid(axis='y', color='#333', linewidth=0.5, alpha=0.5)
    if data.get("ylabel"):
        ax.set_ylabel(data["ylabel"], color='#aaa', fontsize=11)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    return buf

# ── 렌더러: 꺾은선 차트 ─────────────────────────────────────────────
def render_line(data: dict, title: str) -> io.BytesIO:
    series   = data.get("series", [])
    x_labels = data.get("x_labels", [])
    palette  = ['#4a90d9', '#e8a000', '#4caf50', '#e74c3c', '#9b59b6', '#1abc9c']
    unit     = data.get("unit", "")

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG); ax.set_facecolor(PANEL)

    for i, s in enumerate(series):
        color = palette[i % len(palette)]
        ax.plot(range(len(s["values"])), s["values"],
                color=color, linewidth=2.5, marker='o', markersize=6,
                label=s.get("label", f"시리즈{i+1}"))
        for x, y in enumerate(s["values"]):
            ax.annotate(f'{y:,}{unit}', (x, y), textcoords="offset points",
                        xytext=(0, 9), ha='center', color=color, fontsize=8)

    if x_labels:
        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=30, ha='right', color='white')

    ax.set_title(title, color='white', fontsize=14, pad=15)
    ax.tick_params(colors='white', labelsize=10)
    ax.spines['top'].set_visible(False);  ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444'); ax.spines['left'].set_color('#444')
    ax.grid(color='#333', linewidth=0.5, alpha=0.5)
    ax.legend(facecolor=PANEL, edgecolor='#444', labelcolor='white', fontsize=10)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    return buf

# ── 렌더러: 원형 차트 ────────────────────────────────────────────────
def render_pie(data: dict, title: str) -> io.BytesIO:
    labels  = data.get("labels", [])
    values  = data.get("values", [])
    palette = ['#4a90d9', '#e8a000', '#4caf50', '#e74c3c', '#9b59b6', '#1abc9c', '#e67e22']

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

    _, texts, autotexts = ax.pie(
        values, labels=labels,
        colors=palette[:len(values)],
        autopct='%1.1f%%', startangle=90,
        textprops={'color': 'white', 'fontsize': 11},
        wedgeprops={'edgecolor': BG, 'linewidth': 2},
        pctdistance=0.80,
    )
    for at in autotexts:
        at.set_fontsize(10)

    ax.set_title(title, color='white', fontsize=14, pad=15)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    return buf

# ── 렌더러: 표 ──────────────────────────────────────────────────────
def render_table(data: dict, title: str) -> io.BytesIO:
    headers = data.get("headers", [])
    rows    = data.get("rows", [])

    fig, ax = plt.subplots(figsize=(12, max(3.0, len(rows) * 0.55 + 2.0)))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG); ax.axis('off')

    table = ax.table(cellText=rows, colLabels=headers, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.2)

    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor('#4a90d9')
        cell.set_text_props(color='white', fontweight='bold')
        cell.set_edgecolor('#1a1a2e')

    for i in range(1, len(rows) + 1):
        for j in range(len(headers)):
            cell = table[i, j]
            cell.set_facecolor(PANEL if i % 2 == 0 else '#1e1e30')
            cell.set_text_props(color='white')
            cell.set_edgecolor('#333')

    ax.set_title(title, color='white', fontsize=13, pad=20, y=1.0)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    return buf

# ── 렌더러: 사무실 배치도 ────────────────────────────────────────────
def render_floor_plan(data: dict, title: str) -> io.BytesIO:
    """
    상대 좌표계 (0.0 ~ 1.0) 사용. 내부 캔버스: 1000 x 700 단위.

    data 구조:
    {
      "north_label": "북측 창가",        # 선택
      "zones":    [{"x":0.05,"y":0.05,"w":0.90,"h":0.25,"label":"임원 구역","color":"blue","border":"darkblue"}],
      "dividers": [{"x":0.05,"y":0.35,"w":0.25,"h":0.05,"label":"서가","color":"brown"}],
      "furniture":[{"x":0.06,"y":0.10,"w":0.15,"h":0.12,"label":"임원 1","color":"lightblue"}],
      "circles":  [{"cx":0.75,"cy":0.65,"r":0.055,"label":"원형 탁상","color":"orange"}],
      "entry":    {"x":0.40,"y":0.95,"w":0.20}   # 선택
    }
    """
    CW, CH = 1000, 700

    fig, ax = plt.subplots(figsize=(13, 9))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#f0ebe0')
    ax.set_xlim(0, CW); ax.set_ylim(CH, 0)
    ax.set_aspect('equal'); ax.axis('off')

    # 외벽
    ax.add_patch(patches.Rectangle((0, 0), CW, CH,
                                    linewidth=3, edgecolor='#333', facecolor='#f0ebe0'))

    def px(r): return r * CW
    def py(r): return r * CH

    # 구역 배경
    for z in data.get("zones", []):
        ax.add_patch(patches.Rectangle(
            (px(z["x"]), py(z["y"])), px(z["w"]), py(z["h"]),
            linewidth=1.5, edgecolor=_color(z.get("border", "darkblue")),
            facecolor=_color(z.get("color", "cream")), alpha=0.65))
        if z.get("label"):
            ax.text(px(z["x"]) + px(z["w"]) / 2, py(z["y"]) + 14, z["label"],
                    ha='center', va='center', fontsize=9, fontweight='bold',
                    color=z.get("text_color", "#1a3a6a"))

    # 가벽 / 서가 / 파티션
    for d in data.get("dividers", []):
        ax.add_patch(patches.Rectangle(
            (px(d["x"]), py(d["y"])), px(d["w"]), py(d["h"]),
            linewidth=2, edgecolor='#3a2a1a', facecolor=_color(d.get("color", "brown"))))
        if d.get("label"):
            ax.text(px(d["x"]) + px(d["w"]) / 2, py(d["y"]) + py(d["h"]) / 2, d["label"],
                    ha='center', va='center', fontsize=8, color='white', fontweight='bold')

    # 가구 (책상 등)
    for f in data.get("furniture", []):
        ax.add_patch(patches.FancyBboxPatch(
            (px(f["x"]), py(f["y"])), px(f["w"]), py(f["h"]),
            boxstyle="round,pad=2", linewidth=1.5,
            edgecolor='#555', facecolor=_color(f.get("color", "lightblue"))))
        if f.get("label"):
            ax.text(px(f["x"]) + px(f["w"]) / 2, py(f["y"]) + py(f["h"]) / 2, f["label"],
                    ha='center', va='center', fontsize=9, fontweight='bold', color='#222')

    # 원형 테이블
    for c in data.get("circles", []):
        ax.add_patch(plt.Circle(
            (px(c["cx"]), py(c["cy"])), px(c.get("r", 0.04)),
            linewidth=1.5, edgecolor=_color(c.get("border", "darkorange")),
            facecolor=_color(c.get("color", "orange"))))
        if c.get("label"):
            ax.text(px(c["cx"]), py(c["cy"]), c["label"],
                    ha='center', va='center', fontsize=8, fontweight='bold', color='#5a3000')

    # 입구
    entry = data.get("entry", {})
    if entry:
        ex, ey, ew = px(entry.get("x", 0.42)), py(entry.get("y", 0.965)), px(entry.get("w", 0.16))
        ax.add_patch(patches.Rectangle((ex, ey), ew, 16,
                                        linewidth=2, edgecolor='#5a4000', facecolor='#c8a000'))
        ax.text(ex + ew / 2, ey + 8, "▼ ENTRY (입구)",
                ha='center', va='center', fontsize=8, color='white', fontweight='bold')

    # 북측 레이블
    ax.text(CW / 2, -10, data.get("north_label", "[ 북측 / 창가 ]"),
            ha='center', va='center', fontsize=9, color='#4a90d9', fontweight='bold')

    ax.set_title(title, color='white', fontsize=13, pad=10,
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a2e', alpha=0.85))

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close()
    return buf

# ── Telegram sendPhoto ───────────────────────────────────────────────
def send_photo(chat_id: str, buf: io.BytesIO, caption: str) -> dict:
    buf.seek(0)
    image_data = buf.read()
    boundary   = b'----FormBoundary7MA4YWxkTrZu0gW'

    def field(name, value):
        return (b'--' + boundary + b'\r\n'
                + f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
                + (value if isinstance(value, bytes) else value.encode())
                + b'\r\n')

    body = (field('chat_id', chat_id)
            + field('caption', caption[:1024])
            + field('parse_mode', 'HTML')
            + b'--' + boundary + b'\r\n'
            + b'Content-Disposition: form-data; name="photo"; filename="image.png"\r\n'
            + b'Content-Type: image/png\r\n\r\n'
            + image_data + b'\r\n'
            + b'--' + boundary + b'--\r\n')

    req = urllib.request.Request(
        f"{TELEGRAM_API}/sendPhoto",
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary.decode()}'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

# ── HTTP Handler ─────────────────────────────────────────────────────
RENDERERS = {
    "bar":        render_bar,
    "line":       render_line,
    "pie":        render_pie,
    "table":      render_table,
    "floor_plan": render_floor_plan,
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logging.info(fmt % args)

    def do_GET(self):
        if self.path == '/health':
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != '/render':
            self._json(404, {"error": "not found"}); return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length)) if length else {}

            chart_type = body.get("type", "bar")
            title      = body.get("title", "차트")
            data       = body.get("data", {})
            caption    = body.get("caption", title)
            chat_id    = body.get("telegram_chat_id", CEO_TELEGRAM_ID)

            if not chat_id:
                self._json(400, {"status": "error", "error": "CEO_TELEGRAM_ID not configured"}); return
            if chart_type not in RENDERERS:
                self._json(400, {"status": "error", "error": f"Unknown type: {chart_type}. Available: {list(RENDERERS)}"}); return

            buf    = RENDERERS[chart_type](data, title)
            result = send_photo(chat_id, buf, caption)

            if result.get("ok"):
                self._json(200, {"status": "ok", "message_id": result["result"]["message_id"]})
            else:
                self._json(500, {"status": "error", "error": str(result)})

        except Exception as e:
            logging.exception("Render error")
            self._json(500, {"status": "error", "error": str(e)})

    def _json(self, code: int, body: dict):
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    port = int(os.environ.get("RENDER_PORT", 7779))
    logging.info("Image-render service listening on :%d", port)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
