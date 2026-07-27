Odoo eLearning (`website_slides`) only accepts YouTube, Vimeo and Google Drive as
external content sources. This module adds **SharePoint Online / OneDrive for
Business** (Microsoft 365) as a fourth source, for both videos and documents.

Microsoft does not support anonymous embedding of SharePoint videos: the native
`embed.aspx` iframe only renders for a visitor who already has a Microsoft 365
session in their browser. This module therefore does **not** use that iframe.
Instead, the Odoo server itself authenticates against Microsoft Graph with an
Entra ID (Azure AD) application using the client credentials flow, resolves the
shared link and serves the content to the attendee. As a consequence:

* attendees do **not** need a Microsoft account, not even a login prompt;
* the files stay private on SharePoint — no "Anyone with the link" sharing;
* videos play in the native HTML5 player, so **completion tracking works** just
  like it does for YouTube and Vimeo (the SharePoint iframe offers no player API);
* Word, Excel and PowerPoint documents are converted to PDF on the fly by
  Microsoft Graph, so they display in the course viewer.

Supported links are whatever Microsoft Graph can resolve: sharing links
(`/:v:/s/...`, `/:b:/s/...`), `stream.aspx` links, OneDrive short links
(`1drv.ms`) and direct file URLs.
