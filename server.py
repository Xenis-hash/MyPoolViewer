"""MyPoolViewer — Flask API (Phase 3+5)"""
import os, sys
from flask import Flask, request, jsonify, send_from_directory, Response
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calculator import PoolInputs, calculate

CSV    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "master_pool_components.csv")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app    = Flask(__name__, static_folder=STATIC)

def _inp(body):
    return PoolInputs(
        width_m      = float(body.get("width_m",  8)),
        length_m     = float(body.get("length_m", 16)),
        depth_m      = float(body.get("depth_m",  1.5)),
        pool_type    = str(body.get("pool_type",   "skimmer")),
        filtration   = str(body.get("filtration",  "saltwater")),
        heating      = bool(body.get("heating",    True)),
        indoor       = bool(body.get("indoor",     False)),
        liner_style  = str(body.get("liner_style", "touch")),
        liner_color  = str(body.get("liner_color", "elegance")),
        light_color  = str(body.get("light_color", "rgbw")),
        drain_color  = str(body.get("drain_color", "white")),
        grille_color = str(body.get("grille_color","white")),
        inlet_color  = str(body.get("inlet_color", "white")),
        ladder_type  = str(body.get("ladder_type", "standard")),
    )

def _comp(c):
    if c is None: return None
    if isinstance(c, list): c = c[0] if c else None
    if c is None: return None
    return {"model": c.model, "code": c.code,
            "subcategory": getattr(c,'subcategory',''), "category": getattr(c,'category','')}

def _comps(lst):
    return [_comp(c) for c in (lst or [])]

@app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    try:
        body = request.get_json(force=True)
        inp  = _inp(body)
        r    = calculate(inp, CSV)
        return jsonify({
            "geometry":     {"volume_m3": r.volume_m3, "surface_m2": r.surface_m2},
            "hydraulics":   {"design_flow_m3h": r.design_flow_m3h,
                             "turnover_hours": r.turnover_hours,
                             "n_chlorinators": r.n_chlorinators},
            "engine_room_m2": r.engine_room_m2,
            "equipment": {
                "filter": _comp(r.filter), "pump": _comp(r.pump),
                "treatment": _comp(r.treatment), "valve_manifold": _comp(r.valve_manifold),
                "strainer": _comp(r.strainer), "check_valve": _comp(r.check_valve),
                "vibration_damper": _comp(r.vibration_damper), "air_blower": _comp(r.air_blower),
                "heater": _comp(r.heater), "dehumidifier": _comp(r.dehumidifier),
                "automation": _comp(r.automation), "robot_cleaner": _comp(r.robot_cleaner),
                "liner": _comp(r.liner),
            },
            "quantities": {
                "main_drains": _comps(r.main_drains),
                "return_inlets": _comps(r.return_inlets),
                "overflow_grilles": _comps(r.overflow_grilles),
                "lighting": _comps(r.lighting),
                "light_transformer": _comp(r.light_transformer),
                "pool_surround": _comps(r.pool_surround),
            },
            "bom":      r.bom,
            "warnings": r.warnings,
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 400

@app.route("/api/options", methods=["GET"])
def api_options():
    return jsonify({"status": "ok", "csv_rows": sum(1 for _ in open(CSV)) - 1})

@app.route("/api/report", methods=["POST"])
def api_report():
    try:
        body = request.get_json(force=True)
        inp  = _inp(body)
        r    = calculate(inp, CSV)
        from report import generate_pdf
        pdf  = generate_pdf(inp, r)
        return Response(pdf, mimetype="application/pdf",
                        headers={"Content-Disposition":
                                 "attachment; filename=MyPoolViewer_Report.pdf"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 400

if __name__ == "__main__":
    print("MyPoolViewer API → http://localhost:5000")
    app.run(debug=True, port=5000)
