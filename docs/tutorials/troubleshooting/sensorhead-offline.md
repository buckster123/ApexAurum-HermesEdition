# SensorHead Offline

**Estimated reading time: 5 minutes**

When the ApexPocket app or web dashboard shows your SensorHead as disconnected, work through this decision tree from top to bottom. Each step either resolves the issue or tells you to continue to the next check.

---

## Step 1: Is the Bridge Service Running?

Check the systemd service status:

```bash
systemctl status sensorhead-bridge
```

- **Active (running)** -- proceed to Step 2.
- **Inactive (dead)** or **failed** -- start the service:

  ```bash
  sudo systemctl start sensorhead-bridge
  ```

  Wait 5 seconds, then check status again. If it starts successfully, check the app -- the device should come online within 10-15 seconds.

  - Still failing? Check the logs:

    ```bash
    journalctl -u sensorhead-bridge -n 50 --no-pager
    ```

    Look for Python tracebacks or `ModuleNotFoundError`. Common causes:
    - Virtual environment not activated in the service unit file
    - Missing Python dependency (run `pip install -r requirements.txt` in the SensorHead venv)
    - Permission error on config file (see Step 4)

---

## Step 2: Does the Pi Have Internet?

```bash
ping -c 3 google.com
```

- **Success (replies received)** -- proceed to Step 3.
- **Failure (network unreachable or 100% packet loss)** -- check Wi-Fi:

  ```bash
  nmcli device wifi list
  ```

  If your network is visible, reconnect:

  ```bash
  sudo nmcli device wifi connect "YOUR_NETWORK" password "YOUR_PASSWORD"
  ```

  If no networks are listed, check if the Wi-Fi adapter is enabled:

  ```bash
  nmcli radio wifi
  ```

  If disabled:

  ```bash
  nmcli radio wifi on
  ```

  If using Ethernet, check the cable and run `ip addr` to verify an IP address is assigned on `eth0`.

---

## Step 3: Can the Bridge Reach the Cloud?

Check the backend health endpoint:

```bash
curl -s https://backend-production-507c.up.railway.app/health | python3 -m json.tool
```

- **JSON response with status "ok"** -- backend is up, proceed to Step 4.
- **Connection refused or timeout** -- the cloud backend may be down. Railway auto-restarts services, so wait 2-3 minutes and try again. If it persists for more than 10 minutes, the issue is on the cloud side, not your SensorHead.
- **SSL certificate error** -- check that the system clock is correct:

  ```bash
  date
  ```

  If the date is wrong (common after long power outages), update it:

  ```bash
  sudo timedatectl set-ntp true
  ```

Now check the bridge logs for WebSocket connection messages:

```bash
journalctl -u sensorhead-bridge -f --no-pager -n 50
```

Look for these messages:

- `"Bridge connected to cloud"` -- connection is working, issue may be intermittent.
- `"Connection refused"` or `"WebSocket handshake failed"` -- backend is rejecting the connection. Proceed to Step 4.
- `"Bridge disconnected... Reconnecting in Xs"` -- the bridge is in reconnect mode. It uses exponential backoff up to 5 minutes. You can restart the service to reset the backoff:

  ```bash
  sudo systemctl restart sensorhead-bridge
  ```

---

## Step 4: Is the Configuration Correct?

Check the bridge configuration file:

```bash
cat ~/.config/sensorhead/bridge.json
```

Verify these fields:

| Field | Expected Value |
|-------|---------------|
| `cloud_url` | `https://backend-production-507c.up.railway.app` |
| `ws_url` | `wss://backend-production-507c.up.railway.app/ws/bridge` |
| `device_token` | A real token (not empty, not `"YOUR_TOKEN_HERE"`) |
| `device_id` | A UUID string |

Common problems:

- **Token is empty or placeholder** -- you need to register the device on the web dashboard (Devices page) and get a real token. See [02 - Pair Your Phone](../quick-start/02-pair-your-phone.md).
- **Wrong cloud_url** -- must start with `https://`, not `http://`.
- **ws_url missing** -- the bridge auto-derives it from `cloud_url`, but if present, it must use `wss://`.
- **Invalid JSON** -- validate the syntax:

  ```bash
  python3 -m json.tool ~/.config/sensorhead/bridge.json
  ```

  If this prints an error, fix the JSON (missing commas, unquoted strings, trailing commas are common).

- **Permission denied** -- the config file should be readable by your user:

  ```bash
  ls -la ~/.config/sensorhead/bridge.json
  ```

  Should show `-rw-------` (owner read/write only). If it is owned by root:

  ```bash
  sudo chown $USER:$USER ~/.config/sensorhead/bridge.json
  ```

---

## Step 5: Restart the Bridge

After fixing any issues found above:

```bash
sudo systemctl restart sensorhead-bridge
```

Wait 10 seconds, then check:

```bash
systemctl status sensorhead-bridge
```

And tail the logs to confirm connection:

```bash
journalctl -u sensorhead-bridge -f --no-pager
```

You should see `"Bridge connected to cloud"` within a few seconds of startup.

---

## Step 6: Check for Zombie Processes

If the service shows as failed but a bridge process is still running, it may be stuck:

```bash
ps aux | grep sensor_head
```

If you see a `sensor_head.bridge` process with a PID but the service is dead, kill the orphan:

```bash
sudo kill -9 <PID>
```

Then start the service fresh:

```bash
sudo systemctl start sensorhead-bridge
```

---

## Step 7: Full Reset

If nothing above works, perform a complete stop-and-start cycle:

```bash
sudo systemctl stop sensorhead-bridge
sleep 3
ps aux | grep sensor_head | grep -v grep
```

If any processes remain, kill them. Then start clean:

```bash
sudo systemctl start sensorhead-bridge
```

Check the very first log lines for initialization errors:

```bash
journalctl -u sensorhead-bridge --since "1 minute ago" --no-pager
```

---

## Still Offline?

If you have worked through every step and the SensorHead still shows as offline:

1. Verify your account is active on the web dashboard (billing page).
2. Try unpairing and re-pairing the device on the Devices page.
3. Check that your Pi's hostname resolves correctly: `hostname -I` should show a valid IP.
4. On the web dashboard, check the device's "Last seen" timestamp -- if it shows a recent time, the bridge is connecting but the app may not be refreshing. Pull down to refresh in ApexPocket.
