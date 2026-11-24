"""Exercise the seven browser entry points against the same local bytes as readers."""
import argparse
import csv
import functools
import http.server
import io
import json
from pathlib import Path
from threading import Thread
from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("index","engine","trisphere","trisphere-prototype","equilibrium","screening","coil-scan")

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def exercise(page, name):
    element=page.locator
    if name=="index":
        slider=element("#leak");slider.focus();slider.press("End")
        assert element("#nextInventory").inner_text()=="60.0%"
        element("#reset").click();assert element("#nextInventory").inner_text()=="90.0%"
        return "Keyboard sets outward crossing to 100%; inventory 60%, reset 90%"
    if name=="engine":
        element("#external").check();assert "externally supported" in element("#status").inner_text()
        energy=element("#ledger").inner_text()
        element("#concept").check();assert "zero power" in element("#quark").inner_text()
        assert energy==element("#ledger").inner_text()
        return "External bootstrap labeled; conjectural stage changes no ledger entry"
    if name=="trisphere":
        before=element("#comparison").inner_text();element("#boundary").select_option("exhaust")
        assert before and before!=element("#comparison").inner_text()
        return "Both model summaries update when the exhaust opens"
    if name=="trisphere-prototype":
        page.wait_for_function("document.querySelector('#run-status').textContent.includes('complete')")
        with page.expect_download() as download: element("#export").click()
        record=json.loads(download.value.path().read_text())
        assert record["schema"]=="trisphere-run/2" and record["observerView"]["affectsDynamics"] is False
        assert record["parameters"] and len(record)>6
        return "Downloaded a populated run/2 with observer-only view"
    if name=="equilibrium":
        anchors=element('a[download][href$="summary.json"]')
        with page.expect_download() as download: anchors.first.click()
        raw=download.value.path().read_bytes()
        assert raw==(ROOT/"benchmarks/openstep-001/results/summary.json").read_bytes()
        element("summary").first.click()
        assert element("details").first.get_attribute("open") is not None
        return "Downloaded exact equilibrium summary bytes; opened provenance details"
    page.wait_for_function("document.querySelector('#load-status').textContent.includes('loaded')")
    if name=="screening":
        element("#eta-t").select_option("0.30")
        with (ROOT/"benchmarks/openstep-002/results/electric-sweep.csv").open() as f:
            records=list(csv.DictReader(f))
        row=next(r for r in records if all(float(r[k])==float(element("#"+id).input_value()) for k,id in
            (("thermal_efficiency","eta-t"),("heating_wallplug_efficiency","eta-w"),("other_electric_MW","parasite"))))
        assert f'{float(row["net_electric_MW"]):.1f}' in element("#electric-output").inner_text()
        return "Changed conversion efficiency; displayed net MW matches original CSV"
    element("#grid").select_option("257");element("#shift").select_option("0.05")
    data=json.loads((ROOT/"benchmarks/openstep-003/results/summary.json").read_text())
    row=next(r for r in data["rows_by_grid"]["257"] if r["shift_m"]==.05)
    assert f'{row["representative_heat_MW_m2"]:.2f}' in element("#case-output").inner_text()
    assert "Unresolved solve" in element("#sweep-table").inner_text()
    return "Positive 5 cm readout matches source JSON; unresolved neighbors visible"

def main(out, executable):
    out.mkdir(parents=True,exist_ok=True)
    handler=functools.partial(SilentHandler,directory=str(ROOT))
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
    Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/"
    rows=[]
    try:
        with sync_playwright() as api:
            browser=api.chromium.launch(executable_path=executable,headless=True,args=["--no-sandbox"])
            version=browser.version
            for width,height in ((1280,800),(390,844)):
                for name in PAGES:
                    page=browser.new_page(viewport=dict(width=width,height=height))
                    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                    page.on("response",lambda r:errors.append(str(r.status)+" "+r.url.split(base)[-1]) if r.status>=400 else None)
                    row=dict(page=name,width=width,height=height)
                    try:
                        page.goto(base+name+".html",wait_until="networkidle")
                        assert page.locator("h1").count()==1
                        row["interaction"]=exercise(page,name)
                        assert page.evaluate("Array.from(document.images).every(i=>i.complete && i.naturalWidth>0 && i.alt.length>0)")
                        # Nonuniform pixels in each visible canvas, separately from the whole page.
                        for canvas in page.locator("canvas:visible").all():
                            img=Image.open(io.BytesIO(canvas.screenshot())).convert("L")
                            assert ImageStat.Stat(img).stddev[0]>2
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"), "viewport has horizontal overflow"
                        if name in ("coil-scan","trisphere-prototype") and width==1280:
                            page.screenshot(path=str(out/(name+".png")))
                        assert not errors,errors
                        row["verdict"]="PASS"
                    except Exception as e:
                        row.update(verdict="FAIL",error=repr(e),resource_errors=errors)
                    finally:
                        rows.append(row);page.close()
            for name,stage in (("coil-scan","003"),("screening","002")):
                page=browser.new_page()
                page.route(f"**/openstep-{stage}/results/summary.json",lambda route:route.fulfill(status=404,body="missing"))
                page.goto(base+name+".html",wait_until="networkidle")
                covered="could not be loaded" in page.locator("#load-status").inner_text()
                rows.append(dict(page=name,fixture="missing dataset",verdict="PASS" if covered else "FAIL"));page.close()
            browser.close()
    finally:
        server.shutdown();server.server_close()
    (out/"browser.json").write_text(json.dumps(dict(chromium=version,cases=rows),indent=2)+"\n")
    print([(r["page"],r.get("width"),r.get("error")) for r in rows if r["verdict"]=="FAIL"])
    return any(r["verdict"]=="FAIL" for r in rows)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("output",type=Path);parser.add_argument("--chromium",default="/usr/bin/chromium")
    args=parser.parse_args();raise SystemExit(main(args.output,args.chromium))
