import base64
import time

from django.test import TestCase

from .models import Consent, Decision, Plug, ShiftBlock


def basic(pw):
    return {"HTTP_AUTHORIZATION": "Basic " + base64.b64encode(f"x:{pw}".encode()).decode()}


class Lender(TestCase):
    def setUp(self):
        p = Plug.objects.create(plug_id="WC-1", entrepreneur_id="E-01", public_jwk={})
        now = int(time.time())
        for s in range(1, 11):
            ShiftBlock.objects.create(plug=p, seq=s, t_start=now - s * 86400, t_end=now, work_min=480, idle_min=0, other_min=0,
                                      credited_mwh=2_000_000, vrms_dv=0, irms_ca=0, trips=0, prev_hash="", hash="", sig="", submitted_by="o")

    def test_requires_auth(self):
        self.assertEqual(self.client.get("/lender/").status_code, 401)
        self.assertEqual(self.client.get("/lender/", **basic("wrong")).status_code, 401)

    def test_flow(self):
        ok = basic("lender-demo")
        self.assertIn(b"E-01", self.client.get("/lender/", **ok).content)
        self.assertIn(b"no digital consent", self.client.get("/lender/E-01/", **ok).content)
        Consent.objects.create(entrepreneur_id="E-01", at_ms=1, lang="ta", signer="Meena", submitted_by="o")
        pdf = self.client.get("/lender/E-01/kfs.pdf", **ok)
        self.assertTrue(pdf.content.startswith(b"%PDF") and b"Meena" in pdf.content)
        self.assertIn(b"E-01,WC-1", self.client.get("/lender/export.csv", **ok).content)
        self.client.post("/lender/E-01/decide/", {"status": "flagged"}, **ok)
        self.assertEqual(Decision.objects.get(pk="E-01").status, "flagged")
        self.assertEqual(self.client.post("/lender/E-01/decide/", {"status": "x"}, **ok).status_code, 400)
