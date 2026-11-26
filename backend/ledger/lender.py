"""Lender / NGO web dashboard, CSV export and KFS PDF. Server-rendered, no JS.
Auth: HTTP Basic, any user name, password = WC_LENDER_TOKEN (dev default 'lender-demo' only when DEBUG)."""
import base64
import csv
import hmac
import time
from html import escape as e

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect

from .models import Consent, DailySale, Decision, Plug, ShiftBlock, TamperAlert
from .scoring import DAY, score


def guarded(view):
    def wrap(request, *a, **k):
        tok = settings.LENDER_TOKEN
        try:
            pw = base64.b64decode(request.headers.get("Authorization", "")[6:]).decode().partition(":")[2]
        except ValueError:
            pw = ""
        if not tok or not hmac.compare_digest(pw.encode(), tok.encode()):
            r = HttpResponse("Lender sign-in required", status=401)
            r["WWW-Authenticate"] = 'Basic realm="WattCredit lender"'
            return r
        if request.method == "POST" and request.headers.get("Sec-Fetch-Site", "same-origin") == "cross-site":
            return HttpResponseForbidden("cross-site POST refused")
        return view(request, *a, **k)
    return wrap


def borrower(ent_id, now=None):
    now = now or time.time()
    plugs = list(Plug.objects.filter(entrepreneur_id=ent_id))
    blocks = list(ShiftBlock.objects.filter(plug__in=plugs).values_list("t_start", "work_min", "credited_mwh"))
    sales = list(DailySale.objects.filter(entrepreneur_id=ent_id, status__in=("confirmed", "transcribed")).values_list("at_ms", "amount_paise"))
    alerts = TamperAlert.objects.filter(plug_id__in=[p.plug_id for p in plugs]).count()
    consent = Consent.objects.filter(entrepreneur_id=ent_id).order_by("-at_ms").first()
    sc = score(blocks, [(a, p or 0) for a, p in sales], alerts, now, settings.REV_PER_KWH)
    if not consent:
        sc["flags"].append("no digital consent on file")
        sc["limit"] = 0
    last = ShiftBlock.objects.filter(plug__in=plugs).order_by("-received_at").values_list("received_at", flat=True).first()
    return {"id": ent_id, "plugs": plugs, "blocks": blocks, "score": sc, "alerts": alerts, "consent": consent,
            "lastSync": last, "decision": Decision.objects.filter(pk=ent_id).first()}


def _ents():
    return sorted({p.entrepreneur_id for p in Plug.objects.exclude(entrepreneur_id="")})


PAGE = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>WattCredit lender</title><style>body{font:15px system-ui;margin:24px;max-width:980px}table{border-collapse:collapse;width:100%}"
        "td,th{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left}.bad{color:#b00020}.ok{color:#0a7d33}button{padding:8px 14px;margin-right:6px}</style>")


@guarded
def dashboard(request):
    rows = ""
    for i in _ents():
        b = borrower(i); s = b["score"]
        sync = f"{b['lastSync']:%d %b %H:%M}" if b["lastSync"] else "never"
        rows += (f"<tr><td><a href='/lender/{e(i)}/'>{e(i)}</a></td><td>{', '.join(e(p.plug_id) for p in b['plugs'])}</td><td>{sync}</td>"
                 f"<td class={'bad' if b['alerts'] else 'ok'}>{b['alerts'] or 'none'}</td><td>{s['kwh30']}</td><td>₹{s['limit']:,}</td>"
                 f"<td>{e(b['decision'].status) if b['decision'] else '-'}</td></tr>")
    return HttpResponse(PAGE + f"<h1>Plugs and borrowers</h1><p><a href='/lender/export.csv'>Export CSV</a></p>"
                        f"<table><tr><th>Borrower</th><th>Plug</th><th>Last sync</th><th>Tamper</th><th>Productive kWh (30 d)</th><th>Suggested limit</th><th>Decision</th></tr>{rows}</table>")


def _chart(blocks, now, days=90):
    per = [0.0] * days
    for t, _, mwh in blocks:
        d = int((now - t) // DAY)
        if 0 <= d < days:
            per[days - 1 - d] += mwh / 1e6
    top = max(per) or 1
    bars = "".join(f"<rect x='{i * 8}' y='{100 - 100 * v / top:.0f}' width='6' height='{100 * v / top:.0f}' fill='#2a6'/>" for i, v in enumerate(per))
    return f"<svg viewBox='0 0 {days * 8} 100' width='100%' height='120' role=img aria-label='kWh per day, last {days} days'>{bars}</svg>"


@guarded
def borrower_page(request, ent_id):
    b = borrower(ent_id); s = b["score"]
    if not b["plugs"]:
        return HttpResponse("unknown borrower", status=404)
    flags = "".join(f"<li class=bad>{e(f)}</li>" for f in s["flags"]) or "<li class=ok>No flags</li>"
    d = b["decision"]
    return HttpResponse(PAGE + f"""<p><a href='/lender/'>&larr; all borrowers</a></p><h1>{e(ent_id)}</h1>
<p>Decision: <b>{e(d.status) if d else 'pending'}</b> &middot; <a href='/lender/{e(ent_id)}/kfs.pdf'>Key Facts Statement (PDF)</a></p>
<h2>Machine runtime: kWh per day, 90 days</h2>{_chart(b['blocks'], time.time())}
<table><tr><th>Productive kWh 30 d</th><td>{s['kwh30']}</td><th>Work hours 30 d</th><td>{s['workHours30']}</td></tr>
<tr><th>Voice/keypad sales 30 d</th><td>₹{s['loggedSales30']:,}</td><th>Energy-estimated revenue</th><td>₹{s['energyRevenue30']:,}</td></tr>
<tr><th>Consistency</th><td>{s['consistency']}</td><th>Seasonality (30 d vs 90 d avg)</th><td>{s['seasonality']}</td></tr>
<tr><th>Monthly income used</th><td>₹{s['monthlyIncome']:,}</td><th>EMI capacity (50% FOIR)</th><td>₹{s['emiCapacity']:,}</td></tr>
<tr><th>Recommended limit</th><td colspan=3><b>₹{s['limit']:,}</b> over {s['tenureMonths']} months</td></tr></table>
<h3>Flags</h3><ul>{flags}</ul>
<form method=post action='/lender/{e(ent_id)}/decide/'><button name=status value=approved>Approve</button>
<button name=status value=flagged>Flag for field audit</button></form>""")


@guarded
def decide(request, ent_id):
    st = request.POST.get("status")
    if request.method != "POST" or st not in ("approved", "flagged"):
        return HttpResponse("bad request", status=400)
    Decision.objects.update_or_create(entrepreneur_id=ent_id, defaults={"status": st, "limit": borrower(ent_id)["score"]["limit"] if st == "approved" else 0})
    return HttpResponseRedirect(f"/lender/{ent_id}/")


@guarded
def export_csv(request):
    r = HttpResponse(content_type="text/csv"); r["Content-Disposition"] = "attachment; filename=wattcredit_borrowers.csv"
    w = csv.writer(r)
    w.writerow(["borrower", "plugs", "tamper_alerts", "kwh_30d", "work_hours_30d", "logged_sales_30d", "energy_revenue_30d",
                "consistency", "emi_capacity", "recommended_limit", "consent", "decision", "flags"])
    for i in _ents():
        b = borrower(i); s = b["score"]
        w.writerow([i, " ".join(p.plug_id for p in b["plugs"]), b["alerts"], s["kwh30"], s["workHours30"], s["loggedSales30"],
                    s["energyRevenue30"], s["consistency"], s["emiCapacity"], s["limit"], "yes" if b["consent"] else "no",
                    b["decision"].status if b["decision"] else "", "; ".join(s["flags"])])
    return r


def make_pdf(lines):
    """Minimal one-page PDF (Helvetica, Latin-1 text). ponytail: single page, no wrapping; use reportlab if KFS grows."""
    esc = lambda t: t.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 11 Tf 14 TL 50 790 Td " + " T* ".join(f"({esc(l)}) Tj" for l in lines) + " ET"
    objs = ["<</Type/Catalog/Pages 2 0 R>>", "<</Type/Pages/Kids[3 0 R]/Count 1>>",
            "<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            f"<</Length {len(stream.encode('latin-1'))}>>\nstream\n{stream}\nendstream", "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offs = b"%PDF-1.4\n", []
    for n, o in enumerate(objs, 1):
        offs.append(len(out)); out += f"{n} 0 obj\n{o}\nendobj\n".encode("latin-1")
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    return out + f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{x}\n%%EOF".encode()


@guarded
def kfs_pdf(request, ent_id):
    b = borrower(ent_id); s = b["score"]
    if not b["plugs"]:
        return HttpResponse("unknown borrower", status=404)
    c = b["consent"]
    lines = ["WattCredit - Key Facts Statement (KFS)", f"Generated: {time.strftime('%d %b %Y %H:%M UTC', time.gmtime())}", "",
             f"Borrower: {ent_id}    Plug(s): {', '.join(p.plug_id for p in b['plugs'])}",
             f"Digital consent: {'signed by ' + c.signer + ' at ' + time.strftime('%d %b %Y %H:%M UTC', time.gmtime(c.at_ms / 1000)) if c else 'NOT ON FILE'}",
             "", "Repayment capacity (FOIR 50%)",
             f"  Productive energy, last 30 days: {s['kwh30']} kWh over {s['workHours30']} work hours ({s['activeDays30']} active days)",
             f"  Logged sales, last 30 days: Rs {s['loggedSales30']:,}    Energy-estimated revenue: Rs {s['energyRevenue30']:,}",
             f"  Monthly income used: Rs {s['monthlyIncome']:,}    Max EMI at 50% FOIR: Rs {s['emiCapacity']:,}",
             f"  Recommended limit: Rs {s['limit']:,} over {s['tenureMonths']} months (indicative; interest rate and fees set by the lender)",
             "", f"Flags: {'; '.join(s['flags']) or 'none'}",
             "", "Telemetry audit trail (SHA-256 hash chain, ECDSA signed by plug)"]
    for p in b["plugs"]:
        lines.append(f"  {p.plug_id}: {p.last_seq} verified blocks, chain head {p.last_hash[:24]}...")
    lines += [f"  Tamper alerts: {b['alerts']}", "", f"Lender decision: {b['decision'].status if b['decision'] else 'pending'}"]
    r = HttpResponse(make_pdf(lines), content_type="application/pdf"); r["Content-Disposition"] = f"inline; filename=KFS_{ent_id}.pdf"
    return r
