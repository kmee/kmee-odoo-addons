## Adding a lesson from the website

In a course, click **Add Content** and:

* **Video**: paste the SharePoint / OneDrive link in *Video Link*. Get it with the
  **Copy link** button of SharePoint, Teams or OneDrive. The title, thumbnail and
  duration are filled in automatically.
* **Document**: choose *Retrieve from Google Drive or SharePoint* and paste the
  SharePoint link. PDF files are served directly; Word, Excel and PowerPoint files
  are converted to PDF by Microsoft Graph.
* **Image**: same as documents.

The source is detected from the link itself, so there is no extra option to pick:
a Google Drive link keeps using the native Google integration and a SharePoint
link goes through Microsoft Graph.

## Adding a lesson from the backend

**eLearning > Courses > (a course) > Content**. Set *Content Type*, then:

* for a video, paste the link in *Video Link* — *Video Source* switches to
  **SharePoint** on its own;
* for a document or an image, set the source to *Retrieve from SharePoint* and use
  the *SharePoint Document Link* / *SharePoint Image Link* field.

## What attendees see

Nothing Microsoft-specific: no login prompt, no consent screen, not even a
Microsoft account. Videos play in the browser's own player, and the lesson is
marked as completed automatically when the attendee reaches the end — the same
behaviour as YouTube and Vimeo lessons.

There is no need to change the sharing settings of the file on SharePoint. Access
is controlled by the eLearning rules only: an attendee can watch a video if, and
only if, they can access the lesson (published course, *Allow Preview* lesson, or
course membership). Course officers can always access it.

## Day-to-day operations

* **Replacing a video**: edit the lesson and paste the new link. The cached
  Microsoft identifiers and URL are dropped and re-resolved.
* **Moving files on SharePoint**: avoid it, or fix the links afterwards — see
  ROADMAP.
* **Rotating the client secret**: put a reminder before its expiry date. When it
  expires, every SharePoint lesson stops loading at once; replacing the secret in
  the settings is enough, the cached token is renewed automatically.
