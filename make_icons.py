"""Claude Design で作ったロゴ（SVG/HTML）から、Play 掲載画像と Android ランチャーアイコン一式を書き出して検品する。

使い方（例）:
  python make_icons.py --fg brand/logo-fg.svg --bg "#0B5FFF" --feature brand/feature.html --out brand/out
  python make_icons.py --fg fg.svg --bg bg.svg --mono mono.svg --feature feature.svg --out out

入力の約束（SKILL.md のロゴ・アイコン作成の節を参照）:
  --fg       前景レイヤー。正方形・108dp キャンバス相当（例 viewBox="0 0 108 108"）、背景は透明。
             ロゴは中央 66dp（安全域）の内側に収める。外周 18dp は端末のマスクで切られる。
  --bg       背景レイヤー。"#RRGGBB" か、--fg と同じ正方形の SVG/PNG。透明不可。
  --mono     テーマアイコン（Android 13+）用の単色シルエット。省略時は --fg のアルファから自動生成。
  --feature  フィーチャーグラフィック 1024x500 の SVG/HTML/PNG（省略可）。
  --play-icon  Play 掲載用 512 アイコンを別デザインで用意する場合の SVG/PNG（省略時は bg+fg を合成）。

SVG/HTML は Chrome（headless）で描画する。PNG を渡した場合はそのまま使う。
SVG は <img> として描くので外部フォント・外部画像は読まれない（文字はパス化するかシステムフォント）。
Web フォントを使う掲載画像は、フォントの <link> を書いた単体の HTML で渡す。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

DENSITIES = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}
RENDER = 1728  # 108dp の描画解像度（432px@xxxhdpi の4倍）。縮小して使う
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
]


def find_chrome():
    env = os.environ.get("CHROME_PATH")
    if env:
        if not (os.path.isfile(env) or shutil.which(env)):
            sys.exit(f"CHROME_PATH が指すファイルが無い: {env}")
        return env
    for c in CHROME_CANDIDATES:
        if os.path.isfile(c) or shutil.which(c):
            return c
    sys.exit("Chrome/Edge が見つからない。CHROME_PATH を設定する。")


def render(src, w, h, tmp):
    """SVG/HTML/PNG を w x h の RGBA 画像にする。"""
    src = Path(src).resolve()
    if not src.is_file():
        sys.exit(f"入力ファイルが無い: {src}")
    if src.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        return Image.open(src).convert("RGBA").resize((w, h), Image.LANCZOS)
    if src.suffix.lower() == ".svg":
        page = Path(tmp) / f"wrap_{src.stem}_{w}x{h}.html"
        page.write_text(
            "<!doctype html><html><head><style>html,body{margin:0;background:transparent}"
            f"img{{display:block;width:{w}px;height:{h}px}}</style></head>"
            f'<body><img src="{src.as_uri()}"></body></html>',
            encoding="utf-8",
        )
    else:
        page = src
    out = Path(tmp) / f"shot_{src.stem}_{w}x{h}.png"
    cmd = [
        find_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--default-background-color=00000000",
        "--allow-file-access-from-files", f"--user-data-dir={Path(tmp) / 'chrome-profile'}",
        "--virtual-time-budget=5000",  # Web フォント等の読み込みを待ってから撮る
        f"--window-size={w},{h}", f"--screenshot={out}", page.as_uri(),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    img = Image.open(out).convert("RGBA")
    if img.size != (w, h):  # ウィンドウ枠ぶん小さく撮れる環境がある → 必ず検出する
        sys.exit(f"描画サイズ不一致: {src.name} 期待 {w}x{h} 実際 {img.size[0]}x{img.size[1]}")
    return img


def layer(spec, size, tmp):
    if spec.startswith("#"):
        return Image.new("RGBA", (size, size), spec)
    return render(spec, size, size, tmp)


def silhouette(img):
    """アルファだけを残した白のシルエット（monochrome 層はアルファしか使われない）。"""
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white.putalpha(img.getchannel("A"))
    return white


def mask(size, shape):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    if shape == "circle":
        d.ellipse((0, 0, size - 1, size - 1), fill=255)
    else:  # 角丸四角（ランチャーで最も一般的な見え方の近似）
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.2), fill=255)
    return m


def viewport(composite):
    """108dp のうち、マスクで見える中央 72dp を切り出す。"""
    s = composite.size[0]
    m = round(s * 18 / 108)
    return composite.crop((m, m, s - m, s - m))


def outside_safe_zone(fg):
    """安全域（中央 66dp の円）の外に不透明な画素がどれだけあるか（%）。"""
    s = fg.size[0]
    r = s * 33 / 108
    outside = Image.new("L", fg.size, 255)
    ImageDraw.Draw(outside).ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=0)
    a = fg.getchannel("A").point(lambda v: 255 if v > 32 else 0)
    hit = ImageChops.multiply(a, outside)
    total = a.histogram()[255]
    bad = hit.histogram()[255]
    return 100.0 * bad / total if total else 0.0


def save_png(img, path, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert(mode).save(path, optimize=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows コンソールの文字化け防止
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--fg", required=True)
    ap.add_argument("--bg", required=True)
    ap.add_argument("--mono")
    ap.add_argument("--feature")
    ap.add_argument("--play-icon")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    out = Path(a.out)
    res = out / "res"
    play = out / "play"
    problems = []

    with tempfile.TemporaryDirectory() as tmp:
        fg = layer(a.fg, RENDER, tmp)
        bg = layer(a.bg, RENDER, tmp)
        if bg.getchannel("A").getextrema()[0] < 255:
            problems.append("背景レイヤーに透明部分がある（背景は不透明にする）")
        mono = silhouette(layer(a.mono, RENDER, tmp)) if a.mono else silhouette(fg)
        composite = Image.alpha_composite(bg, fg)

        if fg.getchannel("A").getextrema()[1] == 0:
            problems.append("前景が完全に透明（SVG が空か、描画に失敗している）")
        pct = outside_safe_zone(fg)
        if pct > 1.0:
            problems.append(f"前景の {pct:.1f}% が安全域（中央66dp円）の外。端末によってロゴが欠ける")

        # アダプティブアイコン（API 26+）: 各密度の 108dp レイヤー
        for name, k in DENSITIES.items():
            px = round(108 * k)
            d = res / f"mipmap-{name}"
            save_png(fg.resize((px, px), Image.LANCZOS), d / "ic_launcher_foreground.png", "RGBA")
            save_png(bg.resize((px, px), Image.LANCZOS), d / "ic_launcher_background.png", "RGBA")
            save_png(mono.resize((px, px), Image.LANCZOS), d / "ic_launcher_monochrome.png", "RGBA")
            # 旧来アイコン（API 24-25 用。minSdk 24 なら必須）: 48dp
            lp = round(48 * k)
            vis = viewport(composite).resize((lp, lp), Image.LANCZOS)
            for fname, shape in (("ic_launcher.png", "rounded"), ("ic_launcher_round.png", "circle")):
                icon = Image.new("RGBA", (lp, lp), (0, 0, 0, 0))
                icon.paste(vis, (0, 0), mask(lp, shape))
                save_png(icon, d / fname, "RGBA")

        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@mipmap/ic_launcher_background" />\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
            '    <monochrome android:drawable="@mipmap/ic_launcher_monochrome" />\n'
            "</adaptive-icon>\n"
        )
        anydpi = res / "mipmap-anydpi-v26"
        anydpi.mkdir(parents=True, exist_ok=True)
        for f in ("ic_launcher.xml", "ic_launcher_round.xml"):
            (anydpi / f).write_text(xml, encoding="utf-8")

        # Play 掲載用 512 アイコン: 全面の正方形・角丸なし・影なし（角丸と影は Play が付ける）
        if a.play_icon:
            icon512 = render(a.play_icon, 512, 512, tmp)
        else:
            icon512 = composite.resize((512, 512), Image.LANCZOS)
        p512 = play / "icon-512.png"
        save_png(icon512, p512, "RGBA")
        if icon512.getchannel("A").getextrema()[0] < 255:
            problems.append("512アイコンに透明部分がある（Play の背景色が透けて見える）")
        if p512.stat().st_size > 1024 * 1024:
            problems.append(f"icon-512.png が {p512.stat().st_size // 1024}KB（上限 1024KB）")

        # フィーチャーグラフィック 1024x500: JPEG か 24bit PNG（アルファなし）
        if a.feature:
            feat = render(a.feature, 1024, 500, tmp)
            flat = Image.new("RGB", feat.size, (255, 255, 255))
            flat.paste(feat, (0, 0), feat)
            save_png(flat, play / "feature-1024x500.png", "RGB")

        # 見え方の確認シート（円・角丸・Play 30%角丸・テーマアイコン）
        cells = []
        vis = viewport(composite).resize((192, 192), Image.LANCZOS)
        for shape in ("circle", "rounded"):
            c = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
            c.paste(vis, (0, 0), mask(192, shape))
            cells.append(c)
        pm = Image.new("L", (192, 192), 0)
        ImageDraw.Draw(pm).rounded_rectangle((0, 0, 191, 191), radius=int(192 * 0.3), fill=255)
        p = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
        p.paste(icon512.resize((192, 192), Image.LANCZOS), (0, 0), pm)
        cells.append(p)
        theme = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
        tint = Image.new("RGBA", (192, 192), (214, 227, 255, 255))
        glyph = Image.new("RGBA", (192, 192), (26, 47, 99, 0))
        glyph.putalpha(viewport(mono).resize((192, 192), Image.LANCZOS).getchannel("A"))
        theme.paste(Image.alpha_composite(tint, glyph), (0, 0), mask(192, "circle"))
        cells.append(theme)
        sheet = Image.new("RGB", (4 * 192 + 5 * 24, 240), (238, 238, 238))
        for i, c in enumerate(cells):
            sheet.paste(c, (24 + i * 216, 24), c)
        save_png(sheet, out / "preview-masks.png", "RGB")

    # 検品
    checks = [
        (play / "icon-512.png", (512, 512), "RGBA"),
        (play / "feature-1024x500.png", (1024, 500), "RGB"),
    ]
    for n, k in DENSITIES.items():
        for f in ("foreground", "background", "monochrome"):
            checks.append((res / f"mipmap-{n}" / f"ic_launcher_{f}.png", (round(108 * k),) * 2, "RGBA"))
        for f in ("ic_launcher.png", "ic_launcher_round.png"):
            checks.append((res / f"mipmap-{n}" / f, (round(48 * k),) * 2, "RGBA"))
    print("== 書き出し結果 ==")
    for path, size, mode in checks:
        if not path.exists():
            if "feature" in path.name and not a.feature:
                print(f"  -    {path.name}（--feature 未指定）")
                continue
            problems.append(f"{path} が無い")
            continue
        im = Image.open(path)
        ok = im.size == size and im.mode == mode
        if not ok:
            problems.append(f"{path.name}: {im.size} {im.mode}（期待 {size} {mode}）")
        print(f"  {'OK ' if ok else 'NG '} {path.relative_to(out)}  {im.size[0]}x{im.size[1]} {im.mode} {path.stat().st_size // 1024}KB")
    for f in ("ic_launcher.xml", "ic_launcher_round.xml"):
        x = res / "mipmap-anydpi-v26" / f
        if not x.is_file():
            problems.append(f"{x} が無い")
    print(f"  安全域の外にはみ出した前景: {pct:.1f}%")
    print(f"  確認シート: {out / 'preview-masks.png'}（円／角丸／Play表示／テーマアイコン）")
    if problems:
        print("\n== 要修正 ==")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\nPASS")


if __name__ == "__main__":
    main()
