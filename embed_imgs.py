#!/usr/bin/env python3
"""
검수 통과한 도식화(generated/{material}_{angle}.png) 9장을 vetti_toss.html에 임베드.
- IMGS를 재질×각도 중첩 구조로 교체: { croc:{1,2,3}, lizard:{1,2,3}, ostrich:{1,2,3} }
- 기존 1/2/3 평면 키를 쓰는 코드도 자동 호환되도록 loadImg 시그니처를 (mat, view)로 변경

사용법:
  python3 embed_imgs.py
"""
import re, base64, sys
from pathlib import Path

ROOT = Path(__file__).parent
GEN = ROOT / "generated" / "clean"   # postprocess_imgs.py 결과물
HTML = ROOT / "vetti_toss.html"

ANGLES = {1: "front", 2: "side", 3: "back"}
MATERIALS = ["croc", "lizard", "ostrich"]

CROC_FALLBACK = {}   # 후처리본에 croc도 포함되어 있으므로 fallback 불필요


def load_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def main():
    imgs = {}
    missing = []
    for m in MATERIALS:
        imgs[m] = {}
        for vid, ang in ANGLES.items():
            p = GEN / f"{m}_{ang}.png"
            if not p.exists():
                missing.append(f"{m}_{ang}.png")
                continue
            imgs[m][vid] = load_b64(p)
            print(f"  {m}/{ang}: {p.name} ({len(imgs[m][vid])} chars)")

    if missing:
        print(f"\n! 누락: {missing}", file=sys.stderr)
        print("generated/ 폴더에 위 파일들을 준비해주세요.", file=sys.stderr)
        sys.exit(1)

    # IMGS 블록 생성
    block = "const IMGS = {\n"
    for m in MATERIALS:
        block += f"  {m}: {{\n"
        for vid in (1, 2, 3):
            comma = "," if vid < 3 else ""
            block += f"    {vid}:'data:image/png;base64,{imgs[m][vid]}'{comma}\n"
        comma = "," if m != MATERIALS[-1] else ""
        block += f"  }}{comma}\n"
    block += "};\n"

    s = HTML.read_text()
    new = re.sub(r"const IMGS = \{[\s\S]*?^\};\n", block, s,
                 count=1, flags=re.MULTILINE)
    if new == s:
        print("! IMGS 블록을 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    HTML.write_text(new)
    print(f"\n임베드 완료. 파일 크기: {len(s):,} → {len(new):,} bytes")
    print("\n다음으로 vetti_toss.html에서 loadImg/colorize/renderPreview를 (mat, view) "
          "시그니처로 업데이트해야 합니다 — Claude에게 요청하세요.")


if __name__ == "__main__":
    main()
