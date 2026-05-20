# Deployment Notes

## Target architecture

Browser microphone and speaker stay in Chrome or Edge.
Asterisk handles SIP signaling, RTP, WebRTC negotiation, DTLS/SRTP, ICE, and SIP trunk bridging.
FastAPI handles app logic, authentication, session metadata, and optional AMI-driven origination.

## Recommended rollout

1. Confirm Asterisk listens on `8088` and `8089` for HTTP/WSS.
2. Install valid TLS certificates on the PBX.
3. Apply `rtp.conf`, `http.conf`, `pjsip.conf`, and `extensions.conf` with your real values.
4. Open firewall ports:
   - `8088/tcp` for HTTP if used internally
   - `8089/tcp` for secure WebSocket
   - `5060/udp` or provider-specific SIP transport
   - `10000-20000/udp` for RTP
5. If Asterisk is behind NAT, set `external_signaling_address`, `external_media_address`, and local network rules correctly.
6. Point FastAPI `.env` values to the browser SIP extension and WSS endpoint.
7. Register the browser SIP endpoint, then test browser-to-provider outbound calling.

## Production hardening

- Prefer `wss://` only for browser SIP transport.
- Use a real TURN server if users are behind restrictive NAT or corporate firewalls.
- Keep browser SIP credentials separate per user or session, not shared globally.
- Move call records from memory into Postgres or Redis-backed persistence.
- Add AMI event ingestion or ARI webhooks if you need authoritative live call state.
- Put FastAPI behind a reverse proxy with TLS and auth before exposing it.

## Validation checklist

- Browser gets microphone permission.
- SIP.js connects over WSS.
- Browser registers as extension `7001`.
- Outbound call rings the real phone through the provider trunk.
- Audio is two-way without desktop audio drivers.
- Hangup state is reflected in both browser and backend logs.
