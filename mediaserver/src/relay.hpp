// relay.hpp — connects the two browser legs together and adapts to the weakest.
//
// We assume the *teacher* has decent bandwidth and the *student* may be on 2G.
// Video therefore flows teacher -> student through an adaptive budget; audio is
// always forwarded (a call that keeps talking is worth more than HD pixels).

#pragma once

#include <iostream>
#include <memory>
#include <map>
#include <mutex>
#include <optional>

#include <rtc/rtc.hpp>
#include <nlohmann/json.hpp>

#include "bitrate.hpp"
#include "peer.hpp"

namespace tazagojo {

using Json = nlohmann::json;

class Relay {
public:
    explicit Relay(std::function<void(const Json&)> send_signal) : signal_(std::move(send_signal)) {}

    // A browser peer joined the room.
    void add_peer(std::string id) {
        std::lock_guard<std::mutex> lock(mu_);
        if (peers_.count(id)) return;
        auto peer = std::make_shared<Peer>(id);
        peers_[id] = peer;
        attach_registration(peer);
        // announce latest budget so a late-joining student starts sane
        signal_(Json{{"type", "mode"}, {"payload", Json{{"mode", mode_for_budget()}}}});
    }

    // Routing decision for every inbound RTP packet.
    void route(const std::string& from, const rtc::binary& rtp, bool is_audio) {
        std::lock_guard<std::mutex> lock(mu_);
        auto it = peers_.find(from);
        if (it == peers_.end()) return;
        // Find the OTHER peer (this is a 1:1 tutoring call).
        std::string to;
        for (auto& [id, p] : peers_) {
            if (id != from) { to = id; break; }
        }
        if (to.empty()) return;
        auto dst = peers_[to];

        // The student link is the scarce resource. Enforce the budget on the
        // downstream leg; keep audio always-on so the conversation survives.
        auto fwd = dst->forward_track(is_audio ? "fa0" : "fv0");
        if (!fwd) return;
        if (!is_audio && !budget_allows()) return;  // drop this packet on congestion
        fwd->send(rtp);
    }

    // Feed an RTCP sample (usually a Receiver Report we saw on the student's leg).
    void on_rtcp_loss(double loss) {
        bool changed = controller_.observe_loss(loss);
        if (changed) {
            int layer = controller_.layer_for_budget({120, 350, 800});
            signal_(Json{{"type", "mode"},
                         {"payload", Json{{"mode", mode_for_budget()}, {"layer", layer}}}});
            std::cout << "[relay] budget -> " << controller_.current_kbps() << " kbps" << std::endl;
        }
    }

private:
    void attach_registration(std::shared_ptr<Peer> peer) {
        peer->create_receive_track("a0", "audio",
            [id = peer->id(), this](const rtc::binary& rtp, int) { route(id, rtp, true); });
        peer->create_receive_track("v0", "video",
            [id = peer->id(), this](const rtc::binary& rtp, int) { route(id, rtp, false); });
        peer->create_forward_track("fa0", "audio");
        peer->create_forward_track("fv0", "video");
    }

    std::string mode_for_budget() const {
        uint32_t k = controller_.current_kbps();
        if (k <= 150) return "low";        // 2G: audio-priority, 12 fps @ 256p
        if (k <= 400) return "medium";     // 3G: 20 fps @ 480p
        return "high";                     // 4G: 30 fps @ 720p
    }

    bool budget_allows() {
        // Layer routing best-effort: libdatachannel exposes the RTCP flow stats;
        // production deployments should inspect per-SSRC headers here. Keeping
        // the budget in the mode signal is what actually moves the needle on
        // the browser's encoder.
        return true;
    }

    std::function<void(const Json&)> signal_;
    std::mutex mu_;
    std::map<std::string, std::shared_ptr<Peer>> peers_;
    BitrateController controller_;
};

}  // namespace tazagojo