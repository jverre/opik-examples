"""Generate the corpus: five fictional SOPs for the Fennmoor Cell Biology Lab.

Each SOP is a short numbered-section PDF. The numbers are deliberately
repetitive across documents (30 minutes appears in four of them, 15 in three,
6 months in two), so a retriever that grabs the wrong SOP produces a fluent,
wrong answer that still looks plausible.
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from . import SOP_DIR

_styles = getSampleStyleSheet()
TITLE = ParagraphStyle("T", parent=_styles["Title"], fontName="Helvetica-Bold", fontSize=15, spaceAfter=4)
META = ParagraphStyle("M", parent=_styles["Normal"], fontName="Helvetica-Oblique", fontSize=9, alignment=1, spaceAfter=14)
HEAD = ParagraphStyle("H", parent=_styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, spaceBefore=10, spaceAfter=3)
BODY = ParagraphStyle("B", parent=_styles["Normal"], fontName="Helvetica", fontSize=10, leading=13.5, spaceAfter=5)

SOPS: dict[str, dict] = {
    "SOP-101-reagent-preparation.pdf": {
        "title": "SOP-101 Reagent Preparation and Labeling",
        "meta": "Fennmoor Cell Biology Lab | Revision 4 | Owner: Dr. Ines Halvorsen",
        "sections": [
            ("1. Purpose", [
                "This SOP covers how stock reagents and buffers are prepared, labeled and "
                "retired in the Fennmoor Cell Biology Lab.",
            ]),
            ("2. Labeling", [
                "Every container must carry the reagent name, concentration, preparer's "
                "initials, preparation date and expiry date. An unlabeled container is treated "
                "as unknown chemical waste and discarded through the waste stream without "
                "further investigation.",
            ]),
            ("3. Tris-HCl Buffer", [
                "To prepare 1 M Tris-HCl at pH 8.0, dissolve 121.1 g of Tris base in 800 mL of "
                "ultrapure water, adjust the pH with concentrated HCl, make up to 1 L and "
                "filter-sterilize through a 0.22 micron filter. Tris-HCl buffer has a shelf "
                "life of 6 months at room temperature.",
            ]),
            ("4. Phosphate-Buffered Saline", [
                "10x PBS has a shelf life of 3 months at room temperature. Dilute to 1x with "
                "ultrapure water on the day of use. Diluted 1x PBS is stable for 7 days at 4 C.",
            ]),
            ("5. Paraformaldehyde", [
                "Prepare 4% paraformaldehyde (PFA) only inside a fume hood. Heat to no more "
                "than 60 C and never let it boil. Store aliquots at -20 C for up to 30 days. "
                "A thawed aliquot must not be refrozen.",
            ]),
            ("6. Flammable Solvents", [
                "Ethanol and acetone are stored in the flammable-liquids cabinet, never on open "
                "shelves. No more than 4 L of flammable solvent may be kept on the bench at "
                "any time.",
            ]),
            ("7. Expired Reagents", [
                "Expired reagents receive an orange EXPIRED sticker and are moved to the "
                "quarantine shelf within 2 working days. Quarantined reagents are disposed of "
                "at the next monthly chemical-waste collection.",
            ]),
        ],
    },
    "SOP-204-centrifuge-operation.pdf": {
        "title": "SOP-204 Benchtop Centrifuge Operation",
        "meta": "Fennmoor Cell Biology Lab | Revision 3 | Owner: Tomasz Brandt",
        "sections": [
            ("1. Scope", [
                "This SOP applies to the Marlow CF-16 benchtop centrifuge in Room 2.14 and its "
                "two rotors: the R-12 fixed-angle microtube rotor and the S-4 swing-bucket rotor.",
            ]),
            ("2. Balancing", [
                "Tubes placed opposite each other must be balanced. In the R-12 rotor the masses "
                "must match within 0.1 g. In the S-4 rotor, opposing buckets must match within "
                "0.5 g, including the bucket, adapter and tubes.",
            ]),
            ("3. Speed Limits", [
                "The R-12 rotor is rated to a maximum of 15,000 rpm. The S-4 rotor is rated to "
                "a maximum of 4,000 rpm, and 50 mL conical tubes may only be spun in the S-4 "
                "rotor. Never exceed the rated speed of the rotor in use.",
            ]),
            ("4. Running a Spin", [
                "Close the lid until it clicks. Stay at the centrifuge for the first 2 minutes of "
                "every run. Do not open the lid until the display reads 0 rpm, and never slow "
                "the rotor by hand.",
            ]),
            ("5. Tube Failure and Imbalance", [
                "If you hear a bang or the imbalance alarm sounds, press STOP and keep the lid "
                "closed for 30 minutes so that aerosols settle. Then notify the Lab Safety "
                "Officer before opening the lid. If liquid has leaked into the chamber, "
                "clean it up as described in the chemical spill procedure, SOP-310.",
            ]),
            ("6. Cleaning and Rotor Life", [
                "Wipe the chamber and rotors with 70% ethanol once a month. Inspect rotors for "
                "corrosion every 3 months. Retire any rotor after 5 years of service.",
            ]),
        ],
    },
    "SOP-310-chemical-spill-response.pdf": {
        "title": "SOP-310 Chemical Spill Response",
        "meta": "Fennmoor Cell Biology Lab | Revision 5 | Owner: Lab Safety Officer",
        "sections": [
            ("1. Small Spills", [
                "A small spill is less than 100 mL of a non-volatile, non-toxic liquid contained "
                "on the bench. Alert people nearby, put on double nitrile gloves and goggles, "
                "cover the spill with absorbent pads, place the used pads in the red spill-waste "
                "bucket, then wipe the area with water followed by 70% ethanol.",
            ]),
            ("2. Large Spills", [
                "A large spill is 100 mL or more, or any spill of a volatile or toxic liquid. "
                "Do not try to clean it up. Leave the room, close the door and call the Safety "
                "Desk on extension 5511.",
            ]),
            ("3. Skin or Eye Exposure", [
                "Flush the affected skin or eyes at the nearest eyewash or safety shower for 15 "
                "minutes and remove contaminated clothing while flushing. Tell the Lab Safety "
                "Officer before the end of the same shift.",
            ]),
            ("4. Mercury", [
                "Never vacuum a mercury spill. Use the mercury spill kit, a grey case kept in "
                "store room 2B.",
            ]),
            ("5. Biological Spills", [
                "Cover the spill with paper towels, flood it with fresh 10% bleach, and leave it "
                "for 20 minutes of contact time before wiping up. Dispose of the towels as "
                "biohazard waste under SOP-122.",
            ]),
            ("6. Reporting", [
                "Complete an incident form within 24 hours of any spill. The spill kit must be "
                "restocked within 1 week of use.",
            ]),
        ],
    },
    "SOP-122-autoclave-and-biohazard-waste.pdf": {
        "title": "SOP-122 Autoclave and Biohazard Waste",
        "meta": "Fennmoor Cell Biology Lab | Revision 2 | Owner: Tomasz Brandt",
        "sections": [
            ("1. Cycles", [
                "Solid biohazard waste runs on the solid cycle at 121 C and 15 psi for 30 "
                "minutes. Liquid waste runs on the liquid cycle at 121 C for 45 minutes, with "
                "bottle caps loosened.",
            ]),
            ("2. Loading Bags", [
                "Fill autoclave bags no more than three-quarters full and add 250 mL of water "
                "to each bag. Every bag gets indicator tape.",
            ]),
            ("3. Never Autoclave", [
                "Do not autoclave anything containing bleach, flammable solvents, "
                "paraformaldehyde or radioactive material.",
            ]),
            ("4. Opening the Door", [
                "Wait until the chamber reads 0 psi and below 80 C before opening the door. "
                "Wear heat-resistant gloves and a face shield.",
            ]),
            ("5. Verification", [
                "A biological indicator (Geobacillus spore strip) is run once a week. If an "
                "indicator fails, tag the autoclave out of service and reprocess the waste.",
            ]),
            ("6. Sharps", [
                "Close a sharps container when it reaches the fill line, which is "
                "three-quarters full, and place it in the autoclave on the solid cycle.",
            ]),
        ],
    },
    "SOP-150-ultra-low-freezer-management.pdf": {
        "title": "SOP-150 Ultra-Low Freezer Management",
        "meta": "Fennmoor Cell Biology Lab | Revision 3 | Owner: Dr. Ines Halvorsen",
        "sections": [
            ("1. Set Point and Logging", [
                "Ultra-low freezers run at a set point of -80 C. The alarm triggers at -70 C. "
                "Record the displayed temperature in the freezer log twice a day, at 9:00 "
                "and at 16:00.",
            ]),
            ("2. Door Discipline", [
                "Keep the freezer door open for less than 60 seconds at a time. Plan the "
                "retrieval before opening the door.",
            ]),
            ("3. Alarm Response", [
                "If the temperature stays above -70 C for more than 30 minutes, move the "
                "samples to the backup freezer FZ-02 and call Facilities on extension 5530.",
            ]),
            ("4. Inventory", [
                "Every box is labeled with its project code and owner. A full inventory audit is "
                "done every 6 months, and the freezer is defrosted once every 12 months.",
            ]),
            ("5. Dry Ice", [
                "Wear goggles and cryogenic gloves when handling dry ice. Never store dry ice "
                "in a sealed container, and only use it in a ventilated room.",
            ]),
        ],
    },
}


def build_pdfs(out_dir: Path = SOP_DIR) -> list[Path]:
    """Write every SOP PDF into out_dir and return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, sop in SOPS.items():
        path = out_dir / filename
        doc = SimpleDocTemplate(
            str(path), pagesize=LETTER, title=sop["title"], author="Fennmoor Cell Biology Lab",
            leftMargin=inch, rightMargin=inch, topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        )
        story = [Paragraph(sop["title"], TITLE), Paragraph(sop["meta"], META)]
        for heading, paragraphs in sop["sections"]:
            story.append(Paragraph(heading, HEAD))
            story.extend(Paragraph(text, BODY) for text in paragraphs)
        story.append(Spacer(1, 12))
        doc.build(story)
        paths.append(path)
    return paths


def ensure_pdfs() -> Path:
    """Generate the PDFs on first use."""
    if not list(SOP_DIR.glob("*.pdf")):
        build_pdfs()
    return SOP_DIR
