import sys, time, requests
from geopy.distance import geodesic
from lxml import etree as ET
import gpxpy

API_URL = "https://api.opentopodata.org/v1/srtm90m"
BATCH = 90

KML_NS = "http://www.opengis.net/kml/2.2"
NSMAP = {None: KML_NS}

COLORS = {
    # Descents (red range)
    "steep_down_30": "ff800000",
    "steep_down_25": "ff990000",
    "steep_down_20": "ffB20000",
    "steep_down_15": "ffCC0000",
    "steep_down_10": "ffE60000",
    "steep_down_5":  "ffff0000",

    # Small descents
    "down_4":   "ffcc8000",
    "down_3":   "ffdd9900",
    "down_2":   "ffeeaa00",
    "down_1":   "ffffbb00",

    # Flat
    "flat":     "ffffffff",

    # Climbs (blue range)
    "up_1":     "ff0088ff",
    "up_2":     "ff0099ff",
    "up_3":     "ff00aaff",
    "up_4":     "ff00bbff",
    "up_5":     "ff00ccff",
    "up_10":    "ff0088ff",
    "up_15":    "ff0044ff",
    "up_20":    "ff0022ff",
    "up_25":    "ff0000ff",
    "up_30":    "ff220088",
}

def classify(g):
    if g <= -25:   return "steep_down_30"
    if g <= -20:   return "steep_down_25"
    if g <= -15:   return "steep_down_20"
    if g <= -10:   return "steep_down_15"
    if g <= -5:    return "steep_down_10"
    if g <= -2.5:  return "steep_down_5"

    if g <= -1.5:  return "down_4"
    if g <= -1:    return "down_3"
    if g <= -0.5:  return "down_2"
    if g <= -0.25: return "down_1"

    if abs(g) < 0.25: return "flat"

    if g <= 0.25:  return "up_1"
    if g <= 0.5:   return "up_2"
    if g <= 1:     return "up_3"
    if g <= 1.5:   return "up_4"
    if g <= 2.5:   return "up_5"
    if g <= 5:     return "up_10"
    if g <= 10:    return "up_15"
    if g <= 15:    return "up_20"
    if g <= 20:    return "up_25"
    if g <= 25:    return "up_30"
    return "up_30"

def read_points(fn):
    pts = []

    if fn.endswith(".gpx"):
        with open(fn, "r") as f:
            g = gpxpy.parse(f)
        for t in g.tracks:
            for s in t.segments:
                for p in s.points:
                    pts.append((p.latitude, p.longitude))
        print("[i] GPX:", len(pts))
        return pts

    root = ET.parse(fn).getroot()
    for c in root.iter("{http://www.google.com/kml/ext/2.2}coord"):
        lon, lat, _ = map(float, c.text.split())
        pts.append((lat, lon))
    if not pts:
        for coords in root.iter(f"{{{KML_NS}}}coordinates"):
            for l in coords.text.strip().splitlines():
                lon, lat, _ = map(float, l.split(","))
                pts.append((lat, lon))
    print("[i] KML:", len(pts))
    return pts

def load_elevations(pts):
    out=[]
    print("[i] Loading elevations...")
    for i in range(0,len(pts),BATCH):
        chunk = pts[i:i+BATCH]
        q="|".join(f"{lat},{lon}" for lat,lon in chunk)
        r=requests.get(API_URL,params={"locations":q})
        if r.status_code!=200:
            time.sleep(1); r=requests.get(API_URL,params={"locations":q})
        js=r.json()
        out += [x["elevation"] for x in js["results"]]
        print(f"  {len(out)}/{len(pts)}")
        time.sleep(0.1)
    return [(lat,lon,ele) for (lat,lon),ele in zip(pts,out)]

def slope(a,b):
    d=geodesic((a[0],a[1]), (b[0],b[1])).meters
    if d<0.5: return 0
    return (b[2]-a[2])/d*100

def write_kml(points,out):
    root=ET.Element("kml",nsmap=NSMAP)
    doc=ET.SubElement(root,"Document")

    for n,c in COLORS.items():
        s=ET.SubElement(doc,"Style",id=n)
        ls=ET.SubElement(s,"LineStyle")
        ET.SubElement(ls,"color").text=c
        ET.SubElement(ls,"width").text="4"

    for i in range(len(points)-1):
        p1=points[i]
        p2=points[i+1]
        g=slope(p1,p2)
        col=classify(g)

        pm=ET.SubElement(doc,"Placemark")
        ET.SubElement(pm,"styleUrl").text=f"#{col}"
        ls=ET.SubElement(pm,"LineString")
        ET.SubElement(ls,"tessellate").text="1"
        ET.SubElement(ls,"coordinates").text=f"{p1[1]},{p1[0]},{p1[2]} {p2[1]},{p2[0]},{p2[2]}"

    ET.ElementTree(root).write(out, pretty_print=True, encoding="utf-8", xml_declaration=True)
    print(f"[✓] Saved: {out}")


if __name__=="__main__":
    fn=sys.argv[1]
    coords=read_points(fn)
    pts=load_elevations(coords)
    out=fn.replace(".kml","_elev.kml").replace(".gpx","_elev.kml")
    write_kml(pts,out)
