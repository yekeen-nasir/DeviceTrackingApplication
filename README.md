# Tracker — Python CLI device tracker

**Tracker** is a Python-first, command-line device tracking system that helps people manage and monitor their own enrolled devices (laptops/desktops, advanced Termux Android). It is *consent-first* — devices must be enrolled by their owners. Tracker provides an admin CLI, a small device agent, and an optional self-hosted server.

---

## Why I built it
(Short version)
A relative lost a phone and the family couldn't afford advanced tracking or didn’t have the necessary vendor-level access. Tracker was created to give everyday people a pragmatic, privacy-conscious way to track and recover enrolled devices using a pure-Python, command-line approach.

---

## What Tracker CAN do
- Enroll a device (mutual token exchange + device keypair).
- Regular heartbeats from enrolled devices (IP, hostname, Wi-Fi where available).
- Mark device as **Lost** → agent increases telemetry, shows messages, plays chime, or locks (where OS allows).
- Produce an evidence pack (timeline of IPs, ISPs, Wi-Fi BSSIDs, hostname) for authorities.
- Alerts on new IPs, unknown Wi-Fi, or missing heartbeats.
- Cross-platform agent persistence (systemd/Windows Service/LaunchAgent).

---

## What Tracker CANNOT do
- Track a device by phone number alone. Carrier-level tracking or Find-My-Phone features are NOT possible from a pure Python CLI without vendor cooperation or a native mobile app.
- Secretly monitor devices. All devices must be enrolled with owner consent.
- Guarantee exact GPS/street-level accuracy from IP-only telemetry.

---

## Quickstart (admin)
1. Install CLI: `pipx install trackerctl` (or `pip install trackerctl`)
2. Configure server: `trackerctl login --server https://yourserver.example`
3. Enroll device: `trackerctl device create-enrollment` → give token to device owner
4. On device: `tracker-agent enroll --server https://yourserver.example --token <token>`
5. Use `trackerctl device list`, `trackerctl device lost <id>`, `trackerctl report export <id>`

(Full CLI reference in `docs/CLI-REFERENCE.md`)

---

## Security & Privacy
- TLS-only communications.
- Per-device keypair + signed telemetry.
- Minimal PII storage — only what you explicitly add at enrollment.
- See `SECURITY.md` and `PRIVACY.md` for full details.

---

## Install & Distribution
- Recommended: `pipx install trackerctl` / `pipx install tracker-agent`
- Option for end-users: release PyInstaller-built binaries per platform in GitHub Releases.
- Server: run on a VPS behind TLS. See `DEPLOY.md`.

---

## Contributing
Contributions are welcome. See `CONTRIBUTING.md` for how to set up dev environment, run tests, and open issues.

---

## License
MIT License — see `LICENSE`.

---

## Important disclaimer
This tool is intended only for *tracking devices you own or have explicit permission to track*. Do not use for surveillance, stalking, or any unauthorized monitoring. See `TERMS.md` and `PRIVACY.md` for more.
