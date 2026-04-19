#!/usr/bin/env python3
"""
도식화 후처리 — 안티앨리어싱 제거 + 실루엣 감지.

입력: generated/{mat}_{angle}.png (리자드/오스트리치) + 크로커다일 레퍼런스
출력: generated/clean/{mat}_{angle}.png — RGBA 포맷:
  - 가방 외부: alpha 0 (투명)
  - 선: 순수 검정 (0,0,0,255)
  - 내부: 순수 흰색 (255,255,255,255)

이 구조로 만들면 브라우저에서 multiply 블렌드 시 선은 검정으로, 내부만 컬러로
칠해지는 깔끔한 패션 도식화 스타일이 됩니다.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

ROOT = Path(__file__).parent
GEN = ROOT / "generated"
OUT = GEN / "clean"
OUT.mkdir(exist_ok=True)
REF_DIR = Path("/Users/junkim/Desktop/베티(VETTI)/이미지 레퍼런스")

SOURCES = {
    # 재생성 파이프라인: croc도 generated/에서 가져옴 (원본 레퍼런스가 아닌 GPT 재생성본)
    "croc_front":   GEN / "croc_front.png",
    "croc_side":    GEN / "croc_side.png",
    "croc_back":    GEN / "croc_back.png",
    "lizard_front": GEN / "lizard_front.png",
    "lizard_side":  GEN / "lizard_side.png",
    "lizard_back":  GEN / "lizard_back.png",
    "ostrich_front": GEN / "ostrich_front.png",
    "ostrich_side":  GEN / "ostrich_side.png",
    "ostrich_back":  GEN / "ostrich_back.png",
}

THRESH = 180   # L 값 기준 (이하는 검정, 이상은 흰색)


def process(src_path: Path, out_path: Path):
    img = Image.open(src_path).convert("L")
    arr = np.array(img)

    # 1) 이진화 — 안티앨리어싱 완전 제거
    binary = np.where(arr < THRESH, 0, 255).astype(np.uint8)
    work = Image.fromarray(binary, mode="L")

    # 2) 형태학적 닫힘으로 외곽선 틈 메우기
    #    — MinFilter가 어두운 픽셀(선)을 확장시켜 1~3픽셀 갭을 봉합
    sealed = work.filter(ImageFilter.MinFilter(5))

    # 3) 봉합된 이미지에서 네 모서리 floodfill → 외부만 마커(1)로 표시
    marker_img = sealed.copy()
    w, h = marker_img.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for cx, cy in corners:
        if marker_img.getpixel((cx, cy)) == 255:
            ImageDraw.floodfill(marker_img, (cx, cy), 1)

    # 4) 알파 마스크: marker==1 → 투명, 나머지 → 불투명
    marker_arr = np.array(marker_img)
    alpha = np.where(marker_arr == 1, 0, 255).astype(np.uint8)

    # 5) RGB는 원본 binary(날카로운 선)로 구성 — 닫힘 연산은 마스크 용도로만
    rgb = binary
    rgba = np.dstack([rgb, rgb, rgb, alpha])

    Image.fromarray(rgba, "RGBA").save(out_path, "PNG", optimize=True)
    print(f"  ✓ {out_path.name}  ({src_path.stat().st_size:,} → {out_path.stat().st_size:,} bytes)")


def main():
    for name, src in SOURCES.items():
        if not src.exists():
            print(f"  ! 없음: {src}")
            continue
        process(src, OUT / f"{name}.png")
    print(f"\n완료 → {OUT}")


if __name__ == "__main__":
    main()
