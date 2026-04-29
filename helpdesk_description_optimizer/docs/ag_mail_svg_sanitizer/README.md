# AG Mail SVG Sanitizer

Sanitizes incoming email bodies by removing `<img>` tags that point to external SVG
files (domains different from `web.base.url`). This prevents the Odoo backend from
attempting to render untrusted SVGs in the mail composer, avoiding browser
`SecurityError` exceptions (tainted canvas) when replying or forwarding messages.
