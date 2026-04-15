#!/usr/bin/env python3
"""
VETTI 도식화 일괄 생성기
- 기존 크로커다일 도식(Bag1 정/측/후)을 레퍼런스로 OpenAI gpt-image-1(edit) 호출
- 리자드 / 오스트리치 변형을 생성해 generated/ 폴더에 저장
- 검수 후 마음에 드는 것만 골라서 embed_imgs.py로 HTML에 임베드

사용법:
  export OPENAI_API_KEY=sk-...
  python3 generate_schematics.py                 # 모두 생성 (lizard + ostrich)
  python3 generate_schematics.py lizard          # 특정 재질만
  python3 generate_schematics.py lizard front    # 특정 재질·각도만
  python3 generate_schematics.py --variants 3    # 각 항목당 N개 후보 생성

생성되는 파일: generated/{material}_{angle}_v{n}.png
"""
import os, sys, base64, argparse
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("openai 패키지 필요: pip3 install --user openai", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent
REF_DIR = Path("/Users/junkim/Desktop/베티(VETTI)/이미지 레퍼런스")
OUT_DIR = ROOT / "generated"
OUT_DIR.mkdir(exist_ok=True)

REFS = {
    "front": REF_DIR / "Bag1(정면).png",
    "side":  Path("/Users/junkim/Desktop/악어 가죽 핸드백 선형 드로잉.png"),
    "back":  REF_DIR / "Bag1(후면).png",
}

# 각도별 디테일 보존 지시 — 프롬프트에 합쳐짐
ANGLE_DETAILS = {
    "front": "Keep the front view layout with two symmetric handles, center closure, and base feet.",
    "side": (
        "CRITICAL — this is a SIDE profile view with a highly distinctive shape. You MUST "
        "reproduce ALL of these features exactly as in the reference: "
        "(1) The body must be a narrow tapered silhouette — very narrow at top, widest at "
        "bottom, roughly triangular wedge shape. "
        "(2) THE DOMINANT FEATURE is a LARGE V-SHAPED TRIANGULAR OPENING/GUSSET in the center "
        "of the side panel — it is a deep triangular fold that occupies roughly 30-40% of the "
        "side face area, pointing downward from the top opening to a point near the bottom "
        "center. This V-fold must be drawn as two strong black lines forming an inverted "
        "triangle — DO NOT flatten it into a single vertical line, DO NOT omit it. "
        "(3) On the LEFT side near the top, a hanging leather TASSEL/CHARM with a key fob "
        "(small rectangle + fringed tassel strands underneath). "
        "(4) A small D-RING metal hardware at the very top center where handles converge. "
        "(5) Two curved top handles visible from the side (thin elongated ovals). "
        "(6) ABSOLUTELY NO bottom base band, NO horizontal stitching line at the bottom, "
        "NO visible feet, NO bottom hem, NO folded flange. The leather pattern continues "
        "smoothly all the way down and the bag simply ends at a clean bottom edge. "
        "The bottom must be completely featureless — just the outline. "
        "The leather pattern applies ONLY to the outer body panels (left and right of the "
        "V-fold), NOT inside the V-fold (which stays blank/plain interior)."
    ),
    "back": "Keep the back view layout with two symmetric handles and base feet.",
}

# 재질별 프롬프트 — 형태는 유지하고 가죽 표면 패턴만 바꾸도록 명시
MATERIAL_PROMPTS = {
    "lizard": (
        "Redraw this luxury handbag technical flat sketch, KEEPING the exact silhouette, "
        "handles, stitching lines, hardware, proportions, and outline strokes identical. "
        "Replace ONLY the body surface pattern with authentic LIZARD (tejus/monitor) skin: "
        "densely packed, SMALL IRREGULAR POLYGONAL SCALES (pentagon/hexagon shapes of varying "
        "sizes roughly 3-6mm each at real scale), organically tessellated with slight size "
        "variation — NOT a regular grid, NOT graph paper, NOT square cells. Scales should "
        "flow along the body contour, slightly larger near the center and smaller near edges. "
        "Style: crisp black line-art, Hermès/Bottega technical flat sketch, pure white "
        "background, NO shading, NO gradients, NO color, NO shadows."
    ),
    "ostrich": (
        "Redraw this luxury handbag technical flat sketch, KEEPING the exact silhouette, "
        "handles, stitching lines, hardware, proportions, and outline strokes identical. "
        "Replace ONLY the body surface pattern with authentic OSTRICH leather texture: "
        "scattered raised quill follicle BUMPS — small round circles (2-4mm diameter) with "
        "slight shadow underside, irregularly distributed across the bag body (approximately "
        "100-140 bumps), denser in center and sparser near edges. Between bumps the leather "
        "should read as smooth/plain (NO scales, NO grid). Style: crisp black line-art, "
        "Hermès technical flat sketch, pure white background, NO shading on body, NO color."
    ),
    "croc": (
        "Redraw this handbag technical schematic exactly as shown, keeping the silhouette, "
        "handles, stitching, hardware, proportions, and crocodile scale pattern. "
        "Pure black line-art on a clean white background, fashion technical illustration style."
    ),
}


def generate(client, material: str, angle: str, variant: int, size: str, quality: str):
    ref = REFS[angle]
    if not ref.exists():
        print(f"  ! 레퍼런스 없음: {ref}", file=sys.stderr)
        return None

    prompt = MATERIAL_PROMPTS[material] + " " + ANGLE_DETAILS.get(angle, "")
    print(f"  → {material}/{angle} v{variant} 생성 중...")

    with open(ref, "rb") as fh:
        resp = client.images.edit(
            model="gpt-image-1",
            image=fh,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )

    b64 = resp.data[0].b64_json
    out = OUT_DIR / f"{material}_{angle}_v{variant}.png"
    out.write_bytes(base64.b64decode(b64))
    print(f"     ✓ {out.relative_to(ROOT)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("material", nargs="?", choices=["lizard", "ostrich", "croc", "all"],
                    default="all")
    ap.add_argument("angle", nargs="?", choices=["front", "side", "back", "all"],
                    default="all")
    ap.add_argument("--variants", type=int, default=2,
                    help="각 항목당 생성할 후보 수 (기본 2)")
    ap.add_argument("--size", default="1024x1024",
                    choices=["1024x1024", "1536x1024", "1024x1536"])
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("환경변수 OPENAI_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI()

    materials = ["lizard", "ostrich"] if args.material == "all" else [args.material]
    angles = ["front", "side", "back"] if args.angle == "all" else [args.angle]

    total = len(materials) * len(angles) * args.variants
    print(f"총 {total}장 생성 시작 (재질 {len(materials)}, 각도 {len(angles)}, "
          f"후보 {args.variants}, quality={args.quality})\n")

    done = 0
    for m in materials:
        for a in angles:
            for v in range(1, args.variants + 1):
                try:
                    generate(client, m, a, v, args.size, args.quality)
                    done += 1
                except Exception as e:
                    print(f"  ! 실패: {e}", file=sys.stderr)
        print()

    print(f"\n완료: {done}/{total}장 → {OUT_DIR}")
    print("검수 후 채택할 파일을 다음 이름으로 리네임 해주세요:")
    print("  {material}_{angle}.png  (예: lizard_front.png)")
    print("그리고 embed_imgs.py를 실행하세요.")


if __name__ == "__main__":
    main()
