Known limitations, and what they mean in practice.

**Video is served as-is, with no transcoding.** The browser plays the original
file, so the format has to be browser-friendly (MP4/H.264 — see CONFIGURE 1.3) and
there is no adaptive bitrate: every attendee downloads the full quality of the
file. Building a transcoding pipeline is out of scope; if you need HLS/DASH, put a
real video platform in front.

**Office to PDF conversion inherits Microsoft's limits.** Graph converts
Word/Excel/PowerPoint on the fly, but the conversion
[times out after roughly 45 seconds](https://learn.microsoft.com/en-us/answers/questions/5679108/microsoft-graph-pdf-conversion-timing-out-at-45-se),
which large or complex documents hit well below the documented 100 MB ceiling.
Excel is additionally capped at 250 pages, and macro-enabled formats (`.docm`,
`.xlsm` in some cases) are not converted at all. For heavy documents, upload a PDF
to SharePoint instead — PDFs are served directly, without conversion.

**Completion time is only computed for files under 30 MB.** Odoo has to download
the document to count its pages; above that threshold the duration is left for you
to fill in manually. Videos are unaffected: the duration comes from the Graph
metadata.

**Slides store a Microsoft item id, not a copy of the file.** Moving a file to
another site, or deleting it, breaks the lesson with a 404. Renaming is fine.

**The pre-authenticated URL is cached for 45 minutes.** In *Redirect* delivery
mode, an attendee who copies that URL out of their browser can reshare it until it
expires. Use *Stream through Odoo* if that matters more than worker capacity.

**Stream (Classic) videos and live events are not supported**, because Microsoft
Graph cannot read them as drive items.

**No `slide.embed` view counting for external embeds.** The lesson can be embedded
on a third party website, and the media loads, but the SharePoint player has no
iframe of its own so the native external-embed statistics of `website_slides` are
less meaningful than for YouTube.

Possible improvements, in rough order of usefulness:

* certificate-based authentication instead of a client secret, to get rid of the
  yearly secret rotation;
* a *Test connection* button in the settings, instead of relying on the first
  lesson to validate the credentials;
* resumable playback (store the last position per attendee), which the HTML5
  player makes easy and the YouTube/Vimeo integrations do not offer either.
