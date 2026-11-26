# WattCredit Field Desk: Django + TypeScript

One role-based, offline-first web app (officer mode and entrepreneur mode). Installable as a PWA later; the same record formats feed the Flutter build.

## Run (Windows, macOS, Linux; Python 3.10+; no Node needed, the compiled JS is committed)
    cd backend
    python -m venv venv
    venv\Scripts\activate            # Windows      |  source venv/bin/activate   # macOS / Linux
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver            # http://localhost:8000  (DEBUG on: demo key registration enabled)

Open it in Chrome (Android or desktop). Microphone and Bluetooth only work on `localhost` or HTTPS, so to use it on a
phone either deploy behind HTTPS and set `DJANGO_ALLOWED_HOSTS=your.domain`, or tunnel localhost over HTTPS
(for example `cloudflared tunnel --url http://localhost:8000`). Any number of phones/browsers can use one server:
each install gets its own simulated plugs (`WC-7A21-ab12`) and its own signing key.
Chrome's built-in Tamil recognition (`ta-IN`) gives a first transcript with no API key; set `WC_TRANSCRIBER` for a server model.
Production (not done here): `DJANGO_DEBUG=0` turns off the demo key-registration endpoint, so real enrolment is needed first; also set `DJANGO_SECRET_KEY` and `WC_LENDER_TOKEN`, and serve `/static/` with WhiteNoise or a web server (Django's runserver only serves it in DEBUG).
    # sign in with PIN 1234 (first run sets it). Officer mode: Scan, Sync now. Entrepreneur mode: voice and keypad sales.
    # the compiled JS is already in backend/static/app/js; to rebuild: cd frontend && npm i && npm run build

## Tamil voice sales
Entrepreneur taps **இன்றைய விற்பனையைப் பதிவு செய்க**: records <=30 s of Opus audio (mono, 24 kbit/s) and saves it, AES-GCM encrypted, in the local DB and outbox. The ₹500 / ₹1,000 / ₹2,000 keys add up and save as a confirmed keypad sale with no audio. On sync the server stores the clip and transcribes it:

    WC_TRANSCRIBER=sarvam SARVAM_API_KEY=... [SARVAM_MODEL=saaras:v3]   # api.sarvam.ai/speech-to-text, language ta-IN
    WC_TRANSCRIBER=indic  INDIC_URL=http://your-host/transcribe          # your IndicConformer wrapper: multipart {audio, language=ta} -> {"text": ...}
    WC_TRANSCRIBER=vosk   VOSK_MODEL_PATH=/models/vosk-model-ta          # offline demo; needs `pip install vosk` and ffmpeg
    WC_TRANSCRIBE_INLINE=1            # transcribe during the sync request; otherwise run: python manage.py transcribe_pending (cron)

`ledger/amounts.py` pulls the rupee amount (Tamil/Western digits, Tamil number words, "ஆயிரத்து ஐநூறு ரூபாய்" = 1500). One clear amount next to a rupee word becomes `transcribed`; anything else becomes `needs_review` and an officer sets the amount in the Cloud ledger tab. `WC_LLM_AMOUNT_EXTRACTOR=module.func` plugs in an LLM second opinion (not implemented here).

Spend guard: `WC_SARVAM_DAILY_MINUTES` (default 5) caps Sarvam audio per rolling 24 h; beyond it, clips wait unsent to the API.

## Consent, scoring, lender dashboard
- Officer taps Sync on a plug whose borrower has no consent yet: Tamil + English consent screen (typed-name signature, timestamp), saved locally and synced as a `consent` record. No telemetry is pulled without it. OTP is not implemented (`otpOk` is always false).
- `ledger/scoring.py`: 30/90-day productive kWh, consistency, seasonality, logged sales vs energy-estimated revenue (`WC_REVENUE_PER_KWH`, default 150, calibrate per trade), 50% FOIR EMI capacity, limit Rs 5,000-50,000 (0 if tamper alert, no consent, or no confirmed sales).
- Lender portal at http://localhost:8000/lender/ (HTTP Basic, password = `WC_LENDER_TOKEN`, dev default `lender-demo`): plug table, borrower view with 90-day runtime chart, Approve / Flag for field audit, CSV export, KFS PDF.

## Tests that were actually run
    cd backend && python manage.py test ledger     # includes scoring and lender flow
    cd frontend && npm test                                   # tsc + Node e2e on the real compiled modules
    cd ../backend && python -m unittest ledger.test_evidence ledger.test_amounts

## Not verified
- Django was not installed where this was written: `models.py`, `views.py`, settings and URLs are syntax-checked only. Expect to fix small things on first `runserver`.
- Web Bluetooth transport follows the GATT layout in `transport.ts` but was never run against a plug or a browser. The plug firmware must implement that layout.
- Sarvam, IndicConformer and Vosk calls were not run (no network, no keys). Sarvam's current default model is saaras:v4; v3 is marked legacy in their docs.
- Tamil UI strings are a first draft; get a native speaker to review. Number parsing misses compound tens (21-99).
- Browser storage is not SQLCipher; the Android build swaps it in. A background sync with the app fully closed needs the native WorkManager build.
- Dev-only: `/api/dev/register/` trusts the browser to register its own keys. Production needs real enrolment.
