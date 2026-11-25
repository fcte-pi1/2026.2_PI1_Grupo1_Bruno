"""Renderiza o Markdown versionado e anexa os mesmos bytes ao PDF.

Dependências: reportlab, pypdf. Execução a partir da raiz do repositório:
python tools/gerar_pdf_integracao.py
"""
from pathlib import Path
import re
import hashlib
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/7.5 - Testes de integração.md'
TARGET = ROOT / 'output/pdf/testes-integracao-micromouse.pdf'

def inline(value):
    value = escape(value)
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: '<link href="' + escape(m[2], quote=True) + '">' + m[1] + '</link>', value)
    value = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', value)
    return value.replace('`', '')

def generate():
    raw = SOURCE.read_bytes()
    lines = raw.decode('utf-8-sig').splitlines()
    styles = getSampleStyleSheet()
    for name in ('Heading1', 'Heading2', 'Heading3'):
        styles[name].keepWithNext = True
    styles.add(ParagraphStyle(name='BodyReport', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=7))
    styles.add(ParagraphStyle(name='CellReport', fontName='Helvetica', fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='CodeReport', fontName='Courier', fontSize=8, leading=11, spaceAfter=8))
    story = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1; continue
        if line.startswith('```'):
            code = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            story.append(Preformatted('\n'.join(code), styles['CodeReport'], maxLineLength=150))
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                    rows.append([Paragraph(inline(c), styles['CellReport']) for c in cells])
                i += 1
            n = len(rows[0]); width = landscape(A3)[0] - 72
            widths = ([28,100,54,57,68,67,124,155,60,66,round(width-779)] if n == 11 else [width/n]*n)
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE8EF')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#9BAEB9')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([table, Spacer(1,12)]); continue
        elif line.startswith('#'):
            depth = len(line)-len(line.lstrip('#'))
            story.append(Paragraph(inline(line.lstrip('#').strip()), styles['Heading'+str(min(depth,3))]))
        else:
            para = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','- ')):
                para.append(lines[i]); i += 1
            story.append(Paragraph(inline(' '.join(para)), styles['BodyReport'])); continue
        i += 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    temp = TARGET.with_suffix('.render.pdf')
    def footer(canvas, doc):
        canvas.setFont('Helvetica',8)
        canvas.drawString(36,24,'Micromouse | Testes de Integração | 24/11/2026')
        canvas.drawRightString(landscape(A3)[0]-36,24,str(doc.page))
    SimpleDocTemplate(str(temp),pagesize=landscape(A3),rightMargin=36,leftMargin=36,topMargin=32,bottomMargin=42,title='Testes de Integração - Micromouse',author='Equipe Micromouse').build(story,onFirstPage=footer,onLaterPages=footer)
    writer = PdfWriter(clone_from=str(temp))
    writer.add_attachment(SOURCE.name, raw)
    sha = hashlib.sha256(raw).hexdigest()
    writer.add_metadata({'/MarkdownSHA256':sha, '/SourceMarkdown':SOURCE.relative_to(ROOT).as_posix()})
    with TARGET.open('wb') as f: writer.write(f)
    temp.unlink()
    reader = PdfReader(TARGET)
    assert reader.attachments[SOURCE.name][0] == raw
    assert reader.metadata['/MarkdownSHA256'] == sha
    print(f'{TARGET}\nMarkdown SHA-256: {sha}\nPáginas: {len(reader.pages)}')

if __name__ == '__main__':
    generate()
