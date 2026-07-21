"""SRT → ASS 字幕转换，支持关键帧动画风格。

用法：
  python scripts/srt_to_ass.py subtitles.srt --output subtitles.ass
  python scripts/srt_to_ass.py subtitles.srt --style pop --fontsize 48 --output subtitles.ass
"""

import argparse
import pathlib
import re
import sys

try:
    from ass import Dialogue, Document, Style
    from ass.data import Color
except ImportError:
    sys.exit("缺少 ass 库，请运行：python -m pip install ass")


# ── SRT 解析 ────────────────────────────────────────────
def parse_srt(srt_path):
    """解析 SRT 文件，返回 [(开始ms, 结束ms, 文本), ...]"""
    content = pathlib.Path(srt_path).read_text(encoding="utf-8-sig")
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        time_line = lines[1] if len(lines) > 1 else ""
        text = "\n".join(lines[2:])
        match = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
            time_line,
        )
        if not match:
            continue
        start_ms = (
            int(match.group(1)) * 3600000
            + int(match.group(2)) * 60000
            + int(match.group(3)) * 1000
            + int(match.group(4))
        )
        end_ms = (
            int(match.group(5)) * 3600000
            + int(match.group(6)) * 60000
            + int(match.group(7)) * 1000
            + int(match.group(8))
        )
        entries.append((start_ms, end_ms, text.strip()))
    return entries


# ── CSS 颜色转 ASS ───────────────────────────────────────
def hex_to_color(code):
    """#RRGGBB → Color(r, g, b, a=0)"""
    code = code.lstrip("#")
    r, g, b = int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)
    return Color(r=r, g=g, b=b, a=0)


def css_hex_to_ass(code):
    """#RRGGBB → &HAABBGGRR&"""
    code = code.lstrip("#")
    r, g, b = code[0:2], code[2:4], code[4:6]
    return f"&H00{b}{g}{r}&"


# ── 动画风格 ─────────────────────────────────────────────
def apply_pop(text, duration_ms):
    """弹出风格：缩放弹性弹入 + 透明度淡入"""
    t = min(duration_ms, 800)
    return (
        r"{\fscx20\fscy20\1a&HFF&"
        rf"\t(0,0,{t},\fscx20\fscy20,\fscx120\fscy120)"
        rf"\t(0,{t//2},{t},\fscx120\fscy120,\fscx100\fscy100)"
        rf"\t(0,100,{t//3},\1a&HFF&,\1a&H00&)}}"
        + text
    )


def apply_slide(text, duration_ms):
    """滑入风格：从下方 30px 滑入到位"""
    t = min(duration_ms // 2, 500)
    return (
        rf"{{\pos(960,570)\t(0,0,{t},\pos(960,570),\pos(960,540))}}"
        + text
    )


def apply_slide_left(text, duration_ms):
    """左滑入：从右边界滑入到位"""
    t = min(duration_ms // 2, 600)
    return (
        rf"{{\pos(2120,540)\t(0,0,{t},\pos(2120,540),\pos(960,540))}}"
        + text
    )


def apply_fade(text, duration_ms):
    """淡入淡出风格"""
    fade_in = min(duration_ms // 4, 400)
    fade_out = min(duration_ms // 4, 400)
    return rf"{{\fad({fade_in},{fade_out})}}" + text


def apply_karaoke(text, duration_ms):
    """卡拉OK风格：逐字变色（蓝→白）"""
    parts = []
    per_char = max(duration_ms // max(len(text), 1), 30)
    for ch in text:
        if ch.isspace():
            parts.append(ch)
        else:
            parts.append(rf"{{\k{per_char // 10}}}{ch}")
    return "".join(parts)


def apply_bounce(text, duration_ms):
    """弹跳风格：从上方落入 + 两次回弹"""
    t1 = min(duration_ms * 2 // 5, 400)
    t2 = min(duration_ms * 3 // 5, 600)
    t3 = min(duration_ms * 4 // 5, 750)
    return (
        r"{\fscx50\fscy50\1a&HFF&"
        rf"\pos(960,100)\t(0,0,{t1},\pos(960,100),\pos(960,600))"
        rf"\t(0,{t1},{t2},\pos(960,600),\pos(960,480))"
        rf"\t(0,{t2},{t3},\pos(960,480),\pos(960,540))"
        rf"\t(0,0,{t1},\fscx50\fscy50,\fscx110\fscy110)"
        rf"\t(0,{t1},{t2},\fscx110\fscy110,\fscx95\fscy95)"
        rf"\t(0,{t2},{t3},\fscx95\fscy95,\fscx100\fscy100)"
        rf"\t(0,100,{t1//2},\1a&HFF&,\1a&H00&)}}"
        + text
    )


def apply_rotate_in(text, duration_ms):
    """旋转弹入：绕 Z 轴旋转 + 缩放 + 透明度"""
    t = min(duration_ms, 800)
    return (
        r"{\frz-45\fscx30\fscy30\1a&HFF&"
        rf"\t(0,0,{t},\frz-45,\frz0)"
        rf"\t(0,0,{t},\fscx30\fscy30,\fscx100\fscy100)"
        rf"\t(0,100,{t//3},\1a&HFF&,\1a&H00&)}}"
        + text
    )


def apply_flip_3d(text, duration_ms):
    """3D 翻转：绕 Y 轴翻转 + 透明度"""
    t = min(duration_ms, 900)
    return (
        r"{\fry-90\1a&HFF&"
        rf"\t(0,0,{t},\fry-90,\fry0)"
        rf"\t(0,100,{t//3},\1a&HFF&,\1a&H00&)}}"
        + text
    )


def apply_typewriter(text, duration_ms):
    """打字机风格：\clip 从左到右逐字展开"""
    per_char_ms = max(duration_ms // max(len(text), 1), 30)
    parts = []
    total_width = len(text) * 32  # 预估中文字符宽度
    for i, ch in enumerate(text):
        if ch.isspace():
            parts.append(ch)
            continue
        clip_end = (i + 1) * 32
        t_start = i * per_char_ms // 10
        t_end = (i + 1) * per_char_ms // 10
        parts.append(
            rf"{{\clip(800,860,{800 + clip_end},940)"
            rf"\t({t_start},{t_end},\clip(800,860,{800 + (i) * 32},940),\clip(800,860,{800 + clip_end},940))}}"
            + ch
        )
    return "".join(parts)


def apply_glow(text, duration_ms):
    """发光脉冲：描边粗细呼吸式振荡"""
    period = 600
    return (
        r"{\bord0"
        rf"\t(0,0,{period},\bord0,\bord8)"
        rf"\t(0,{period},{period * 2},\bord8,\bord2)"
        rf"\t(0,{period * 2},{period * 3},\bord2,\bord6)"
        rf"\t(0,{period * 3},{period * 4},\bord6,\bord2)}}"
        + text
    )


def apply_blur_in(text, duration_ms):
    """模糊渐清：从高斯模糊到清晰 + 淡入"""
    t = min(duration_ms, 800)
    return (
        r"{\blur30\1a&HFF&"
        rf"\t(0,0,{t},\blur30,\blur0)"
        rf"\t(0,100,{t//3},\1a&HFF&,\1a&H00&)}}"
        + text
    )


def apply_shake(text, duration_ms):
    """抖动风格：快速左右振荡 + 衰减归位"""
    return (
        r"{\pos(950,540)"
        r"\t(0,0,80,\pos(950,540),\pos(970,540))"
        r"\t(0,80,160,\pos(970,540),\pos(940,540))"
        r"\t(0,160,240,\pos(940,540),\pos(965,540))"
        r"\t(0,240,320,\pos(965,540),\pos(955,540))"
        r"\t(0,320,400,\pos(955,540),\pos(960,540))}"
        + text
    )


def apply_color_shift(text, duration_ms):
    """变色渐变：蓝色→品红→白色 关键帧过渡"""
    t1 = min(duration_ms // 2, 600)
    t2 = min(duration_ms, 1200)
    return (
        r"{\1c&H00FF0000&"
        rf"\t(0,0,{t1},\1c&H00FF0000&,\1c&H00FF00FF&)"
        rf"\t(0,{t1},{t2},\1c&H00FF00FF&,\1c&H00FFFFFF&)}}"
        + text
    )


def apply_wipe(text, duration_ms):
    """擦除出现：\clip 从左向右擦除"""
    return (
        r"{\clip(800,860,800,940)"
        rf"\t(0,0,{duration_ms // 10},\clip(800,860,800,940),\clip(800,860,1120,940))}}"
        + text
    )


def apply_combo(text, duration_ms):
    """组合动画：旋转 + 缩放 + 模糊 + 透明度 四属性同时关键帧"""
    t = min(duration_ms, 900)
    return (
        r"{\frz-20\fscx20\fscy20\blur20\1a&HFF&"
        rf"\t(0,0,{t},\frz-20,\frz0)"
        rf"\t(0,0,{t},\fscx20\fscy20,\fscx100\fscy100)"
        rf"\t(0,0,{t//2},\blur20,\blur0)"
        rf"\t(0,100,{t//3},\1a&HFF&,\1a&H00&)}}"
        + text
    )


STYLES = {
    "plain": lambda t, d: t,
    "pop": apply_pop,
    "slide": apply_slide,
    "slide-left": apply_slide_left,
    "fade": apply_fade,
    "karaoke": apply_karaoke,
    "bounce": apply_bounce,
    "rotate-in": apply_rotate_in,
    "flip-3d": apply_flip_3d,
    "typewriter": apply_typewriter,
    "glow": apply_glow,
    "blur-in": apply_blur_in,
    "shake": apply_shake,
    "color-shift": apply_color_shift,
    "wipe": apply_wipe,
    "combo": apply_combo,
}


# ── 命令行 ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SRT → ASS 字幕转换（支持关键帧动画）")
    parser.add_argument("input", help="SRT 文件路径")
    parser.add_argument("--output", help="输出 ASS 文件路径（默认同目录同名.ass）")
    parser.add_argument(
        "--style",
        choices=list(STYLES.keys()),
        default="plain",
        help="动画风格（默认 plain）",
    )
    parser.add_argument("--font", default="微软雅黑", help="字体（默认微软雅黑）")
    parser.add_argument("--fontsize", type=int, default=48, help="字号（默认 48）")
    parser.add_argument("--color", default="#FFFFFF", help="主颜色 #RRGGBB（默认白色）")
    parser.add_argument("--outline-color", default="#000000", help="描边颜色（默认黑色）")
    parser.add_argument("--outline", type=float, default=3, help="描边粗细（默认 3）")
    parser.add_argument("--shadow", type=float, default=1, help="阴影深度（默认 1）")
    parser.add_argument("--alignment", type=int, default=2, help="对齐：2=底部居中 5=顶部居中")
    parser.add_argument("--play-res-x", type=int, default=1920, help="播放分辨率宽")
    parser.add_argument("--play-res-y", type=int, default=1080, help="播放分辨率高")
    args = parser.parse_args()

    srt_path = pathlib.Path(args.input)
    if not srt_path.exists():
        sys.exit(f"SRT 文件不存在：{srt_path}")

    output_path = pathlib.Path(args.output) if args.output else srt_path.with_suffix(".ass")

    entries = parse_srt(str(srt_path))
    if not entries:
        sys.exit("SRT 文件中未找到有效字幕条目")

    style_func = STYLES[args.style]

    doc = Document()
    doc.info["Title"] = srt_path.stem
    doc.info["PlayResX"] = str(args.play_res_x)
    doc.info["PlayResY"] = str(args.play_res_y)

    doc.styles.append(Style(
        Name="Default",
        Fontname=args.font,
        Fontsize=args.fontsize,
        PrimaryColour=hex_to_color(args.color),
        SecondaryColour=hex_to_color("#FF0000"),
        OutlineColour=hex_to_color(args.outline_color),
        BackColour=hex_to_color("#80000000"),
        Outline=args.outline,
        Shadow=args.shadow,
        Alignment=args.alignment,
        MarginL=40,
        MarginR=40,
        MarginV=30,
    ))

    for start_ms, end_ms, text in entries:
        duration = end_ms - start_ms
        animated_text = style_func(text, duration)
        doc.events.append(
            Dialogue(
                start=start_ms * 10,
                end=end_ms * 10,
                style="Default",
                text=animated_text,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig") as f:
        doc.dump_file(f)

    print(f"已生成 ASS 字幕：{output_path}（{len(entries)} 条，风格：{args.style}）")


if __name__ == "__main__":
    main()
