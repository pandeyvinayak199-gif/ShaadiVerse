# Install ShaadiVerse on your phone

ShaadiVerse is an installable web app (PWA). It uses your existing HTTPS deployment and database, with a home-screen icon and its own standalone window. No APK download, Play Store account, or App Store account is needed for this release.

## Update your deployment once

In Render, open the existing web service and choose **Manual Deploy → Deploy latest commit**. Then open its public `https://…onrender.com` address, not the dashboard URL. If you still see old branding or controls, reload or close and reopen the browser tab.

## Android

1. Open the app’s public link in **Chrome**, in a normal browser tab.
2. Tap **Install ShaadiVerse** if offered. Otherwise tap **Get ShaadiVerse on your phone**, or use Chrome’s **⋮ → Install app / Add to Home screen → Install**.
3. Confirm installation and open **ShaadiVerse** from your home screen.

Chrome normally hides installation in Incognito/private browsing. Links opened inside WhatsApp or Instagram should first be opened in Chrome. Chrome decides when to offer its native installation prompt; the app also provides manual instructions.

## iPhone / iPad

1. Open the public app link in **Safari**.
2. Tap **Share**, then **Add to Home Screen**.
3. Leave **Open as Web App** enabled if that switch is shown.
4. Tap **Add** and launch **ShaadiVerse** from the home screen.

You may need to enter the existing private-demo credentials again (`demo` and the configured demo access password). Installing the app does not create new hosting accounts or activate deferred SMS, WhatsApp or payments.

## Connectivity

Sign-in, loading current event data, saving changes and submitting pilot feedback need Internet. Once an organiser has opened the gate online, its offline shell can reopen and queue scans. Queued scans are pending until server verification; the installed app does not approve admission while disconnected. The service worker does not cache guest/API/pass responses. If there is no saved gate session, an offline launch shows a reconnect screen.

The full-screen window and final home-screen installation should be checked on your actual device. Browser validation confirms the manifest, icon dimensions, service worker, Android prompt handling, iPhone guidance, phone layout, offline launch, and cache exclusions; it does not emulate tapping an OS installation confirmation on real hardware.
