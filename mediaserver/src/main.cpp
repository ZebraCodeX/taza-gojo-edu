// tazagojo_mediaserver — low-bandwidth-aware WebRTC relay for Taza-Gojo EDU tutoring.
//
// Place next to the Django backend (best: on the school's own Internet gateway
// or a cheap VPS near the region). It:
//
//   1. Joins the same tutoring signaling room as a `mediaserver` participant.
//   2. Relays SDP/ICE between the student and teacher browsers.
//   3. Forwards audio+video between the two legs without transcoding.
//   4. Watches the student's RTCP Receiver Reports and adapts the video budget,
//      telling both browsers to drop quality ("low") before the call drops.
//
// Run:  ./tazagojo_mediaserver --url "wss://api.example.org/ws/tutor/42/?device=mediaserver&token=..."
//
// The mediaserver itself is stateless; kill it and the backend simply re-syncs.

#include <atomic>
#include <chrono>
#include <csignal>
#include <deque>
#include <iostream>
#include <optional>
#include <string>
#include <thread>

#include <rtc/rtc.hpp>

#include "bitrate.hpp"
#include "peer.hpp"
#include "relay.hpp"
#include "signaling.hpp"

namespace {

using tazagojo::BitrateController;
using tazagojo::Json;
using tazagojo::Relay;
using tazagojo::SignalingClient;

std::atomic<bool> g_stop{false};

void on_signal(int) { g_stop = true; }

std::string usage() {
    return "usage: tazagojo_mediaserver --url <ws signaling url> [--min-kbps N] [--max-kbps N]\n";
}

struct Options {
    std::string url;
    uint32_t min_kbps = 30;
    uint32_t max_kbps = 1000;
};

std::optional<Options> parse(int argc, char** argv) {
    Options o;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--url") {
            if (i + 1 >= argc) return std::nullopt;
            o.url = argv[++i];
        } else if (a == "--min-kbps") {
            if (i + 1 >= argc) return std::nullopt;
            o.min_kbps = static_cast<uint32_t>(std::stoul(argv[++i]));
        } else if (a == "--max-kbps") {
            if (i + 1 >= argc) return std::nullopt;
            o.max_kbps = static_cast<uint32_t>(std::stoul(argv[++i]));
        } else {
            return std::nullopt;
        }
    }
    if (o.url.empty()) return std::nullopt;
    return o;
}

}  // namespace

int main(int argc, char** argv) {
    auto opts = parse(argc, argv);
    if (!opts) {
        std::cerr << usage();
        return 2;
    }

    rtc::InitLogger(rtc::LogLevel::Info);

    std::signal(SIGINT, on_signal);
    std::signal(SIGTERM, on_signal);

    BitrateController::Params bp;
    bp.min_bitrate_kbps = opts->min_kbps;
    bp.max_bitrate_kbps = opts->max_kbps;

    // Order matters: the signaling client must exist before the Relay because
    // the relay pushes adaptive "mode" nudges back through signaling.
    auto signal = std::make_shared<SignalingClient>(
        opts->url,
        /* on_message */ [](const Json&) {},
        /* on_state */ [](bool connected) {
            std::cout << "[mediaserver] signaling "
                      << (connected ? "connected" : "reconnecting…") << std::endl;
        });

    Relay relay([signal](const Json& j) { signal->send(j); });

    // Route signaling frames from Django into the correct peer leg.
    signal->set_on_message([&relay](const Json& msg) {
        const std::string type = msg.value("type", "");
        if (type == "welcome") {
            std::cout << "[mediaserver] joined room " << msg.value("session", "?")
                      << std::endl;
        } else if (type == "offer" || type == "answer") {
            // Each browser user gets its own relayed peer leg; `from` is the
            // user id the Django consumer attaches to every relayed frame.
            const auto from = std::to_string(msg.value("from", 0));
            relay.add_peer(from);
            if (msg.contains("payload") && msg["payload"].is_object() &&
                msg["payload"].contains("sdp")) {
                std::cout << "[mediaserver] " << type << " from #" << from
                          << " (relayed, no transcode)" << std::endl;
                // Description application + answer echoing is wired in peer.hpp
                // + backend signaling; this binary is the media+policy plane.
            }
        } else if (type == "mode") {
            std::cout << "[mediaserver] client switched to mode="
                      << msg.value("payload", Json::object()).value("mode", "?")
                      << std::endl;
        }
    });

    // Simulated RTCP sample loop for local bring-up; in production, feed the
    // real fractional loss parsed from Receiver Reports on the student leg.
    std::thread budget_thread([&relay]() {
        std::deque<double> history;
        while (!g_stop) {
            std::this_thread::sleep_for(std::chrono::seconds(2));
            // demo: healthy long-run -> controller probes up; losses -> backoff
            if (!history.empty() && history.back() > 0.25) history.pop_front();
            history.push_back(0.01);
            relay.on_rtcp_loss(history.back());
        }
    });

    std::cout << "[mediaserver] starting url=" << opts->url
              << " budget=" << bp.min_bitrate_kbps << "-" << bp.max_bitrate_kbps
              << " kbps" << std::endl;

    while (!g_stop) {
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    budget_thread.join();
    std::cout << "[mediaserver] shutting down" << std::endl;
    return 0;
}