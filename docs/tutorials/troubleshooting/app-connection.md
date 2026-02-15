# App Won't Connect

**Estimated reading time: 4 minutes**

When the ApexPocket Android app cannot reach the backend -- showing errors, failing to load messages, or stuck on a connecting screen -- work through this decision tree from top to bottom.

---

## Step 1: Does Your Phone Have Internet?

Open your phone's web browser and load any website (not a cached page -- try something like `example.com`).

- **Website loads** -- internet is working, proceed to Step 2.
- **Website fails to load** -- connect to Wi-Fi or enable mobile data. The app requires an internet connection to communicate with the cloud backend.

---

## Step 2: Is the Backend Reachable?

Open your phone's browser and visit:

```
https://backend-production-507c.up.railway.app/health
```

- **JSON response with "status": "ok"** -- backend is up and reachable from your phone. Proceed to Step 3.
- **Page does not load, timeout, or error** -- the backend may be temporarily down. Railway auto-restarts failed services, so wait 2-3 minutes and try again. If it stays down for more than 10 minutes, the issue is server-side, not on your phone.

---

## Step 3: Check Connection Status in the App

Open ApexPocket and go to **Settings** (gear icon or bottom navigation).

Look at the connection status indicator:

- **"CONNECTED" (green)** -- the app is connected. If you are experiencing issues with specific features, the problem may be a stale session. Try pulling down to refresh on the main chat screen.
- **"DISCONNECTED" (red)** -- tap the **Sync** or **Reconnect** button if available. Wait 10 seconds.
  - If it reconnects, the issue was a temporary network blip.
  - If it stays disconnected, proceed to Step 4.
- **No device shown at all** -- the app is not paired with any device. You need to log in again or re-pair. See Step 4.

---

## Step 4: Check Your Account

Try logging in on the web dashboard from any device:

```
https://frontend-production-5402.up.railway.app
```

- **Login succeeds** -- your account works. The app token may be expired or corrupted.
  - In ApexPocket: log out (Settings page), then log back in with the same credentials.
  - If logging out is not possible, clear the app cache (see Step 5) and log in fresh.
- **Login fails ("invalid credentials")** -- reset your password on the web dashboard, then use the new password in the app.
- **Login fails ("account not found")** -- you may need to create a new account on the web dashboard first. The app does not support account creation -- only login.

---

## Step 5: Clear the App Cache

If the app is behaving strangely (stuck screens, stale data, repeated errors):

1. Open your phone's **Settings** app (the Android system settings, not the ApexPocket settings).
2. Go to **Apps** (or **Applications**).
3. Find and tap **ApexPocket**.
4. Tap **Storage**.
5. Tap **Clear Cache**.

> **Warning:** Do NOT tap "Clear Data" unless you want to completely reset the app. "Clear Data" wipes all local state including cached conversations and preferences. "Clear Cache" only removes temporary files and is safe.

After clearing cache, open ApexPocket and log in again.

---

## Step 6: Check Android Version

ApexPocket requires **Android 8.0 (Oreo)** or later, which is API level 26.

Check your Android version:
1. Open **Settings**.
2. Scroll to **About Phone**.
3. Look for **Android version**.

If your version is below 8.0, ApexPocket will not work on your device. You need a newer phone or tablet.

---

## Step 7: Reinstall the App

If nothing above resolves the issue:

1. Download the latest APK:

   ```
   https://frontend-production-5402.up.railway.app/downloads/apexpocket.apk
   ```

2. Install it over the existing installation (this preserves your data while updating the app binary).
3. Open the app and log in.

If you want a completely fresh start, uninstall ApexPocket first, then install the new APK.

---

## Step 8: Network-Specific Issues

Some networks block WebSocket connections or certain ports. If you can reach the health endpoint in a browser but the app still cannot connect:

- **Corporate or school Wi-Fi** -- these networks often block WebSocket traffic. Try switching to mobile data or a personal hotspot to test.
- **VPN active** -- some VPNs interfere with WebSocket connections. Try disabling the VPN temporarily.
- **DNS issues** -- if your network uses custom DNS that does not resolve Railway domains, try switching to Google DNS (8.8.8.8) or Cloudflare DNS (1.1.1.1) in your phone's Wi-Fi settings.

---

## Still Not Connecting?

1. Check if the issue is specific to the app by testing the web dashboard on your phone's browser. If the web dashboard works but the app does not, the issue is app-specific.
2. Try from a different network (switch between Wi-Fi and mobile data).
3. Check the ApexAurum status page or ask in the community for known outages.
