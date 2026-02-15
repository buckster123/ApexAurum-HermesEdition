# Pair Your Phone

**Estimated reading time: 6 minutes**

Install the ApexPocket app on your Android phone, create your account, and connect to your SensorHead. By the end of this guide, you will be chatting with AZOTH through your phone while your Pi reads the room around you.

---

## Prerequisites

- A Raspberry Pi 5 set up and running (see [01 - First Boot](./01-first-boot.md))
- An Android phone running **Android 8.0 (Oreo) or later**
- A working internet connection on both devices

---

## Step 1: Get the APK

Download the ApexPocket app from the ApexAurum website:

```
https://frontend-production-5402.up.railway.app/downloads/apexpocket.apk
```

You can also scan the QR code on the SensorHead product page, which links to the same download.

> **Tip:** If you are reading this on your phone, just tap the link above. If you are on a computer, the easiest approach is to scan the QR code with your phone's camera.

---

## Step 2: Install on Android

Since ApexPocket is distributed as a direct APK (not through the Google Play Store), your phone will ask for permission to install it.

1. Open the downloaded `.apk` file.
2. Your phone will display a warning about installing from unknown sources.
3. Tap **Settings** when prompted, then enable **Allow from this source** for your browser or file manager.
4. Go back and tap **Install**.

The app is lightweight -- around 15MB -- so installation should be nearly instant.

> **Note:** Allowing installs from unknown sources only applies to the app you used to download the APK (usually Chrome or your file manager). It does not open your phone to arbitrary installs.

---

## Step 3: Open the App

Launch ApexPocket. On first open, you will see the **pairing screen** with the ApexAurum logo and a field asking for your credentials. Do not worry about this yet -- you need an account first.

---

## Step 4: Create Your Account

Open a web browser (on your phone or computer) and go to the ApexAurum dashboard:

```
https://frontend-production-5402.up.railway.app
```

1. Click **Sign Up** in the top right.
2. Enter your email, choose a password, and create your account.
3. Confirm your email if prompted.
4. Log in to the dashboard.

You now have an ApexAurum account. This same account works for the web dashboard, the mobile app, and the SensorHead bridge.

---

## Step 5: Get Your Device Token

In the web dashboard:

1. Navigate to the **Devices** page (in the sidebar or settings menu).
2. Click **Add Device**.
3. Give your device a name (e.g., "Living Room SensorHead" or "Office Pi").
4. The system will generate a **device token** -- a long string of characters.
5. Copy this token. You will need it in the next step.

> **Tip:** You can email or message the token to yourself if you need to transfer it from your computer to your Pi. It is a one-time setup value, not a secret key, so it is safe to send over normal channels.

---

## Step 6: Configure the Pi

SSH into your Raspberry Pi (or use the terminal if you have a monitor connected):

```bash
ssh hailo@sensorhead.local
```

Edit the SensorHead configuration file:

```bash
nano ~/claude-root/SensorHead/config.json
```

Find the `"device_token"` field and paste your token:

```json
{
  "device_token": "YOUR_TOKEN_HERE",
  "api_url": "https://backend-production-507c.up.railway.app",
  "bridge_port": 8765
}
```

Save the file (Ctrl+O, then Enter, then Ctrl+X to exit nano).

> **Note:** If the `config.json` file does not exist yet, create it with the content shown above. The `api_url` and `bridge_port` values shown are the defaults.

---

## Step 7: Restart the Bridge

The SensorHead bridge is the service that connects your Pi's sensors to the ApexAurum cloud. Restart it to pick up the new configuration:

```bash
sudo systemctl restart sensorhead-bridge
```

Check that it started successfully:

```bash
sudo systemctl status sensorhead-bridge
```

You should see `active (running)` in green. If you see any errors, check the logs:

```bash
journalctl -u sensorhead-bridge -n 50 --no-pager
```

---

## Step 8: Connect from the App

Go back to the ApexPocket app on your phone:

1. Log in with the same email and password you created in Step 4.
2. The app will automatically detect your registered device.
3. You should see a **Connected** status indicator turn green.
4. Try sending a message: type "hello" and send it.

AZOTH will respond. You are now talking to an AI agent that has access to your SensorHead's environmental sensors, cameras, and thermal array -- all through your phone.

---

## Troubleshooting

**"Connection failed" or stuck on connecting**

- Make sure your Pi is powered on and connected to the internet.
- Verify the bridge is running: `sudo systemctl status sensorhead-bridge`
- Check that the device token in `config.json` matches the one from the dashboard.
- Ensure your Pi can reach the internet: `ping -c 3 google.com`

**App crashes on launch**

- Make sure you are running Android 8.0 or later. Check in Settings > About Phone.
- Try uninstalling and reinstalling the APK.
- If the issue persists, clear the app's data in Android Settings > Apps > ApexPocket > Storage > Clear Data.

**"Device not found" in the app**

- Log out and log back in to refresh your device list.
- Go to the web dashboard and verify the device still appears under Devices.
- Restart the bridge on the Pi and wait 30 seconds before trying again.

**Bridge keeps crashing**

- Check the logs with `journalctl -u sensorhead-bridge -n 100 --no-pager`
- Common cause: invalid JSON in `config.json`. Run `python3 -m json.tool ~/claude-root/SensorHead/config.json` to validate the syntax.
- Another common cause: incorrect API URL. Make sure it starts with `https://`.

---

## What You Have Now

- An ApexAurum account connected to your Pi
- The ApexPocket app installed and paired
- A working communication channel between your phone and your SensorHead
- The ability to chat with AZOTH (and the other agents) from anywhere

---

## What's Next

Now that you are connected, it is time to meet the four AI agents who live in the Village.

--> [03 - Meet the Agents](./03-meet-the-agents.md)
