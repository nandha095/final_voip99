# Browser SIP Calling Starter

Starter project for a browser-based SIP/WebRTC calling system built around:

- FastAPI for APIs and app orchestration
- Asterisk for SIP, RTP, WebRTC, and trunk bridging
- SIP.js in the browser for microphone/speaker audio

## What this starter includes

- FastAPI app with health, config, and call-management APIs
- Static frontend with SIP.js register, call, answer, and hangup controls
- Asterisk configuration templates for WebRTC and outbound trunk routing
- Environment-driven configuration so we can adapt this to your PBX and trunk

## Quick start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and update values.
3. Start the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Open `http://localhost:8000`.
5. Apply the example Asterisk configs carefully on your PBX after replacing domains, secrets, and trunk values.

## Project layout

- `app/` FastAPI backend
- `static/` browser client
- `asterisk/` sample PBX configs
- `docs/` integration and deployment notes

## Important note

This repo is a production-oriented scaffold, not a drop-in PBX image. Your exact trunk registration details, certificates, public IP/NAT settings, and dialplan rules still need to be aligned with your Asterisk server.
