# export_leaderboard_pdf.py
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
import csv
import os

input_file = "./data/leaderboard.csv"
output_dir = "./docs/tournament-charts"
output_file = os.path.join(output_dir, "leaderboard.pdf")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# === Dokumentlayout ===
doc = SimpleDocTemplate(
    output_file,
    pagesize=A4,
    leftMargin=10, rightMargin=10, topMargin=10, bottomMargin=10
)
elements = []

# === Titelstil ===
title_style = ParagraphStyle(
    name="SmallTitle",
    fontName="Helvetica-Bold",
    fontSize=14,
    alignment=1,
    spaceAfter=6
)

# === Legendenstil ===
legend_style = ParagraphStyle(
    name="Legend",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=colors.grey,
    alignment=1,  # zentriert
    spaceBefore=8
)

# === Titel ===
elements.append(Paragraph("Beyblade X Turnier 2 (12.11.2025) – Rangliste", title_style))
elements.append(Spacer(1, 6))

# === CSV einlesen ===
with open(input_file, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    data = list(reader)

# === Tabellenkopf anpassen ===
data[0] = ["Platz", "Bey", "ELO", "Sp", "S", "N", "WR", "GP", "VP", "Diff", "ΔPos", "ΔELO"]

# === Spaltenbreiten ===
col_widths = [25, 90, 50, 30, 30, 30, 30, 30, 30, 30, 30, 30]

# === Tabelle ===
table = Table(data, colWidths=col_widths, hAlign="CENTER")

table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
    ("TOPPADDING", (0, 1), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
]))

elements.append(table)

# === Legende hinzufügen ===
legend_text = (
    "<b>Legende:</b> "
    "<b>Sp</b> = Spiele, "
    "<b>S</b> = Siege, "
    "<b>N</b> = Niederlagen, "
    "<b>WR</b> = Siegquote/Win Rate (%), "
    "<b>GP</b> = Gewonnene Punkte, "
    "<b>VP</b> = Verlorene Punkte, "
    "<b>Diff</b> = Differenz (GP − VP)"
    ", <b>ΔPos</b> = Positionsdelta seit letztem Turnier"
    ", <b>ΔELO</b> = ELO-Differenz seit letztem Turnier"
)
elements.append(Paragraph(legend_text, legend_style))

# === PDF generieren ===
doc.build(elements)

print(f"Kompakte Rangliste mit Legende erstellt: {output_file}")
