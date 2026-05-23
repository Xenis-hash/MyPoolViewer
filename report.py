"""MyPoolViewer — Phase 5 PDF Report (dark blueprint theme), 6 pages"""
import io, sys, os, math, math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, Color
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak, Image as RLImage)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas as rl_canvas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BG=HexColor("#0a0e1a"); PANEL=HexColor("#0f1628"); PANEL2=HexColor("#111d35")
EDGE=HexColor("#1a3050"); CYAN=HexColor("#4dd9ec"); TEAL=HexColor("#1a8fa0")
GOLD=HexColor("#c9a84c"); WHITE=HexColor("#f0f4f8"); MUTED=HexColor("#6b7fa3")
DIM=HexColor("#1e3a5a")
PW,PH=A4; ML=MR=14*mm; MT=14*mm; MB=12*mm; TW=PW-ML-MR

def S():
    return {
        "h1":   ParagraphStyle("h1",fontName="Helvetica-Bold",fontSize=26,textColor=CYAN,leading=32,spaceAfter=2),
        "h2":   ParagraphStyle("h2",fontName="Helvetica-Bold",fontSize=12,textColor=CYAN,leading=16,spaceBefore=8,spaceAfter=3),
        "h3":   ParagraphStyle("h3",fontName="Helvetica-Bold",fontSize=9,textColor=MUTED,leading=12,spaceBefore=6,spaceAfter=2),
        "sub":  ParagraphStyle("sub",fontName="Helvetica",fontSize=11,textColor=MUTED,leading=15),
        "tag":  ParagraphStyle("tag",fontName="Helvetica-Oblique",fontSize=9,textColor=MUTED,leading=12,spaceAfter=8),
        "body": ParagraphStyle("body",fontName="Helvetica",fontSize=8.5,textColor=WHITE,leading=12),
        "muted":ParagraphStyle("muted",fontName="Helvetica",fontSize=8,textColor=MUTED,leading=11),
        "lbl":  ParagraphStyle("lbl",fontName="Helvetica",fontSize=7,textColor=MUTED,leading=10),
        "val":  ParagraphStyle("val",fontName="Helvetica-Bold",fontSize=10.5,textColor=WHITE,leading=13),
        "code": ParagraphStyle("code",fontName="Courier",fontSize=7.5,textColor=CYAN,leading=10),
        "th":   ParagraphStyle("th",fontName="Helvetica-Bold",fontSize=7.5,textColor=CYAN,leading=10),
        "td":   ParagraphStyle("td",fontName="Helvetica",fontSize=8,textColor=WHITE,leading=10),
        "tdc":  ParagraphStyle("tdc",fontName="Courier",fontSize=7.5,textColor=CYAN,leading=10),
        "tdm":  ParagraphStyle("tdm",fontName="Helvetica",fontSize=7.5,textColor=MUTED,leading=10),
        "foot": ParagraphStyle("foot",fontName="Helvetica",fontSize=7,textColor=MUTED,leading=9,alignment=TA_CENTER),
    }

def _hr(w=0.5,c=None):
    return HRFlowable(width="100%",thickness=w,color=c or CYAN,spaceAfter=4,spaceBefore=4)

class _BG:
    def __init__(self,inp,pcref):
        self.inp=inp; self.pcref=pcref
    def __call__(self,canv,doc):
        canv.saveState(); p=doc.page; tot=self.pcref[0]; inp=self.inp
        canv.setFillColor(BG); canv.rect(0,0,PW,PH,fill=1,stroke=0)
        canv.setStrokeColor(Color(0.08,0.14,0.25)); canv.setLineWidth(0.25)
        for x in range(0,int(PW/mm)+1,10): canv.line(x*mm,0,x*mm,PH)
        for y in range(0,int(PH/mm)+1,10): canv.line(0,y*mm,PW,y*mm)
        if p>1:
            canv.setFillColor(PANEL); canv.rect(0,PH-MT-9*mm,PW,9*mm,fill=1,stroke=0)
            canv.setFillColor(CYAN);  canv.rect(0,PH-MT-9*mm,3,9*mm,fill=1,stroke=0)
            canv.setFont("Helvetica-Bold",8); canv.setFillColor(CYAN)
            canv.drawString(ML+5*mm,PH-MT-5*mm,"MyPoolViewer")
            canv.setFont("Helvetica",8); canv.setFillColor(MUTED)
            canv.drawString(ML+36*mm,PH-MT-5*mm,
                f"{inp.width_m} x {inp.length_m} x {inp.depth_m} m  "
                f"{inp.pool_type.title()} Pool  {inp.filtration.title()}")
        canv.setStrokeColor(DIM); canv.setLineWidth(0.4)
        canv.line(ML,MB+5*mm,PW-MR,MB+5*mm)
        canv.setFont("Helvetica",7); canv.setFillColor(MUTED)
        canv.drawString(ML,MB,"MyPoolViewer  Pool Configuration Report")
        canv.drawRightString(PW-MR,MB,f"Page {p} of {tot}  {datetime.now().strftime('%d %b %Y')}")
        if p==1:
            for (x,y,w,h) in [(0,PH-3,PW,3),(0,0,PW,3),(0,0,3,PH),(PW-3,0,3,PH)]:
                canv.setFillColor(CYAN); canv.rect(x,y,w,h,fill=1,stroke=0)
        canv.restoreState()

def _kpi(kpis,s):
    n=len(kpis); cw=TW/n
    data=[[Paragraph(f'<font size="6.5" color="#6b7fa3">{lbl}</font><br/>'
                     f'<font size="15" color="#f0f4f8"><b>{val}</b></font><br/>'
                     f'<font size="6.5" color="#6b7fa3">{unit}</font>',s["body"])
           for lbl,val,unit in kpis]]
    ts=TableStyle([("BACKGROUND",(0,0),(-1,-1),PANEL2),("BOX",(0,0),(-1,-1),0.5,CYAN),
                   ("INNERGRID",(0,0),(-1,-1),0.5,EDGE),("ALIGN",(0,0),(-1,-1),"CENTER"),
                   ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),7),
                   ("BOTTOMPADDING",(0,0),(-1,-1),7)])
    return Table(data,colWidths=[cw]*n,style=ts)

def _erow(label,comp,qty=1,s=None):
    s=s or S()
    if comp is None: return None
    if isinstance(comp,list):
        if not comp: return None
        qty=len(comp) if qty==1 else qty; comp=comp[0]
    q=f"x{qty}  " if qty>1 else ""
    return Table([[Paragraph(label,s["lbl"]),Paragraph(f"{q}{comp.model}",s["val"]),
                   Paragraph(comp.code,s["code"])]],
        colWidths=[34*mm,TW-34*mm-22*mm,22*mm],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),2),
                          ("BOTTOMPADDING",(0,0),(-1,-1),2),("LEFTPADDING",(0,0),(-1,-1),0),
                          ("RIGHTPADDING",(0,0),(-1,-1),0)]))

def _section(title,rows,s):
    parts=[Paragraph(title.upper(),s["h3"]),_hr(0.4)]
    for r in rows:
        if r: parts.append(r)
    parts.append(Spacer(1,4*mm)); return parts

def _row_style():
    return TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),PANEL),("BACKGROUND",(0,0),(0,-1),HexColor("#0d1930")),
        ("BOX",(0,0),(-1,-1),0.5,CYAN),("LINEBELOW",(0,0),(-1,-2),0.3,EDGE),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"MIDDLE")])

def _cover(inp,result,s):
    story=[]
    pl={"skimmer":"Skimmer Pool","overflow":"Overflow Pool","infinity":"Infinity Edge"}
    fl={"saltwater":"Salt Electrolysis","magnesium":"Magnesium Ionisation","chlorine":"Liquid Chlorine"}
    story.append(Spacer(1,20*mm))
    story.append(Paragraph("My<font color='#4dd9ec'>Pool</font>Viewer",s["h1"]))
    story.append(Paragraph("Pool Configuration Report",s["sub"]))
    story.append(Paragraph("Design your perfect pool. Configure every detail, in minutes.",s["tag"]))
    story.append(_hr(1.0,CYAN)); story.append(Spacer(1,6*mm))
    rows=[["Pool type",pl.get(inp.pool_type,inp.pool_type.title())],
          ["Dimensions",f"{inp.width_m} x {inp.length_m} m   avg. depth {inp.depth_m} m"],
          ["Filtration",fl.get(inp.filtration,inp.filtration.title())],
          ["Heating","Heat pump included" if inp.heating else "No heating"],
          ["Environment","Indoor" if inp.indoor else "Outdoor"],
          ["Liner / membrane",inp.liner_style.replace("-"," ").title()+" / "+inp.liner_color.replace("-"," ").title()]]
    tbl=[[Paragraph(k,s["lbl"]),Paragraph(v,s["body"])] for k,v in rows]
    story.append(Table(tbl,colWidths=[38*mm,TW-38*mm],style=_row_style()))
    story.append(Spacer(1,6*mm))
    kpis=[("Volume",f"{result.volume_m3:.0f}","m3"),("Surface",f"{result.surface_m2:.0f}","m2"),
          ("Design Flow",f"{result.design_flow_m3h:.1f}","m3/h"),("Turnover",f"{result.turnover_hours:.0f}","hours"),
          ("Engine Room",f"{result.engine_room_m2:.1f}","m2"),("BOM Items",f"{len(result.bom)}","lines")]
    story.append(_kpi(kpis,s)); story.append(Spacer(1,5*mm))
    if result.warnings:
        story.append(Paragraph("DESIGN NOTES",s["h3"]))
        for w in result.warnings: story.append(Paragraph(f"   {w}",s["muted"]))
    story.append(Spacer(1,18*mm)); story.append(_hr(0.3,MUTED))
    story.append(Paragraph(f"Generated by MyPoolViewer   {datetime.now().strftime('%d %B %Y  %H:%M')}",s["foot"]))
    story.append(PageBreak()); return story

def _blueprint_page(inp,result,s):
    """Render blueprint using matplotlib (no system Cairo library needed)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch
    import numpy as np

    # Colours
    BG_C    = '#0a0e1a'
    POOL_C  = '#0d3756'
    WATER_C = '#0e5080'
    EDGE_C  = '#4dd9ec'
    GOLD_C  = '#c9a84c'
    MUTED_C = '#6b7fa3'
    ER_C    = '#0f1628'
    ER_EDG  = '#6b7fa3'
    DRAIN_C = '#1a8fa0'
    LIGHT_C = '#f0e860'
    WHITE_C = '#f0f4f8'

    pw = inp.width_m
    pl = inp.length_m
    er_area = result.engine_room_m2
    er_d = max(2.5, (er_area / 1.5) ** 0.5)
    er_w = er_area / er_d
    gap  = 1.2

    fig_w = 14; fig_h = fig_w * 810 / 1260
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(BG_C)
    ax.set_facecolor(BG_C)

    # Pool body
    pool_rect = mpatches.Rectangle((0, 0), pw, pl, linewidth=2,
        edgecolor=EDGE_C, facecolor=WATER_C)
    ax.add_patch(pool_rect)

    # Water shimmer lines
    for i in range(1, 5):
        ax.axhline(pl * i / 5, xmin=0, xmax=pw/ax.get_xlim()[1] if ax.get_xlim()[1] else 1,
                   color=EDGE_C, alpha=0.15, linewidth=0.5)

    # Pool label
    ax.text(pw/2, pl/2, 'POOL\n' + f'{result.volume_m3:.0f} m3',
            ha='center', va='center', color=EDGE_C, fontsize=9,
            alpha=0.5, fontweight='bold')

    # Depth label
    ax.text(pw/2, pl*0.35, f'depth {inp.depth_m:.1f} m',
            ha='center', va='center', color=MUTED_C, fontsize=7, alpha=0.6)

    # Main drains (floor)
    n_drains = len(result.main_drains)
    for i in range(n_drains):
        dx = pw * (0.35 + i * 0.3)
        dy = pl * 0.75
        circle = plt.Circle((dx, dy), 0.18, color=DRAIN_C, zorder=3)
        ax.add_patch(circle)
        ax.plot([dx-0.14, dx+0.14], [dy, dy], color=EDGE_C, linewidth=0.8, zorder=4)
        ax.plot([dx, dx], [dy-0.14, dy+0.14], color=EDGE_C, linewidth=0.8, zorder=4)
    if n_drains:
        ax.text(pw*0.35, pl*0.75 - 0.35, f'DRAIN x{n_drains}',
                ha='center', va='top', color=DRAIN_C, fontsize=6.5)

    # Return inlets (walls)
    n_inlets = len(result.return_inlets)
    n_per = max(1, n_inlets // 2)
    for i in range(n_per):
        yp = pl * 0.2 + (pl * 0.6) * i / max(n_per - 1, 1)
        for xp in [0.1, pw - 0.1]:
            rect = mpatches.Rectangle((xp-0.12, yp-0.1), 0.24, 0.2,
                linewidth=1, edgecolor=EDGE_C, facecolor='#34b5cc', zorder=3)
            ax.add_patch(rect)
    if n_inlets:
        ax.text(0.1, pl*0.2 - 0.35, f'INLET x{n_inlets}',
                ha='center', va='top', color='#34b5cc', fontsize=6.5)

    # Lights
    n_lights = len(result.lighting)
    n_ps = max(1, n_lights // 2)
    for i in range(n_ps):
        ly = pl * 0.2 + (pl * 0.5) * i / max(n_ps - 1, 1)
        for lx in [pw * 0.08, pw * 0.92]:
            circle = plt.Circle((lx, ly), 0.15, color=LIGHT_C, zorder=3, alpha=0.9)
            ax.add_patch(circle)
    if n_lights:
        ax.text(pw*0.08, pl*0.2 - 0.35, f'LIGHT x{n_lights}',
                ha='center', va='top', color=LIGHT_C, fontsize=6.5)

    # Skimmer
    if inp.pool_type == 'skimmer':
        sk = mpatches.Rectangle((pw*0.4, -0.25), pw*0.2, 0.25,
            linewidth=1.5, edgecolor=EDGE_C, facecolor='#2a7fa0', zorder=3)
        ax.add_patch(sk)
        ax.text(pw*0.5, -0.35, 'SKM', ha='center', va='top',
                color=EDGE_C, fontsize=6.5)

    # Robot
    if result.robot_cleaner:
        rb = mpatches.Rectangle((pw*0.65, pl*0.6), 0.4, 0.25,
            linewidth=1, edgecolor=MUTED_C, facecolor='#3a4870', zorder=3)
        ax.add_patch(rb)
        ax.text(pw*0.65 + 0.2, pl*0.6 + 0.12, 'ROBOT',
                ha='center', va='center', color=WHITE_C, fontsize=5.5)

    # Engine room
    er_x0 = pw + gap
    er_y0 = (pl - er_d) / 2
    er_rect = mpatches.Rectangle((er_x0, er_y0), er_w, er_d,
        linewidth=1.5, edgecolor=ER_EDG, facecolor=ER_C, zorder=2)
    ax.add_patch(er_rect)
    ax.text(er_x0 + er_w/2, er_y0 + er_d + 0.25, 'ENGINE ROOM',
            ha='center', va='bottom', color=EDGE_C, fontsize=8, fontweight='bold')

    # Equipment blocks in ER
    equip = []
    if result.filter:   equip.append(('Filter', result.filter.code[:8], EDGE_C))
    if result.pump:     equip.append(('Pump', result.pump.code[:8], '#4dd9ec'))
    if result.treatment:equip.append(('Treatment', result.treatment.code[:8], GOLD_C))
    if result.heater:   equip.append(('Heater', result.heater.code[:8], GOLD_C))
    if result.automation:equip.append(('Auto', result.automation.code[:8], ER_EDG))
    if result.dehumidifier:equip.append(('Dehumid.', result.dehumidifier.code[:8], ER_EDG))

    cols = 2
    bw = (er_w - 0.4) / cols
    bh = min(0.65, (er_d - 0.4) / max(3, math.ceil(len(equip)/cols)))
    for i, (label, code, color) in enumerate(equip):
        col = i % cols; row = i // cols
        bx = er_x0 + 0.2 + col * bw
        by = er_y0 + er_d - 0.2 - (row + 1) * bh
        brect = mpatches.Rectangle((bx, by), bw - 0.1, bh - 0.05,
            linewidth=1, edgecolor=color, facecolor='#0a1020', zorder=3)
        ax.add_patch(brect)
        ax.text(bx + (bw-0.1)/2, by + (bh-0.05)/2, label + '\n' + code,
                ha='center', va='center', color=color, fontsize=5.5,
                multialignment='center')

    # Flow lines
    drain_mid = (pw * 0.5, pl * 0.75)
    er_in = (er_x0, er_y0 + er_d * 0.7)
    ax.annotate('', xy=er_in, xytext=drain_mid,
        arrowprops=dict(arrowstyle='->', color=EDGE_C, lw=1.2, linestyle='dashed'))
    er_out = (er_x0, er_y0 + er_d * 0.3)
    pool_ret = (0, pl * 0.3)
    ax.annotate('', xy=pool_ret, xytext=er_out,
        arrowprops=dict(arrowstyle='->', color=GOLD_C, lw=1.2, linestyle='dashed'))

    # Dimension annotations
    ax.annotate('', xy=(pw, pl + 0.6), xytext=(0, pl + 0.6),
        arrowprops=dict(arrowstyle='<->', color=MUTED_C, lw=1))
    ax.text(pw/2, pl + 0.75, f'{inp.width_m:.0f} m',
            ha='center', va='bottom', color=MUTED_C, fontsize=7.5)
    ax.annotate('', xy=(-0.6, pl), xytext=(-0.6, 0),
        arrowprops=dict(arrowstyle='<->', color=MUTED_C, lw=1))
    ax.text(-0.75, pl/2, f'{inp.length_m:.0f} m',
            ha='right', va='center', color=MUTED_C, fontsize=7.5)

    # Legend
    legend_items = [
        mpatches.Patch(color=DRAIN_C, label='Main Drain'),
        mpatches.Patch(color='#34b5cc', label='Return Inlet'),
        mpatches.Patch(color=LIGHT_C, label='LED Light'),
        mpatches.Patch(color=EDGE_C, label='Suction flow'),
        mpatches.Patch(color=GOLD_C, label='Return flow'),
    ]
    legend = ax.legend(handles=legend_items, loc='lower left',
        framealpha=0.3, facecolor=ER_C, edgecolor=EDGE_C,
        labelcolor=WHITE_C, fontsize=6.5)

    # Title bar
    pool_type_lbl = {'skimmer':'Skimmer','overflow':'Overflow','infinity':'Infinity Edge'}
    filt_lbl = {'saltwater':'Saltwater','magnesium':'Magnesium','chlorine':'Chlorine'}
    fig.text(0.01, 0.97,
        f"MyPoolViewer  |  Pool Blueprint — Top View  |  "
        f"{pool_type_lbl.get(inp.pool_type,inp.pool_type)}  "
        f"{inp.width_m}x{inp.length_m}x{inp.depth_m}m  "
        f"{filt_lbl.get(inp.filtration,inp.filtration)}  "
        f"{result.volume_m3:.0f}m³  |  BOM: {len(result.bom)} items",
        ha='left', va='top', color=MUTED_C, fontsize=7,
        transform=fig.transFigure)

    # Styling
    ax.set_xlim(-1.2, pw + gap + er_w + 0.5)
    ax.set_ylim(-0.8, pl + 1.2)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout(pad=0.3)

    buf2 = io.BytesIO()
    fig.savefig(buf2, format='png', dpi=130, facecolor=BG_C,
                bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    buf2.seek(0)

    png_data = buf2.getvalue()
    from PIL import Image as PILImage
    pil = PILImage.open(io.BytesIO(png_data))
    aspect = pil.height / pil.width
    img = RLImage(io.BytesIO(png_data), width=TW, height=TW * aspect)

    story = [Spacer(1,10*mm), Paragraph("Pool Blueprint",s["h2"]),
             Paragraph("Top-down annotated plan with pool components and engine room",s["muted"]),
             _hr(0.4), Spacer(1,3*mm), img, PageBreak()]
    return story

def _iso_page(inp,result,s):
    from iso3d import render_iso
    story=[Spacer(1,10*mm),Paragraph("3D Pool Visualisation",s["h2"]),
           Paragraph("Isometric projection of pool body and engine room with annotated components",s["muted"]),
           _hr(0.4),Spacer(1,3*mm)]
    png=render_iso(inp,result)
    img=RLImage(io.BytesIO(png),width=TW,height=TW*900/1600)
    story.append(img); story.append(PageBreak()); return story

def _equip_bom(inp,result,s):
    r=result; story=[]
    story.append(Spacer(1,10*mm)); story.append(Paragraph("Equipment Selection",s["h2"]))
    story.append(Paragraph("Sized from Fluidra AstralPool catalog for this configuration",s["muted"]))
    story.append(_hr(0.4)); story.append(Spacer(1,2*mm))
    story.extend(_section("Hydraulic Loop",[
        _erow("Filter",r.filter,s=s),
        _erow("Filter media",r.filter_media[0] if r.filter_media else None,s=s),
        _erow("Pump",r.pump,s=s),_erow("Valve manifold",r.valve_manifold,s=s),
        _erow("Strainer",r.strainer,s=s),_erow("Check valve",r.check_valve,s=s),
        _erow("Vib. damper",r.vibration_damper,s=s),_erow("Air blower",r.air_blower,s=s)],s))
    story.extend(_section("Treatment & HVAC",[
        _erow("Treatment",r.treatment,r.n_chlorinators,s),
        _erow("Heater",r.heater,s=s),_erow("Dehumidifier",r.dehumidifier,s=s),
        _erow("Automation",r.automation,s=s),_erow("Robot cleaner",r.robot_cleaner,s=s)],s))
    shell=[]
    if r.main_drains: shell.append(_erow("Main drains",r.main_drains,len(r.main_drains),s))
    if r.return_inlets: shell.append(_erow("Return inlets",r.return_inlets,len(r.return_inlets),s))
    if r.overflow_grilles: shell.append(_erow("Overflow grilles",r.overflow_grilles,len(r.overflow_grilles),s))
    if r.liner: shell.append(_erow("Liner",r.liner,s=s))
    if r.lighting: shell.append(_erow("Lighting",r.lighting,len(r.lighting),s))
    if r.light_transformer: shell.append(_erow("Transformer",r.light_transformer,s=s))
    story.extend(_section("Pool Shell & Finish",shell,s))
    story.append(Paragraph("Bill of Materials",s["h2"]))
    story.append(Paragraph(f"{len(r.bom)} line items",s["muted"]))
    story.append(_hr(0.4)); story.append(Spacer(1,2*mm))
    cws=[10*mm,32*mm,26*mm,TW-10*mm-32*mm-26*mm-28*mm,28*mm]
    hdr=[Paragraph(t,s["th"]) for t in ["QTY","CATEGORY","CODE","MODEL","NOTE"]]
    rows=[hdr]
    for item in r.bom:
        rows.append([Paragraph(str(item.get("qty",1)),s["td"]),
                     Paragraph(str(item.get("subcategory") or item.get("category","")),s["td"]),
                     Paragraph(str(item.get("code","")),s["tdc"]),
                     Paragraph(str(item.get("model","")),s["td"]),
                     Paragraph(str(item.get("note",""))[:55],s["tdm"])])
    bom_ts=TableStyle([("BACKGROUND",(0,0),(-1,0),HexColor("#0d1930")),
                       ("LINEBELOW",(0,0),(-1,0),0.8,CYAN),
                       *[("BACKGROUND",(0,i),(-1,i),PANEL) for i in range(2,len(rows),2)],
                       ("GRID",(0,0),(-1,-1),0.25,EDGE),("TOPPADDING",(0,0),(-1,-1),3),
                       ("BOTTOMPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),4),
                       ("RIGHTPADDING",(0,0),(-1,-1),4),("VALIGN",(0,0),(-1,-1),"TOP"),
                       ("ALIGN",(0,0),(0,-1),"CENTER")])
    story.append(Table(rows,colWidths=cws,style=bom_ts,repeatRows=1,splitByRow=True))
    return story

def generate_pdf(inp, result) -> bytes:
    buf=io.BytesIO(); pc=[1]; bg=_BG(inp,pc)
    def build(out):
        doc=SimpleDocTemplate(out,pagesize=A4,leftMargin=ML,rightMargin=MR,
            topMargin=MT+10*mm,bottomMargin=MB+8*mm,title="MyPoolViewer Pool Configuration Report")
        st=S()
        story=(_cover(inp,result,st)+_blueprint_page(inp,result,st)+
               _iso_page(inp,result,st)+_equip_bom(inp,result,st))
        doc.build(story,onFirstPage=bg,onLaterPages=bg); return doc.page
    dummy=io.BytesIO(); pc[0]=build(dummy); build(buf); return buf.getvalue()

if __name__=="__main__":
    from calculator import PoolInputs, calculate
    CSV=os.path.join(os.path.dirname(os.path.abspath(__file__)),"master_pool_components.csv")
    inp=PoolInputs(8,16,1.5,"skimmer","saltwater",heating=True,liner_style="touch",liner_color="elegance",light_color="rgbw")
    r=calculate(inp,CSV)
    pdf=generate_pdf(inp,r)
    out="/tmp/report_test.pdf"
    with open(out,"wb") as f: f.write(pdf)
    print(f"OK: {out}  {len(pdf)//1024}KB  {len(r.bom)} BOM items")
