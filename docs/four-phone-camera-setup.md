# Four Phone Camera Setup

This setup runs the StoreSense live pipeline on the Ubuntu server laptop. Four
phones send camera streams to the server, MediaMTX receives them, and the Python
app reads those streams through OpenCV before YOLO and the existing analytics
pipeline process the frames.

## Camera Paths

Use these stable camera IDs everywhere:

```text
entry-cam
queue-cam-1
queue-cam-2
shelf-cam-1
```

## Server Setup

Run these on the Ubuntu server laptop:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git ffmpeg docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in after adding the user to the `docker` group, then start from
the project folder:

```bash
cd ~/FINAL-RETAILAI
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-live.txt
cp .env.example .env
```

Find the server LAN IP:

```bash
hostname -I
```

Start MediaMTX:

```bash
docker compose -f deploy/mediamtx/docker-compose.yml up -d
docker compose -f deploy/mediamtx/docker-compose.yml ps
```

If Ubuntu firewall is enabled:

```bash
sudo ufw allow 8554/tcp
sudo ufw allow 8080/tcp
```

## Phone Setup

Connect all four phones to the same Wi-Fi as the server laptop. In the phone
camera streaming app, publish each phone to one path on the server:

```text
rtsp://<server-lan-ip>:8554/entry-cam
rtsp://<server-lan-ip>:8554/queue-cam-1
rtsp://<server-lan-ip>:8554/queue-cam-2
rtsp://<server-lan-ip>:8554/shelf-cam-1
```

Keep the phones plugged in, keep the stream app open, and disable battery
optimization for that app during testing.

## Verify Phones Are Publishing (before touching Python)

MediaMTX exposes its own HTTP API on port 9997. This is the fastest way to
confirm a phone's stream actually arrived at the server - no Python, OpenCV,
or YOLO involved yet:

```bash
curl -s http://localhost:9997/v3/paths/list | python3 -m json.tool
```

Each camera ID that has a phone actively publishing to it appears as a path
with a non-empty `source`. A camera that never shows up here means the phone
never reached MediaMTX - fix that before debugging the Python side at all.

## Verify Streams

After all four phones are publishing, run:

```bash
source venv/bin/activate
python scripts/check_live_cameras.py
```

All four cameras should print `[OK]`. If one prints `[FAIL]`, check that phone's
Wi-Fi, stream app path, and server IP.

## Start StoreSense Live AI

```bash
source venv/bin/activate
python start_storesense.py --no-hardware --live-ai
```

The API should be available from another laptop at:

```text
http://<server-lan-ip>:8080/health
http://<server-lan-ip>:8080/api/metrics
```

## Troubleshooting Choppy/Corrupted Video

If frames look corrupted or the connection is unstable over WiFi, the RTSP
source defaults to TCP transport with a 5-second connect timeout. Override
either with environment variables if needed:

```bash
STORESENSE_RTSP_TRANSPORT=udp      # default: tcp
STORESENSE_RTSP_TIMEOUT_MS=8000    # default: 5000
```

## If `xlink` Does Not Resolve

SSH can use the server IP directly:

```bash
ssh sarv1@<server-lan-ip>
```

Or add a hosts entry on the client laptop so `sarv1@xlink` works:

```text
<server-lan-ip> xlink
```

On Windows, that hosts file is:

```text
C:\Windows\System32\drivers\etc\hosts
```

