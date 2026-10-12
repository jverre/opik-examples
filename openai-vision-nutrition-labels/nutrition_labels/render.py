"""Draw six fictional nutrition labels with Pillow, plus the truth behind each.

Nothing here is a real product. Every label is generated locally into out/labels/
(git-ignored), and the same `Label.truth` dict that drives the drawing also writes
the test-suite assertions, so the pixels and the expected values cannot drift apart.

Three labels are clean. Three are deliberately hard:
  04_dual_column   per-100g and per-serving columns side by side
  05_rotated       the whole panel photographed at a tilt
  06_low_contrast  grey ink on grey paper, slightly blurred
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

LABEL_DIR = Path("out/labels")
INK = (20, 20, 20)
PAPER = (252, 252, 250)


@dataclass
class Label:
    slug: str
    kind: str
    truth: dict  # per-serving values, the keys of NutritionFacts
    draw: Callable[["Label"], Image.Image]
    hard: bool = False

    @property
    def path(self) -> Path:
        return LABEL_DIR / f"{self.slug}.png"

    def assertions(self) -> list[str]:
        """Two plain-language checks that carry this label's expected values."""
        t = self.truth
        allergens = ", ".join(t["allergens"])
        return [
            f"The product is {t['product_name']}, the serving size is {t['serving_size_g']:g} g, "
            f"and calories is {t['calories']:g} (kcal, per serving)",
            f"Per serving, total fat is {t['total_fat_g']:g} g, carbs {t['total_carbs_g']:g} g, "
            f"protein {t['protein_g']:g} g, sodium {t['sodium_mg']:g} mg, and the allergens are "
            f"exactly: {allergens}",
        ]


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def text(d: ImageDraw.ImageDraw, xy, s: str, size: int, bold: bool = False, fill=INK, anchor="la"):
    d.text(xy, s, font=font(size), fill=fill, stroke_width=1 if bold else 0, stroke_fill=fill, anchor=anchor)


def rule(d: ImageDraw.ImageDraw, y: int, x0: int, x1: int, width: int = 2, fill=INK):
    d.line([(x0, y), (x1, y)], fill=fill, width=width)


# --- US "Nutrition Facts" panel ----------------------------------------------


def us_panel(
    label: Label,
    *,
    ink=INK,
    paper=PAPER,
    size: tuple[int, int] = (560, 760),
    scale: float = 1.0,
    servings_text: str = "about 8 servings per container",
    serving_text: str | None = None,
    footer: list[str] | None = None,
) -> Image.Image:
    t = label.truth
    img = Image.new("RGB", size, paper)
    d = ImageDraw.Draw(img)
    x0, x1 = 30, size[0] - 30

    def s(n: float) -> int:
        return round(n * scale)

    d.rectangle([x0 - 8, 16, x1 + 8, size[1] - 16], outline=ink, width=3)
    text(d, (x0, 28), "Nutrition Facts", s(44), bold=True, fill=ink)
    text(d, (x0, 28 + s(56)), t["product_name"], s(22), fill=ink)
    y = 28 + s(92)
    text(d, (x0, y), servings_text, s(20), fill=ink)
    y += s(28)
    text(d, (x0, y), "Serving size", s(22), bold=True, fill=ink)
    text(d, (x1, y), serving_text or f"{t['serving_size_g']:g} g", s(22), bold=True, fill=ink, anchor="ra")
    y += s(34)
    rule(d, y, x0, x1, 10, ink)
    y += s(14)
    text(d, (x0, y), "Amount per serving", s(18), bold=True, fill=ink)
    y += s(24)
    text(d, (x0, y), "Calories", s(34), bold=True, fill=ink)
    text(d, (x1, y), f"{t['calories']:g}", s(40), bold=True, fill=ink, anchor="ra")
    y += s(52)
    rule(d, y, x0, x1, 6, ink)
    y += s(8)
    for name, value in [
        ("Total Fat", f"{t['total_fat_g']:g} g"),
        ("Sodium", f"{t['sodium_mg']:g} mg"),
        ("Total Carbohydrate", f"{t['total_carbs_g']:g} g"),
        ("Protein", f"{t['protein_g']:g} g"),
    ]:
        text(d, (x0, y), name, s(22), bold=True, fill=ink)
        text(d, (x1, y), value, s(22), fill=ink, anchor="ra")
        y += s(32)
        rule(d, y, x0, x1, 1, ink)
        y += s(8)
    y += s(14)
    for line in footer or []:
        text(d, (x0, y), line, s(17), fill=ink)
        y += s(24)
    return img


def draw_oat_clusters(label: Label) -> Image.Image:
    return us_panel(
        label,
        footer=[
            "INGREDIENTS: whole grain oats, honey, almonds,",
            "wheat flour, sunflower oil, sea salt.",
            "",
            "Contains: almonds, wheat.",
        ],
    )


def draw_lentil_soup(label: Label) -> Image.Image:
    return us_panel(
        label,
        servings_text="2 servings per container",
        serving_text="1 cup (245 g)",
        footer=[
            "INGREDIENTS: lentils, carrots, onion, vegetable",
            "broth, cream, tamari, olive oil, black pepper.",
            "",
            "Contains: milk, soy.",
            "May contain traces of peanuts.",
        ],
    )


# --- EU style table, per 100 g only --------------------------------------------


def draw_seed_crackers(label: Label) -> Image.Image:
    t = label.truth
    img = Image.new("RGB", (620, 640), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 600, 620], outline=INK, width=2)
    text(d, (44, 40), t["product_name"], 30, bold=True)
    text(d, (44, 84), "Nutrition information", 22)
    text(d, (580, 84), "per 100 g", 22, bold=True, anchor="ra")
    y = 120
    rule(d, y, 44, 580, 3)
    y += 14
    rows = [
        ("Energy", "1046 kJ / 250 kcal"),
        ("Fat", f"{t['total_fat_g']:g} g"),
        ("  of which saturates", "2.1 g"),
        ("Carbohydrate", f"{t['total_carbs_g']:g} g"),
        ("  of which sugars", "3.0 g"),
        ("Protein", f"{t['protein_g']:g} g"),
        ("Sodium", f"{t['sodium_mg']:g} mg"),
    ]
    for name, value in rows:
        text(d, (44, y), name, 24)
        text(d, (580, y), value, 24, anchor="ra")
        y += 38
        rule(d, y, 44, 580, 1)
        y += 10
    y += 20
    text(d, (44, y), "Ingredients: wheat flour, sesame seeds, flaxseed,", 20)
    text(d, (44, y + 28), "rapeseed oil, sea salt, yeast.", 20)
    text(d, (44, y + 66), "Allergens: sesame, wheat.", 22, bold=True)
    return img


# --- Hard 1: per-100g and per-serving columns -----------------------------------


def draw_dual_column(label: Label) -> Image.Image:
    t = label.truth
    per100 = {"cal": 470, "fat": 18, "carb": 66, "pro": 9, "na": 180}
    k = t["serving_size_g"] / 100
    assert round(per100["cal"] * k) == round(t["calories"])  # truth matches the drawn columns
    img = Image.new("RGB", (700, 700), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 680, 680], outline=INK, width=2)
    text(d, (44, 40), t["product_name"], 30, bold=True)
    text(d, (44, 84), "Typical values", 22)
    text(d, (420, 84), "per 100 g", 22, bold=True, anchor="ra")
    text(d, (636, 84), f"per {t['serving_size_g']:g} g serving", 22, bold=True, anchor="ra")
    y = 120
    rule(d, y, 44, 636, 3)
    y += 14
    rows = [
        ("Energy (kcal)", per100["cal"], t["calories"]),
        ("Fat (g)", per100["fat"], t["total_fat_g"]),
        ("Carbohydrate (g)", per100["carb"], t["total_carbs_g"]),
        ("Protein (g)", per100["pro"], t["protein_g"]),
        ("Sodium (mg)", per100["na"], t["sodium_mg"]),
    ]
    for name, a, b in rows:
        text(d, (44, y), name, 24)
        text(d, (420, y), f"{a:g}", 28, bold=True, anchor="ra")  # the 100 g column is the loud one
        text(d, (636, y), f"{b:g}", 22, anchor="ra")
        y += 40
        rule(d, y, 44, 636, 1)
        y += 10
    y += 24
    text(d, (44, y), "Ingredients: rolled oats, maple syrup, hazelnuts,", 20)
    text(d, (44, y + 28), "coconut oil, milk powder, salt.", 20)
    text(d, (44, y + 66), "Contains: hazelnuts, milk, oats.", 22, bold=True)
    return img


# --- Hard 2: photographed at a tilt ---------------------------------------------


def draw_rotated(label: Label) -> Image.Image:
    panel = us_panel(
        label,
        size=(500, 640),
        scale=0.82,
        servings_text="about 6 servings per container",
        serving_text="2 cups (38 g)",
        footer=["Contains: peanuts, milk, soy."],
    )
    table = Image.new("RGB", (760, 820), (205, 198, 188))
    rotated = panel.rotate(23, expand=True, resample=Image.BICUBIC, fillcolor=(205, 198, 188))
    table.paste(rotated, ((760 - rotated.width) // 2, (820 - rotated.height) // 2))
    return table


# --- Hard 3: grey ink on grey paper ---------------------------------------------


def draw_low_contrast(label: Label) -> Image.Image:
    img = us_panel(
        label,
        ink=(150, 150, 150),
        paper=(196, 196, 196),
        scale=0.9,
        size=(500, 680),
        servings_text="about 10 servings per container",
        footer=["Contains: cashews, soy."],
    )
    return img.filter(ImageFilter.GaussianBlur(1.4))


LABELS: list[Label] = [
    Label(
        "01_oat_clusters",
        "clean US panel",
        dict(product_name="Fernwood Oat Clusters", serving_size_g=40, calories=170, total_fat_g=6,
             total_carbs_g=27, protein_g=4, sodium_mg=95, allergens=["almonds", "wheat"]),
        draw_oat_clusters,
    ),
    Label(
        "02_lentil_soup",
        "US panel with a 'may contain' trap",
        dict(product_name="Harbor Lentil Soup", serving_size_g=245, calories=130, total_fat_g=3.5,
             total_carbs_g=21, protein_g=8, sodium_mg=640, allergens=["milk", "soy"]),
        draw_lentil_soup,
    ),
    Label(
        "03_seed_crackers",
        "EU table, per 100 g only, kJ before kcal",
        dict(product_name="Brightwell Seed Crackers", serving_size_g=100, calories=250, total_fat_g=9,
             total_carbs_g=34, protein_g=11, sodium_mg=440, allergens=["sesame", "wheat"]),
        draw_seed_crackers,
    ),
    Label(
        "04_dual_column",
        "per-100g and per-serving columns, the 100 g one is louder",
        dict(product_name="Marlow Maple Granola", serving_size_g=30, calories=141, total_fat_g=5.4,
             total_carbs_g=19.8, protein_g=2.7, sodium_mg=54, allergens=["hazelnuts", "milk", "oats"]),
        draw_dual_column,
        hard=True,
    ),
    Label(
        "05_rotated",
        "US panel photographed at a 23 degree tilt",
        dict(product_name="Copperfield Peanut Cups", serving_size_g=38, calories=210, total_fat_g=13,
             total_carbs_g=21, protein_g=5, sodium_mg=115, allergens=["peanuts", "milk", "soy"]),
        draw_rotated,
        hard=True,
    ),
    Label(
        "06_low_contrast",
        "grey ink on grey paper, blurred",
        dict(product_name="Pinecrest Trail Mix", serving_size_g=40, calories=190, total_fat_g=12,
             total_carbs_g=15, protein_g=6, sodium_mg=85, allergens=["cashews", "soy"]),
        draw_low_contrast,
        hard=True,
    ),
]


def get_label(slug_or_path: str) -> Label | None:
    stem = Path(slug_or_path).stem
    return next((label for label in LABELS if label.slug == stem), None)


def render_all() -> list[Path]:
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for label in LABELS:
        label.draw(label).save(label.path)
        paths.append(label.path)
    return paths
