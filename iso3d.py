"""
MyPoolViewer - Phase 5: Isometric 3D Pool Visualizer
"""
import math, io, numpy as np
from PIL import Image, ImageDraw, ImageFont

BG=(10,14,26); POOL_WATER=(12,55,90); POOL_EDGE=(77,217,236)
POOL_FLOOR=(14,42,72); WALL_DARK=(8,25,50); WALL_TOP=(16,65,100)
DECK_COLOR=(20,30,52); DECK_EDGE=(40,65,100); ER_FILL=(18,28,50)
ER_EDGE=(107,127,163); EQUIP_FILL=(15,30,58); EQUIP_EDGE=(26,143,160)
GOLD=(232,180,74); CYAN=(77,217,236); WHITE=(240,244,248); MUTED=(107,127,163)
DRAIN_C=(26,143,160); INLET_C=(34,181,204); LIGHT_C=(240,232,96)
SKIMMER_C=(42,127,160); ROBOT_C=(136,152,200)
W,H=1600,900

def _poly(draw,pts,fill=None,outline=None,width=1):
    if fill: draw.polygon(pts,fill=fill)
    if outline: draw.line(pts+[pts[0]],fill=outline,width=width)

def _label(draw,pt,text,color=WHITE,size=13,anchor='mm'):
    try: fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)
    except: fnt=ImageFont.load_default()
    draw.text(pt,text,font=fnt,fill=color,anchor=anchor)

def _label_bold(draw,pt,text,color=CYAN,size=14):
    try: fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',size)
    except: fnt=ImageFont.load_default()
    draw.text(pt,text,font=fnt,fill=color,anchor='mm')

def render_iso(inp, result) -> bytes:
    img=Image.new('RGB',(W,H),BG); draw=ImageDraw.Draw(img,'RGBA')
    pw=min(inp.width_m,20); pl=min(inp.length_m,30); pd=min(inp.depth_m,2.5)
    er_area=result.engine_room_m2
    er_depth=max(2.5,math.sqrt(er_area/1.6)); er_width=er_area/er_depth
    gap=1.5
    scene_w=pw+gap+er_width; scene_d=max(pl,er_depth)+1.0
    s_x=900/(scene_w+scene_d*0.5); s_y=420/(scene_d*0.5+pw*0.25)
    s=min(s_x,s_y,62); sy=s*0.58
    ox=int(W*0.08+scene_d*0.5*s); oy=int(H*0.68)

    def iso(x,y,z):
        px=ox+int((x-y*0.5)*s); py=oy-int((x*0.25+y*0.5)*s)-int(z*sy*2.2)
        return (px,py)

    def cube_face(corners,fill,edge=None,ew=1):
        pts=[iso(*c) for c in corners]; _poly(draw,pts,fill=fill,outline=edge,width=ew)

    deck=0.6
    cube_face([(-deck,pl+deck,0),(pw+deck,pl+deck,0),(pw+deck,pl+deck,0.12),(-deck,pl+deck,0.12)],DECK_COLOR,DECK_EDGE)
    cube_face([(-deck,-deck,0.12),(pw+deck,-deck,0.12),(pw+deck,pl+deck,0.12),(-deck,pl+deck,0.12)],(24,36,62),DECK_EDGE)
    cube_face([(0,pl,0),(pw,pl,0),(pw,pl,-pd),(0,pl,-pd)],WALL_DARK,POOL_EDGE,1)
    cube_face([(pw,0,0),(pw,pl,0),(pw,pl,-pd),(pw,0,-pd)],WALL_TOP,POOL_EDGE,1)
    cube_face([(0,0,0),(0,pl,0),(0,pl,-pd),(0,0,-pd)],WALL_DARK,POOL_EDGE,1)
    cube_face([(0,0,0),(pw,0,0),(pw,0,-pd),(0,0,-pd)],WALL_TOP,POOL_EDGE,1)
    cube_face([(0,0,-pd),(pw,0,-pd),(pw,pl,-pd),(0,pl,-pd)],POOL_FLOOR,POOL_EDGE)
    water_pts=[iso(0,0,0),iso(pw,0,0),iso(pw,pl,0),iso(0,pl,0)]
    draw.polygon(water_pts,fill=POOL_WATER)
    for i in range(1,5):
        ys=pl*i/5; draw.line([iso(0,ys,0),iso(pw,ys,0)],fill=(60,160,210,40),width=1)
    draw.polygon(water_pts,outline=POOL_EDGE,fill=None)

    if inp.pool_type in ('overflow','infinity'):
        chan=0.35
        cube_face([(-chan,-chan,0.12),(pw+chan,-chan,0.12),(pw+chan,pl+chan,0.12),(-chan,pl+chan,0.12)],None,(26,143,160,200),2)

    callouts=[]
    n_drains=len(result.main_drains)
    for i in range(n_drains):
        dx=pw*0.4+i*pw*0.2; dy=pl*0.75; dz=-pd
        dp=iso(dx,dy,dz)
        draw.ellipse([dp[0]-6,dp[1]-3,dp[0]+6,dp[1]+3],fill=DRAIN_C,outline=CYAN,width=1)
        draw.line([dp[0]-5,dp[1],dp[0]+5,dp[1]],fill=CYAN,width=1)
        draw.line([dp[0],dp[1]-3,dp[0],dp[1]+3],fill=CYAN,width=1)
        if i==0: callouts.append((dp,f'DRAIN x{n_drains}',DRAIN_C))

    n_inlets=len(result.return_inlets); n_per=max(1,n_inlets//2)
    inlet_pts=[]
    for i in range(n_per):
        yp=pl*0.2+(pl*0.6)*i/max(n_per-1,1)
        inlet_pts.append((0,yp,-0.4)); inlet_pts.append((pw,yp,-0.4))
    for pos in inlet_pts[:n_inlets]:
        ip=iso(*pos); draw.rectangle([ip[0]-4,ip[1]-3,ip[0]+4,ip[1]+3],fill=INLET_C,outline=CYAN,width=1)
    if inlet_pts: callouts.append((iso(*inlet_pts[0]),f'INLET x{n_inlets}',INLET_C))

    n_lights=len(result.lighting); n_ps=max(1,n_lights//2)
    lpts=[]
    for i in range(n_ps):
        ly=pl*0.2+(pl*0.5)*i/max(n_ps-1,1)
        lpts.append(iso(pw*0.05,ly,-0.3)); lpts.append(iso(pw*0.95,ly,-0.3))
    for lp in lpts:
        draw.ellipse([lp[0]-10,lp[1]-6,lp[0]+10,lp[1]+6],fill=(240,232,96,30))
        draw.ellipse([lp[0]-5,lp[1]-3,lp[0]+5,lp[1]+3],fill=LIGHT_C)
    if lpts: callouts.append((lpts[0],f'LIGHT x{n_lights}',LIGHT_C))

    if inp.pool_type=='skimmer':
        sx=pw*0.5; spts=[iso(sx-0.2,0,0.12),iso(sx+0.2,0,0.12),iso(sx+0.2,-0.25,0.12),iso(sx-0.2,-0.25,0.12)]
        _poly(draw,spts,fill=SKIMMER_C,outline=CYAN,width=1)
        callouts.append((iso(sx,-0.1,0.12),'SKIMMER',SKIMMER_C))

    if result.robot_cleaner:
        rb=iso(pw*0.75,pl*0.65,-pd+0.08)
        draw.rectangle([rb[0]-10,rb[1]-5,rb[0]+10,rb[1]+5],fill=ROBOT_C,outline=MUTED,width=1)
        callouts.append((rb,'ROBOT',ROBOT_C))

    er_x0=pw+gap; er_y0=(pl-er_depth)/2; er_h=2.8
    cube_face([(er_x0,er_y0,0),(er_x0+er_width,er_y0,0),(er_x0+er_width,er_y0,er_h),(er_x0,er_y0,er_h)],ER_FILL,ER_EDGE,1)
    cube_face([(er_x0,er_y0,0),(er_x0,er_y0+er_depth,0),(er_x0,er_y0+er_depth,er_h),(er_x0,er_y0,er_h)],(12,20,40),ER_EDGE,1)
    cube_face([(er_x0,er_y0+er_depth,0),(er_x0+er_width,er_y0+er_depth,0),(er_x0+er_width,er_y0+er_depth,er_h),(er_x0,er_y0+er_depth,er_h)],ER_FILL,ER_EDGE,1)
    cube_face([(er_x0+er_width,er_y0,0),(er_x0+er_width,er_y0+er_depth,0),(er_x0+er_width,er_y0+er_depth,er_h),(er_x0+er_width,er_y0,er_h)],(16,26,50),ER_EDGE,1)
    cube_face([(er_x0,er_y0,er_h),(er_x0+er_width,er_y0,er_h),(er_x0+er_width,er_y0+er_depth,er_h),(er_x0,er_y0+er_depth,er_h)],(18,28,52,180),ER_EDGE,1)

    pad_x=er_width*0.08; pad_y=er_depth*0.08
    col_w=(er_width-3*pad_x)/2; row_h=(er_depth-3*pad_y)/2.5; bh=2.2

    def er_block(col,row,label,color=EQUIP_EDGE):
        bx0=er_x0+pad_x+col*(col_w+pad_x); by0=er_y0+pad_y+row*(row_h+pad_y)
        bx1=bx0+col_w; by1=by0+row_h
        cube_face([(bx0,by1,0),(bx1,by1,0),(bx1,by1,bh),(bx0,by1,bh)],EQUIP_FILL,color)
        cube_face([(bx1,by0,0),(bx1,by1,0),(bx1,by1,bh),(bx1,by0,bh)],(12,22,45),color)
        cube_face([(bx0,by0,bh),(bx1,by0,bh),(bx1,by1,bh),(bx0,by1,bh)],(22,38,68),color,1)
        cube_face([(bx0,by0,bh),(bx1,by0,bh),(bx1,by0,bh+0.1),(bx0,by0,bh+0.1)],color)
        lp=iso((bx0+bx1)/2,by1,bh*0.5); _label(draw,lp,label,color=WHITE,size=11)

    if result.filter: er_block(0,0,result.filter.model.split()[0][:10],EQUIP_EDGE)
    if result.pump: er_block(1,0,'Pump',CYAN)
    if result.treatment: er_block(0,1,'Treatment',GOLD)
    if result.heater: er_block(1,1,'Heater',GOLD)
    if result.automation: er_block(0,2,'Automation',ER_EDGE)
    if result.dehumidifier: er_block(1,2,'Dehumid.',EQUIP_EDGE)

    drain_pt=iso(pw*0.4,pl*0.75,-pd); er_in=iso(er_x0,er_y0+er_depth*0.7,0.5)
    pool_exit=iso(pw,pl*0.75,0); mid_pt=iso(pw*0.4,pl*0.75,-pd+0.2)
    draw.line([drain_pt,mid_pt,pool_exit,er_in],fill=(77,217,236,160),width=2)
    er_out=iso(er_x0,er_y0+er_depth*0.3,0.6); pool_ret=iso(0,pl*0.3,-0.4)
    draw.line([er_out,pool_ret],fill=(201,168,76,160),width=2)

    er_lp=iso(er_x0+er_width/2,er_y0,er_h+0.4); _label_bold(draw,er_lp,'ENGINE ROOM',CYAN,14)

    for pt,label,color in callouts:
        draw.line([pt,(pt[0]+25,pt[1]-18)],fill=color,width=1)
        _label(draw,(pt[0]+27,pt[1]-20),label,color=color,size=11,anchor='lm')

    p_w0=iso(0,pl+0.8,0); p_w1=iso(pw,pl+0.8,0)
    draw.line([p_w0,p_w1],fill=MUTED,width=1)
    mid=((p_w0[0]+p_w1[0])//2,(p_w0[1]+p_w1[1])//2)
    _label(draw,(mid[0],mid[1]+14),f'{inp.width_m:.0f} m',MUTED,11)
    p_l0=iso(pw+0.6,0,0); p_l1=iso(pw+0.6,pl,0)
    draw.line([p_l0,p_l1],fill=MUTED,width=1)
    mid2=((p_l0[0]+p_l1[0])//2,(p_l0[1]+p_l1[1])//2)
    _label(draw,(mid2[0]+20,mid2[1]),f'{inp.length_m:.0f} m',MUTED,11)
    p_d0=iso(-0.6,pl*0.5,0); p_d1=iso(-0.6,pl*0.5,-pd)
    draw.line([p_d0,p_d1],fill=MUTED,width=1)
    mid3=((p_d0[0]+p_d1[0])//2,(p_d0[1]+p_d1[1])//2)
    _label(draw,(mid3[0]-28,mid3[1]),f'{inp.depth_m:.1f} m',MUTED,11)

    try:
        fnt_big=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',18)
        fnt_med=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    except: fnt_big=fnt_med=ImageFont.load_default()
    pl_lbl={'skimmer':'Skimmer','overflow':'Overflow','infinity':'Infinity Edge'}
    fl_lbl={'saltwater':'Salt','magnesium':'Magnesium','chlorine':'Chlorine'}
    draw.text((30,30),'3D Pool Visualisation',font=fnt_big,fill=CYAN)
    draw.text((30,56),(f"{pl_lbl.get(inp.pool_type,'Pool')}  {inp.width_m}x{inp.length_m}x{inp.depth_m}m  "
                       f"{fl_lbl.get(inp.filtration,inp.filtration)}  {result.volume_m3:.0f}m3"),font=fnt_med,fill=MUTED)

    legend=[(DRAIN_C,'Main Drain'),(INLET_C,'Return Inlet'),(LIGHT_C,'LED Light'),
            (EQUIP_EDGE,'Hydraulics'),(CYAN,'Pump'),(GOLD,'Treatment/Heat'),
            ((77,217,236),'Suction Flow'),((201,168,76),'Return Flow')]
    lx=W-190
    draw.rectangle([lx-8,H-190,W-10,H-10],fill=(16,24,42),outline=ER_EDGE,width=1)
    draw.text((lx,H-185),'LEGEND',font=fnt_med,fill=MUTED)
    for i,(color,label) in enumerate(legend):
        y=H-163+i*20; c=color[:3] if isinstance(color,tuple) and len(color)==4 else color
        draw.ellipse([lx,y,lx+10,y+10],fill=c)
        draw.text((lx+16,y),label,font=fnt_med,fill=(180,200,220))

    buf=io.BytesIO(); img.save(buf,'PNG',optimize=True); return buf.getvalue()
