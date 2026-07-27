/** @odoo-module **/

import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";
import publicWidget from "web.public.widget";

/**
 * Plays a SharePoint video with the native HTML5 player.
 *
 * SharePoint has no embeddable player API, but since the content is served by
 * Odoo itself (see the /slides/sharepoint/content controller) we can use a plain
 * <video> element and get the completion tracking that the YouTube and Vimeo
 * integrations provide.
 */
const VideoPlayerSharepoint = publicWidget.Widget.extend({
    template: "website_slides_sharepoint.fullscreen.video",

    init: function (parent, slide) {
        this.slide = slide;
        return this._super.apply(this, arguments);
    },

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            this.videoElement = this.el.querySelector("video");
            this.videoElement.addEventListener(
                "timeupdate",
                this._onVideoTimeUpdate.bind(this)
            );
            this.videoElement.addEventListener("ended", this._onVideoEnded.bind(this));
        });
    },

    // --------------------------------------------------------------------------
    // Handlers
    // --------------------------------------------------------------------------

    /**
     * Go to the next slide once the video is over, like the other players do.
     */
    _onVideoEnded: function () {
        if (this.slide.hasNext) {
            this.trigger_up("slide_go_next", this.slide);
        }
    },

    /**
     * Mark the slide as completed once the attendee reaches the end of the video.
     * The 30 seconds tolerance matches the YouTube and Vimeo players, but is
     * capped for short videos so that they can be completed at all.
     */
    _onVideoTimeUpdate: function () {
        const duration = this.videoElement.duration;
        if (!duration || !isFinite(duration)) {
            return;
        }
        const completionThreshold = Math.max(duration - 30, duration * 0.95);
        if (this.videoElement.currentTime < completionThreshold) {
            return;
        }
        if (this.slide.isMember && !this.slide.hasQuestion && !this.slide.completed) {
            this.trigger_up("slide_mark_completed", this.slide);
        }
    },
});

Fullscreen.include({
    /**
     * The native implementation appends YouTube player parameters to the embed
     * URL, which makes no sense for a plain media URL served by Odoo.
     *
     * @override
     */
    _preprocessSlideData: function (slidesDataList) {
        const slides = this._super(slidesDataList);
        slides.forEach((slideData) => {
            if (this._isSharepointVideo(slideData)) {
                slideData.embedUrl = `/slides/sharepoint/content/${slideData.id}`;
                // The player marks the slide as completed on its own.
                slideData._autoSetDone = false;
            }
        });
        return slides;
    },

    /**
     * @override
     */
    _renderSlide: async function () {
        const slide = this.get("slide");
        if (slide.isQuiz || !this._isSharepointVideo(slide)) {
            return this._super.apply(this, arguments);
        }
        if (this._renderSlideRunning) {
            return;
        }
        this._renderSlideRunning = true;
        try {
            const $content = this.$(".o_wslides_fs_content");
            $content.empty();
            if (this.websiteAnimateWidget) {
                this.websiteAnimateWidget.destroy();
                this.websiteAnimateWidget = null;
            }
            this.videoPlayer = new VideoPlayerSharepoint(this, slide);
            return await this.videoPlayer.appendTo($content);
        } finally {
            this._renderSlideRunning = false;
        }
    },

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _isSharepointVideo: function (slideData) {
        return (
            slideData.category === "video" && slideData.videoSourceType === "sharepoint"
        );
    },
});

export default VideoPlayerSharepoint;
