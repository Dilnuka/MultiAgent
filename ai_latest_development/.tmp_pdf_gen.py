import os
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm

def md_to_pdf(md_text: str, out_path: Path):
    styles = getSampleStyleSheet()
    flowables = []
    def parse_bold(text: str) -> str:
        parts = text.split('**')
        for j in range(1, len(parts), 2):
            parts[j] = '<b>' + parts[j] + '</b>'
        return ''.join(parts)
    lines = md_text.splitlines()
    i = 0
    current_paragraph = []
    while i < len(lines):
        original_line = lines[i]
        line = original_line.strip()
        if line.startswith('#'):
            if current_paragraph:
                text = parse_bold(' '.join(current_paragraph))
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            level = 0
            while level < len(line) and line[level] == '#':
                level += 1
            text = parse_bold(line[level:].strip())
            heading_style = 'Heading' + str(min(level, 6))
            flowables.append(Paragraph(text, styles.get(heading_style, styles['Heading1'])))
        elif line.startswith('* ') or line.startswith('- '):
            if current_paragraph:
                text = parse_bold(' '.join(current_paragraph))
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            text = line[2:].strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(('* ', '- ', '#')) and '|' not in lines[i].strip() and not (lines[i].strip() and lines[i].strip()[0].isdigit() and '.' in lines[i].strip()) and lines[i].strip():
                text += ' ' + lines[i].strip()
                i += 1
            i -= 1
            text = parse_bold(text)
            flowables.append(Paragraph('\u2022 ' + text, styles.get('Bullet', styles['Normal'])))
        elif line and line[0].isdigit() and '.' in line:
            if current_paragraph:
                text = parse_bold(' '.join(current_paragraph))
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            try:
                num, rest = line.split('.', 1)
                num = int(num.strip())
                text = rest.strip()
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(('* ', '- ', '#')) and '|' not in lines[i].strip() and not (lines[i].strip() and lines[i].strip()[0].isdigit() and '.' in lines[i].strip()) and lines[i].strip():
                    text += ' ' + lines[i].strip()
                    i += 1
                i -= 1
                text = parse_bold(text)
                flowables.append(Paragraph(f"{num}. {text}", styles.get('Normal')))
            except ValueError:
                current_paragraph.append(original_line)
        elif line and '|' in line and (i + 1 < len(lines) and '|' in lines[i + 1]):
            if current_paragraph:
                text = parse_bold(' '.join(current_paragraph))
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            i -= 1
            data = []
            for tl in table_lines:
                cells = [cell.strip() for cell in tl.split('|') if cell.strip()]
                if cells:
                    data.append(cells)
            if len(data) > 1 and all(('-' in cell or ':' in cell) for cell in data[1]):
                data = data[0:1] + data[2:]
            if data:
                t = Table(data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                flowables.append(t)
        elif not line:
            if current_paragraph:
                text = parse_bold(' '.join(current_paragraph))
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            flowables.append(Spacer(1, 0.1 * mm))
        else:
            current_paragraph.append(original_line.strip())
        i += 1
    if current_paragraph:
        text = parse_bold(' '.join(current_paragraph))
        flowables.append(Paragraph(text, styles['Normal']))
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    doc.build(flowables)

candidates = [Path.cwd()/"report_formatted.md", Path.cwd()/"report.md", Path.cwd().parent/"report.md"]
md_path = next((p for p in candidates if p.exists()), None)
if not md_path:
    raise SystemExit("No report.md or report_formatted.md found.")
text = md_path.read_text(encoding='utf-8', errors='ignore')
out_path = (Path.cwd()/f"ai_risk_report_{datetime.now().strftime('%Y%m%d')}.pdf").resolve()
md_to_pdf(text, out_path)
print(str(out_path))
