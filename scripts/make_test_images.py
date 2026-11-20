"""1080x1080 JPEG 테스트 이미지 2장 생성 → docs/test/ (GitHub Pages 공개 경로)."""
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "test"
SIZE = 1080
MAX_BYTES = 8 * 1024 * 1024
SLIDES = [("#1F3A5F", "TEST 1/2"), ("#8A1C1C", "TEST 2/2")]


def font(size: int):
    for name in ("malgunbd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    for i, (bg, label) in enumerate(SLIDES, 1):
        img = Image.new("RGB", (SIZE, SIZE), bg)
        d = ImageDraw.Draw(img)
        d.text((SIZE / 2, SIZE / 2 - 60), label, font=font(140), fill="white", anchor="mm")
        d.text((SIZE / 2, SIZE / 2 + 90), "업로드 테스트 · 곧 삭제", font=font(56), fill="white", anchor="mm")
        d.text((SIZE / 2, SIZE - 80), stamp, font=font(36), fill="#DDDDDD", anchor="mm")
        path = OUT / f"slide{i}.jpg"
        img.save(path, "JPEG", quality=90, optimize=True)  # 표준 baseline JPEG (MPO/JPS 아님)
        size = path.stat().st_size
        assert size <= MAX_BYTES, f"{path.name} {size} bytes > 8MB"
        print(f"{path.relative_to(OUT.parent.parent)}  {SIZE}x{SIZE}  {size/1024:.0f}KB")


if __name__ == "__main__":
    main()
