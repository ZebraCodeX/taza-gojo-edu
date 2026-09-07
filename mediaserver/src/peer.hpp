// peer.hpp — one participant's leg of the relayed WebRTC call.
//
// A `Peer` owns a single PeerConnection toward one browser client. For that leg
// we are a pure forwarder:
//   - ONE receive track  (recvonly)   — whatever the browser sends to us
//   - ONE forward track  (sendonly)   — whatever we send to the browser
//
// The relay (relay.hpp) connects "the far side's receive track" to "this side's
// forward track". The browser negotiates ordinary audio+video (we answer with
// the same codecs it offered; no transcoding happens here — cheap CPU, no FEC
// burn on the school's router).

#pragma once

#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include <rtc/rtc.hpp>

namespace tazagojo {

class Peer : public std::enable_shared_from_this<Peer> {
public:
    using MediaHandler = std::function<void(const rtc::binary& rtp, int ssrc)>;

    explicit Peer(std::string id) : id_(std::move(id)) {
        std::cout << "[peer] creating leg " << id_ << std::endl;
        pc_ = std::make_shared<rtc::PeerConnection>(config());
        pc_->onStateChange([](rtc::PeerConnection::State s) {
            std::cout << "[peer] pc state: " << s << std::endl;
        });
        pc_->onGatheringStateChange([](rtc::PeerConnection::GatheringState s) {
            std::cout << "[peer] gathering: " << s << std::endl;
        });
    }

    static rtc::Configuration config() {
        rtc::Configuration c;
        // In congested/mobile environments STUN+ICE fixes ~most NAT traversal.
        // Deploy a TURN server next to the mediaserver for the hard cases.
        c.iceServers.emplace_back("stun:stun.l.google.com:19302");
        // c.iceServers.emplace_back("turn:turn.example.org:3478?transport=udp");
        c.portRangeBegin = 50000;   // keep the school firewall happy
        c.portRangeEnd = 50100;
        return c;
    }

    std::shared_ptr<rtc::PeerConnection> pc() const { return pc_; }

    // Browser -> server leg. For each media type the browser is sending we
    // create a recvonly track and forward RTP to the matching far-side Peer.
    void create_receive_track(const std::string& mid, const std::string& kind,
                              MediaHandler handler) {
        auto tr = pc_->addTrack(description_for(mid, kind, rtc::Description::Direction::RecvOnly));
        tr->onMessage([this, mid, handler](rtc::message_variant data) {
            if (std::holds_alternative<rtc::binary>(data)) {
                const auto& bin = std::get<rtc::binary>(data);
                if (handler) handler(bin, 0);
            }
        });
        recv_tracks_[mid] = tr;
    }

    // Server -> browser leg. Forward far-side media by calling send() on this
    // track (libdatachannel hands the RTP packets through to the peer).
    std::shared_ptr<rtc::Track> create_forward_track(const std::string& mid,
                                                     const std::string& kind) {
        auto tr = pc_->addTrack(description_for(mid, kind, rtc::Description::Direction::SendOnly));
        fwd_tracks_[mid] = tr;
        return tr;
    }

    std::shared_ptr<rtc::Track> forward_track(const std::string& mid) const {
        auto it = fwd_tracks_.find(mid);
        return it != fwd_tracks_.end() ? it->second : nullptr;
    }

    void on_local_description(std::function<void(std::string sdp)> cb) {
        pc_->onLocalDescription([cb](rtc::Description desc) {
            if (cb) cb(std::string(desc));
        });
    }
    void on_local_candidate(std::function<void(std::string cand)> cb) {
        pc_->onLocalCandidate([cb](rtc::Candidate cand) {
            if (cb) cb(std::string(cand));
        });
    }

    // Apply the SDP/ICE from the Django signal relay.
    void set_remote_description(const std::string& sdp_or_candidate) {
        if (sdp_or_candidate.rfind("candidate:", 0) == 0) {
            pc_->addRemoteCandidate(rtc::Candidate(sdp_or_candidate));
            return;
        }
        pc_->setRemoteDescription(rtc::Description(sdp_or_candidate));
    }

    const std::string& id() const { return id_; }

private:
    static rtc::Description::Media description_for(const std::string& mid,
                                                    const std::string& kind,
                                                    rtc::Description::Direction dir) {
        // One m-line per kind; mid must be unique per leg.
        return rtc::Description::Media(kind == "audio" ? "audio" : "video", mid, dir);
    }

    std::string id_;
    std::shared_ptr<rtc::PeerConnection> pc_;
    std::map<std::string, std::shared_ptr<rtc::Track>> recv_tracks_;
    std::map<std::string, std::shared_ptr<rtc::Track>> fwd_tracks_;
};

}  // namespace tazagojo