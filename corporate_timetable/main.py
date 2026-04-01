import json
import os
import shutil
from datetime import datetime
from io import BytesIO
from typing import List, Optional

from fastapi import FastAPI, Request, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)

from database import Base, engine, SessionLocal
from models import PlannerRecord


UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Corporate Weekly Planner")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class WeeklyRow(BaseModel):
    time: str
    monday: str
    tuesday: str
    wednesday: str
    thursday: str
    friday: str
    saturday: str
    sunday: str
    row_type: str = "normal"


class PlannerPayload(BaseModel):
    title: str
    organization: str
    department: str
    team: str
    week_range: str
    prepared_by: str
    notes: str
    logo_path: Optional[str] = None
    rows: List[WeeklyRow]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def safe_text(value: str) -> str:
    return (value or "").strip()


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def footer(canvas, doc):
    canvas.saveState()
    width, height = landscape(A4)

    canvas.setStrokeColorRGB(0.65, 0.7, 0.75)
    canvas.line(doc.leftMargin, 18, width - doc.rightMargin, 18)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.32, 0.37, 0.43)
    canvas.drawString(doc.leftMargin, 8, "Confidential – Internal Use Only")
    canvas.drawRightString(width - doc.rightMargin, 8, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    planners = db.query(PlannerRecord).order_by(PlannerRecord.id.desc()).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "planners": planners
        }
    )


@app.post("/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg"]:
        raise HTTPException(status_code=400, detail="Only PNG and JPG logos are allowed")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = f"logo_{timestamp}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"logo_path": filepath.replace("\\", "/")}


@app.post("/save-planner")
async def save_planner(payload: PlannerPayload, db: Session = Depends(get_db)):
    record = PlannerRecord(
        title=payload.title,
        organization=payload.organization,
        department=payload.department,
        team=payload.team,
        week_range=payload.week_range,
        prepared_by=payload.prepared_by,
        notes=payload.notes,
        logo_path=payload.logo_path,
        rows_json=json.dumps([row.dict() for row in payload.rows], ensure_ascii=False)
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"message": "Planner saved successfully", "planner_id": record.id}


@app.get("/load-planner/{planner_id}")
async def load_planner(planner_id: int, db: Session = Depends(get_db)):
    record = db.query(PlannerRecord).filter(PlannerRecord.id == planner_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Planner not found")

    return {
        "id": record.id,
        "title": record.title,
        "organization": record.organization,
        "department": record.department,
        "team": record.team,
        "week_range": record.week_range,
        "prepared_by": record.prepared_by,
        "notes": record.notes,
        "logo_path": record.logo_path,
        "rows": json.loads(record.rows_json)
    }


@app.post("/generate-pdf")
async def generate_pdf(payload: PlannerPayload):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=22,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="CorporateTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=8
    )

    banner_style = ParagraphStyle(
        name="BannerStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.white
    )

    meta_label_style = ParagraphStyle(
        name="MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0f172a")
    )

    meta_value_style = ParagraphStyle(
        name="MetaValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111827")
    )

    header_style = ParagraphStyle(
        name="HeaderStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.3,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.white
    )

    time_style = ParagraphStyle(
        name="TimeStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a")
    )

    body_style = ParagraphStyle(
        name="BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=9.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111827")
    )

    break_style = ParagraphStyle(
        name="BreakStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#334155")
    )

    notes_style = ParagraphStyle(
        name="NotesStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1f2937")
    )

    def para(text: str, style: ParagraphStyle) -> Paragraph:
        cleaned = escape_html(safe_text(text))
        if not cleaned:
            cleaned = " "
        cleaned = cleaned.replace("\n", "<br/>")
        return Paragraph(cleaned, style)

    story = []

    logo_path = safe_text(payload.logo_path)
    title_text = safe_text(payload.title) or "Weekly Corporate Planner"
    organization = safe_text(payload.organization) or "Organization"
    department = safe_text(payload.department) or "Department"
    team = safe_text(payload.team) or "Team"
    week_range = safe_text(payload.week_range) or "Week Range"
    prepared_by = safe_text(payload.prepared_by) or "Prepared By"
    notes = safe_text(payload.notes)
    generated_on = datetime.now().strftime("%d %b %Y, %I:%M %p")

    # Header block with optional logo
    if logo_path and os.path.exists(logo_path):
        logo = Image(logo_path, width=1.0 * inch, height=0.55 * inch)
        header_table = Table([
            [logo, Paragraph(title_text, title_style), para("", meta_value_style)]
        ], colWidths=[1.2 * inch, 8.2 * inch, 1.2 * inch])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph(title_text, title_style))

    story.append(Paragraph(f"{organization} • {department} • {team}", subtitle_style))

    banner = Table(
        [[Paragraph("CONFIDENTIAL – INTERNAL DISTRIBUTION ONLY", banner_style)]],
        colWidths=[10.85 * inch]
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#b91c1c")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#7f1d1d")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.12 * inch))

    meta_data = [
        [
            para("Organization", meta_label_style),
            para(organization, meta_value_style),
            para("Week", meta_label_style),
            para(week_range, meta_value_style),
        ],
        [
            para("Department", meta_label_style),
            para(department, meta_value_style),
            para("Prepared By", meta_label_style),
            para(prepared_by, meta_value_style),
        ],
        [
            para("Team", meta_label_style),
            para(team, meta_value_style),
            para("Generated On", meta_label_style),
            para(generated_on, meta_value_style),
        ],
    ]

    meta_table = Table(
        meta_data,
        colWidths=[1.15 * inch, 2.8 * inch, 1.05 * inch, 2.55 * inch]
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.18 * inch))

    table_data = [[
        para("Time Block", header_style),
        para("Monday", header_style),
        para("Tuesday", header_style),
        para("Wednesday", header_style),
        para("Thursday", header_style),
        para("Friday", header_style),
        para("Saturday", header_style),
        para("Sunday", header_style),
    ]]

    row_types = ["header"]

    for row in payload.rows:
        is_break = safe_text(row.row_type).lower() == "break"

        if is_break:
            break_label = safe_text(row.monday) or safe_text(row.time) or "Break"
            table_data.append([
                para(row.time, break_style),
                para(break_label, break_style),
                para(break_label, break_style),
                para(break_label, break_style),
                para(break_label, break_style),
                para(break_label, break_style),
                para(break_label, break_style),
                para(break_label, break_style),
            ])
            row_types.append("break")
        else:
            table_data.append([
                para(row.time, time_style),
                para(row.monday, body_style),
                para(row.tuesday, body_style),
                para(row.wednesday, body_style),
                para(row.thursday, body_style),
                para(row.friday, body_style),
                para(row.saturday, body_style),
                para(row.sunday, body_style),
            ])
            row_types.append("normal")

    planner_table = Table(
        table_data,
        colWidths=[
            1.22 * inch,
            1.38 * inch,
            1.38 * inch,
            1.38 * inch,
            1.38 * inch,
            1.38 * inch,
            1.38 * inch,
            1.38 * inch,
        ],
        repeatRows=1
    )

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d3557")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#eef4fb")),
        ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#475569")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#94a3b8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]

    for idx, row_type in enumerate(row_types[1:], start=1):
        if row_type == "break":
            style_cmds.extend([
                ("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#e2e8f0")),
                ("TEXTCOLOR", (0, idx), (-1, idx), colors.HexColor("#334155")),
            ])
        else:
            fill = "#ffffff" if idx % 2 == 1 else "#f8fafc"
            style_cmds.append(("BACKGROUND", (1, idx), (-1, idx), colors.HexColor(fill)))

    planner_table.setStyle(TableStyle(style_cmds))
    story.append(planner_table)

    if notes:
        story.append(Spacer(1, 0.18 * inch))
        notes_header = Table(
            [[Paragraph("Notes / Remarks", header_style)]],
            colWidths=[10.85 * inch]
        )
        notes_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1d3557")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#475569")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        notes_table = Table([[para(notes, notes_style)]], colWidths=[10.85 * inch])
        notes_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#94a3b8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(notes_header)
        story.append(notes_table)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)
    filename = title_text.lower().replace(" ", "_").replace("/", "_") + ".pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )