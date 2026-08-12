Configuration has three parts: prepare the content on Microsoft 365, register an
application in Entra ID (Azure AD), and fill in the credentials in Odoo. Budget
about 20 minutes. Granting the permissions (step 2.2) needs a **Global
Administrator** or Privileged Role Administrator of the Microsoft tenant — the rest
can be done by whoever administers the courses.

## 1. On the SharePoint / Microsoft 365 side

### 1.1 Where the files must live

Any file readable by Microsoft Graph works:

| Source | Where it actually lives | Supported |
|---|---|---|
| SharePoint site document library | `contoso.sharepoint.com/sites/<site>` | Yes |
| Teams channel *Files* tab | the SharePoint site of the team | Yes |
| OneDrive for Business | `contoso-my.sharepoint.com/personal/<user>` | Yes |
| Teams meeting recording | OneDrive of the organiser, or the channel site | Yes |
| Stream (Classic) video never migrated | old Stream service | **No** |
| Personal (consumer) OneDrive | `onedrive.live.com` | **No** |

**Recommendation:** create one dedicated SharePoint site (e.g. *eLearning*) with
one library per course, instead of scattering lessons across personal OneDrives.
It keeps the permission grant of step 2.2 narrow, and a lesson does not break
when the person who uploaded it leaves the company.

### 1.2 What you do **not** need to do

These are the usual dead ends — skip them:

* **Do not** share the files with *"Anyone with the link"*. The Odoo server reads
  them with its own application identity; keep your default (restricted) sharing
  settings.
* **Do not** configure anything in *SharePoint admin center > Settings > Embedding*.
  That setting governs the `embed.aspx` iframe, which this module does not use.
* **Do not** create Microsoft accounts or guest invitations for your attendees.

### 1.3 Video format — read this before uploading

Odoo serves the **original file** to the browser's native `<video>` player. There
is no transcoding and no adaptive streaming, so the format must be one browsers
can play natively:

| Format | Result |
|---|---|
| **MP4 (H.264 video + AAC audio)** | Works everywhere — **use this** |
| WebM (VP8/VP9) | Works on Chrome/Firefox/Edge |
| MOV | Only if it wraps H.264 + AAC |
| MKV, AVI, WMV, FLV | **Does not play** |
| HEVC/H.265 in MP4 | Unreliable (no Chrome/Firefox support on many platforms) |

If you upload from Teams recordings you already get MP4/H.264 and nothing needs
to be done. For anything else, convert before uploading, e.g.:

```bash
ffmpeg -i lesson.mkv -c:v libx264 -profile:v high -c:a aac -movflags +faststart lesson.mp4
```

`-movflags +faststart` matters: it moves the index to the beginning of the file so
the attendee can start watching before the whole video is downloaded.

Also keep an eye on file size: every viewer downloads the full file, so a 4 GB
lesson costs 4 GB of Microsoft egress per attendee. Aim for 720p/1080p at a
reasonable bitrate.

### 1.4 Getting the link

Open the file in SharePoint, Teams or OneDrive and use **Copy link** (the *Share*
dialog works too). All of these are accepted:

```
https://contoso.sharepoint.com/:v:/s/elearning/EaBcDeF123?e=xYz789
https://contoso-my.sharepoint.com/:v:/g/personal/user_contoso_com/EaBcDeF123
https://contoso.sharepoint.com/sites/elearning/_layouts/15/stream.aspx?id=%2Fsites%2F...
https://contoso.sharepoint.com/sites/elearning/Shared%20Documents/lesson.mp4
https://1drv.ms/v/s!AbCdEf
```

The module does not parse these URLs itself — it asks Microsoft Graph to resolve
them — so link formats that Microsoft changes in the future keep working.

## 2. Register the application in Entra ID (Azure AD)

### 2.1 Create the registration

1. Go to [App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
   and click **New registration**.
2. Name it (e.g. `Odoo eLearning`), pick *Accounts in this organizational
   directory only*, and leave the redirect URI **empty** — this is a daemon
   application, no user ever signs in.
3. From the *Overview* page, copy the **Directory (tenant) ID** and the
   **Application (client) ID**.
4. In **Certificates & secrets > New client secret**, create a secret and copy its
   **value** immediately — it is shown only once. Note the expiry date: when the
   secret expires, videos stop loading, so put a reminder in your calendar.

### 2.2 Grant permissions

Two options. Pick the second one unless you are in a hurry.

**Option A — simple, broad (`Files.Read.All` + `Sites.Read.All`)**

In **API permissions > Add a permission > Microsoft Graph > Application
permissions**, add `Files.Read.All` and `Sites.Read.All`, then click **Grant admin
consent for \<tenant\>**.

This lets the application read *every* file of the tenant. It is the fastest path
and what most tutorials show, but it is a lot of authority for an eLearning
portal.

**Option B — least privilege (`Sites.Selected`), recommended**

Add only the `Sites.Selected` application permission and grant admin consent.
By itself it gives access to *nothing*: an administrator then authorises the
application site by site. With the [Microsoft Graph PowerShell SDK](https://learn.microsoft.com/en-us/powershell/microsoftgraph/):

```powershell
Connect-MgGraph -Scopes "Sites.FullControl.All"
$site = Get-MgSite -Search "elearning"          # note the returned site Id
New-MgSitePermission -SiteId $site.Id -BodyParameter @{
    roles = @("read")
    grantedToIdentities = @(@{ application = @{
        id = "<application-client-id>"; displayName = "Odoo eLearning" } })
}
```

Repeat for every site holding course content (including the OneDrive site of a
user, if you serve lessons from a personal OneDrive).

> **Important:** do **not** combine `Sites.Selected` with `Files.Read.All` or
> `Sites.Read.All`. The broad permissions win and the per-site restriction becomes
> meaningless — see the
> [Microsoft Graph permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference).

Either way, the permissions are **read-only**: the module never writes to
SharePoint.

### 2.3 Outbound hosts to allow

The Odoo server is the one talking to Microsoft, so if its outbound traffic is
filtered, these hosts have to be reachable **from the server**:

| Host | Needed for |
|---|---|
| `login.microsoftonline.com` | obtaining the application token |
| `graph.microsoft.com` | resolving links, reading metadata |
| `<tenant>.sharepoint.com`, `<tenant>-my.sharepoint.com`, `*.svc.ms` | downloading thumbnails and converted PDFs |

Nothing has to be opened *inbound*: no callback, no webhook, no redirect URI.

In *Stream through Odoo* delivery mode, the content hosts on the third row also
carry the media itself. In *Redirect* mode the attendee's browser fetches the media
straight from Microsoft, so those hosts must also be reachable **from the
attendees' network** — which is normally the case for anyone with internet access.

## 3. In Odoo

1. Go to **Website > Configuration > Settings > eLearning > Microsoft 365 /
   SharePoint** and fill in **Tenant ID**, **Client ID** and **Client Secret**.
2. Choose the **Delivery** mode:

   * **Redirect to Microsoft** (default) — Odoo answers with a redirection to a
     short lived pre-authenticated Microsoft URL. The media never transits through
     Odoo, which keeps the workers free. This is what you want for video.
     Trade-off: an attendee who inspects the page sees that Microsoft URL, and it
     stays usable for about an hour.
   * **Stream through Odoo** — Odoo downloads and re-streams the content, hiding
     the Microsoft URL. Range requests are honoured so seeking still works, but a
     worker is busy for the whole playback. Only pick this if exposing the
     temporary URL is unacceptable, and size your workers accordingly (one
     concurrent viewer = one busy worker).

The credentials are stored in `ir.config_parameter`
(`website_slides_sharepoint.tenant_id`, `.client_id`, `.client_secret`), which is
readable by administrators only. The application token is cached in the same place
and renewed automatically.

## 4. Check that it works

Add a video lesson with a SharePoint link (see USAGE). If the title, thumbnail and
duration are filled in automatically, the whole chain — token, Graph, permissions
— is working.

If it is not, the table below covers what actually goes wrong in practice. Server
log messages are emitted by `odoo.addons.website_slides_sharepoint`.

| Symptom | Cause | Fix |
|---|---|---|
| *"The Microsoft 365 integration is not configured"* | empty Tenant/Client/Secret | step 3 |
| *"Could not authenticate against Microsoft 365"* | wrong tenant/client id, or **expired client secret** | recreate the secret (2.1) |
| *"The file could not be found on SharePoint, or the Odoo application does not have permission"* | admin consent missing, or the site was not granted under `Sites.Selected` | 2.2 |
| Metadata is fetched but the player stays black | video codec not supported by browsers | 1.3, re-encode to MP4/H.264 |
| Video plays but seeking is impossible | `moov` atom at the end of the file | re-encode with `-movflags +faststart` |
| Office document shows an error instead of a PDF | conversion timed out (large or complex file) | see ROADMAP; upload a PDF instead |
| Everything works for staff, nothing for anonymous visitors | the course/lesson is not published, or the lesson is members-only | publish the course, or tick *Allow Preview* |
| Sporadic failures under load | Graph throttling (HTTP 429) | spread the load, prefer *Redirect* mode |
