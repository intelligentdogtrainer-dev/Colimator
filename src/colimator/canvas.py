"""Рендер «бесконечного холста» из референса.

Сцена — это одно большое полотно с расставленными на нём объектами, по
которому ездит камера. Кадры рисует Chromium: вёрстка на CSS даёт настоящую
типографику и скругления, чего не получить фильтрами ffmpeg.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path

from .style import CANVAS_BG, FRAME_H, FRAME_W, GREEN, INK

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FONTS_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"


@dataclass
class Node:
    """Объект на холсте. Координаты — в системе полотна, не кадра."""

    x: int
    y: int
    text: str
    kind: str = "pill"  # heading | pill | ghost
    appear: float = 0.0


@dataclass
class CameraKey:
    t: float
    x: int
    y: int
    scale: float = 1.0


@dataclass
class Scene:
    duration: float
    nodes: list[Node] = field(default_factory=list)
    camera: list[CameraKey] = field(default_factory=list)
    fps: int = 30


_PAGE = """<!doctype html>
<meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Heading'; src: url('file://{fonts}/PlayfairDisplay[wght].ttf'); }}
  @font-face {{ font-family: 'Body'; src: url('file://{fonts}/PT_Serif-Web-Regular.ttf'); }}
  html, body {{ margin: 0; width: {w}px; height: {h}px; overflow: hidden; background: {bg}; }}
  /* Клетка холста: две сетки — мелкая и покрупнее, обе едва заметны. */
  #viewport {{
    position: absolute; inset: 0;
    background-image:
      linear-gradient(to right, rgba(7,6,2,.055) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(7,6,2,.055) 1px, transparent 1px);
    background-size: 24px 24px;
  }}
  #world {{ position: absolute; left: 0; top: 0; transform-origin: 0 0; }}
  .node {{ position: absolute; transform: translate(-50%, -50%); white-space: nowrap;
           opacity: 0; will-change: opacity, transform; }}
  .heading {{ font-family: 'Heading', Georgia, serif; font-weight: 600; font-size: 62px;
              color: {ink}; letter-spacing: -.5px; }}
  .ghost {{ font-family: 'Heading', Georgia, serif; font-size: 20px; color: rgba(7,6,2,.34); }}
  .pill {{ font-family: 'Body', Georgia, serif; font-size: 34px; color: {ink};
           border: 2.5px solid {ink}; border-radius: 999px; padding: 14px 30px; background: transparent; }}
  .accent {{ background: {green}; color: {bg}; border-color: {green}; }}
</style>
<div id="viewport"><div id="world"></div></div>
<script>
const NODES = {nodes};
const CAMERA = {camera};
const world = document.getElementById('world');
NODES.forEach((n, i) => {{
  const el = document.createElement('div');
  el.className = 'node ' + n.kind + (n.accent ? ' accent' : '');
  el.style.left = n.x + 'px';
  el.style.top = n.y + 'px';
  el.textContent = n.text;
  el.dataset.appear = n.appear;
  world.appendChild(el);
}});

const ease = u => u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u);

function camAt(t) {{
  if (CAMERA.length === 1) return CAMERA[0];
  let a = CAMERA[0], b = CAMERA[CAMERA.length - 1];
  for (let i = 0; i < CAMERA.length - 1; i++) {{
    if (t >= CAMERA[i].t && t <= CAMERA[i + 1].t) {{ a = CAMERA[i]; b = CAMERA[i + 1]; break; }}
    if (t > CAMERA[i].t) {{ a = CAMERA[i]; b = CAMERA[Math.min(i + 1, CAMERA.length - 1)]; }}
  }}
  const span = Math.max(b.t - a.t, 1e-6);
  const u = ease((t - a.t) / span);
  return {{ x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u, scale: a.scale + (b.scale - a.scale) * u }};
}}

// Камера смотрит в точку холста, которая должна оказаться в центре кадра.
window.seek = function (t) {{
  const c = camAt(t);
  const tx = {w} / 2 - c.x * c.scale;
  const ty = {h} / 2 - c.y * c.scale;
  world.style.transform = `translate(${{tx}}px, ${{ty}}px) scale(${{c.scale}})`;
  for (const el of world.children) {{
    const u = ease((t - parseFloat(el.dataset.appear)) / 0.42);
    el.style.opacity = u;
    el.style.transform = `translate(-50%, -50%) translateY(${{(1 - u) * 18}}px)`;
  }}
}};
</script>
"""


def render(scene: Scene, out_dir: Path) -> int:
    """Рисует кадры сцены в out_dir как frame_%05d.png. Возвращает их число."""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    nodes = [
        {
            "x": n.x,
            "y": n.y,
            "text": html.unescape(n.text),
            "kind": n.kind,
            "appear": n.appear,
            "accent": n.kind == "pill" and n.text.startswith("*"),
        }
        for n in scene.nodes
    ]
    for node, spec in zip(scene.nodes, nodes):
        spec["text"] = node.text.lstrip("*")

    page_html = _PAGE.format(
        w=FRAME_W,
        h=FRAME_H,
        bg=CANVAS_BG,
        ink=INK,
        green=GREEN,
        fonts=FONTS_DIR.as_posix(),
        nodes=json.dumps(nodes, ensure_ascii=False),
        camera=json.dumps([vars(k) for k in scene.camera], ensure_ascii=False),
    )

    total = int(round(scene.duration * scene.fps))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--force-device-scale-factor=1", "--hide-scrollbars"],
        )
        page = browser.new_page(viewport={"width": FRAME_W, "height": FRAME_H})
        page.set_content(page_html)
        page.wait_for_timeout(400)  # дать шрифтам подгрузиться
        for i in range(total):
            page.evaluate("seek", i / scene.fps)
            page.screenshot(path=str(out_dir / f"frame_{i:05d}.png"))
        browser.close()
    return total
