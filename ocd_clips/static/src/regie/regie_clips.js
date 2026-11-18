import { patch } from "@web/core/utils/patch";

import { OcdLiveRegie } from "@ocd_live_shop/regie/regie";

/**
 * The control room at the end of the live (design ClipsAutomatiques): « Send the video of the
 * live » beside « Publish the replay », with where its clips stand.
 */
patch(OcdLiveRegie.prototype, {
    openClips() {
        this.actionService.doAction(this.data().clips.action);
    },
});
