# Trusted PC Chrome Remote Debug Setup

Use this when Google/Suno blocks VPS headless login.

## On Windows PC PowerShell

Start Chrome debug profile:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="C:\suno-chrome"
```

If Chrome only listens on `127.0.0.1:9222`, bridge it to Tailscale:

```powershell
netsh interface portproxy add v4tov4 listenaddress=<TAILSCALE_PC_IP> listenport=9223 connectaddress=127.0.0.1 connectport=9222
New-NetFirewallRule -DisplayName "Chrome Remote Debug 9223" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9223
```

Verify:

```powershell
netstat -ano | findstr :9223
```

## From VPS

```bash
curl http://<TAILSCALE_PC_IP>:9223/json/version
```

Then connect with Chrome DevTools Protocol and extract the Suno Clerk cookie.
