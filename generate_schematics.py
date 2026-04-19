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
    "side":  REF_DIR / "Bag1(측면).png",
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

# 공통 품질 요건 — 모든 재질에 프리펜드됨
QUALITY_PREAMBLE = (
    "You are redrawing a handbag technical flat sketch in the style of a Hermès atelier "
    "production schematic. ABSOLUTE REQUIREMENTS — the output will be recolored downstream, "
    "so the drawing MUST be clean line-art suitable for digital color fill:\n"
    "• LINE WEIGHT: main silhouette 1.5–2px pure black (#000000). Internal construction "
    "  (seams, panel joins) 0.8–1px. Surface pattern lines 0.4–0.7px max.\n"
    "• INTERIOR FILL: the body inside the outline must read as PURE WHITE (#FFFFFF) "
    "  everywhere except the pattern marks themselves. NO gray fills, NO hatching, "
    "  NO scratchy pixels, NO cross-hatching, NO tonal shading, NO gradients.\n"
    "• SURFACE PATTERN: DRAWN SPARSELY. Pattern marks occupy at most 25–30% of the body "
    "  area (the rest is clean white). DO NOT fill the entire surface densely — restraint.\n"
    "• PATTERN CONSISTENCY: lines must be solid and closed (no broken/dashed artifacts, "
    "  no JPEG noise, no aliasing). Every pattern cell is a distinct closed shape.\n"
    "• BACKGROUND: pure white #FFFFFF outside the bag silhouette, no drop shadow, "
    "  no vignette, no paper texture.\n"
    "• CENTERING & MARGINS: bag is centered with ~8% margin on all sides.\n"
    "• ABSOLUTELY NO: color, gradients, soft shadows, photo-realistic shading, "
    "  textured paper, watermarks, text, dimension labels, rulers.\n"
    "KEEP the exact silhouette, handle shape, stitching positions, hardware positions, "
    "proportions, and overall outline strokes from the reference image — only the "
    "SURFACE PATTERN is allowed to change as described below.\n\n"
)

# 재질별 프롬프트 — QUALITY_PREAMBLE이 앞에 자동 붙음
MATERIAL_PROMPTS = {
    "croc": (
        "SURFACE PATTERN: authentic NILE CROCODILE belly scale pattern — a VERTICAL "
        "lattice of rectangular/square scales arranged in regular rows, each scale "
        "approximately 8–12mm at real scale. Larger more square scales in the center "
        "belly region (3–4 rows wide), tapering to smaller elongated scales near the "
        "side seams. Scales are drawn as simple closed quadrilaterals separated by "
        "thin 0.5px black gridlines — like a clean brick-wall pattern, NOT a dense "
        "crackled texture. Horn-back scales (if present) as a narrow top band of "
        "slightly raised circular bumps. Keep total pattern density SPARSE and ORDERLY."
    ),
    "lizard": (
        "SURFACE PATTERN: authentic TEJUS/MONITOR LIZARD skin — small IRREGULAR "
        "polygonal scales (mixed pentagon and hexagon shapes of varying sizes, 3–6mm "
        "each at real scale), organically tessellated. NOT a regular grid, NOT graph "
        "paper, NOT square cells. Scales flow along the body contour — slightly larger "
        "near the center and smaller near the edges. Draw only the scale outlines (thin "
        "0.5px black); interior of each scale stays pure white. SPARSE enough that "
        "~30% of body area is clean white between scale divisions."
    ),
    "ostrich": (
        "SURFACE PATTERN: authentic OSTRICH leather — scattered raised quill follicle "
        "BUMPS. Draw as small ROUND CIRCLES (2–4mm diameter at real scale) with a tiny "
        "crescent shadow on the lower-right side of each bump to suggest relief. "
        "Distribute ~80–120 bumps irregularly across the bag body, denser in the "
        "center panel and sparser near edges and seams. BETWEEN bumps the leather "
        "reads as smooth/plain pure white — NO scales, NO grid, NO hatching. "
        "This is the critical ostrich 'polka-dot relief' look."
    ),
}


def generate(client, material: str, angle: str, variant: int, size: str, quality: str):
    ref = REFS[angle]
    if not ref.exists():
        print(f"  ! 레퍼런스 없음: {ref}", file=sys.stderr)
        return None

    prompt = QUALITY_PREAMBLE + MATERIAL_PROMPTS[material] + "\n\n" + ANGLE_DETAILS.get(angle, "")
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

    materials = ["croc", "lizard", "ostrich"] if args.material == "all" else [args.material]
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
