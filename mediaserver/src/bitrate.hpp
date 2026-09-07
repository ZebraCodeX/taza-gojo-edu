// BitrateController — adaptive video budget for low-bandwidth campuses.
//
// The mediaserver lives on the *good* network side of the call (e.g. a 4G/FTTH
// box at the school, or datacenter). The near-3G student usually has the weak
// uplink. We adapt the relay to that student by:
//
//   1. parsing RTCP Receiver Reports the student actually sends back, and
//   2. exponentially shrinking the video budget on loss, then slowly probing up.
//
// When the budget drops we stop forwarding higher simulcast layers and nudge the
// browser (via signaling) to request a lower bitrate / resolution.
//
// This header is deliberately dependency-free so it can be unit-tested anywhere.

#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <array>
#include <algorithm>
#include <chrono>

namespace tazagojo {

// --- RTCP parsing ----------------------------------------------------------

// Minimal, spec-conformant RTCP Receiver Report parser. Returns the worst
// fractional loss (0.0 .. 1.0) observed across any report block in the packet.
// RFC 3550: RR packet = [header][sender ssrc][report blocks]
//   header byte0..3: V=2, P, RC, PT=201, length
//   report block:   ssrc_40, frac_lost_8, cum_lost_24, ext_seq_32,
//                   jitter_32, lsr_32, dlsr_32
inline double rtcp_fractional_loss(const uint8_t* data, size_t len) {
    if (len < 8) return 0.0;
    double worst = 0.0;
    size_t offset = 0;
    while (offset + 4 <= len) {
        const uint8_t b0 = data[offset];
        const uint8_t b1 = data[offset + 1];
        const unsigned version = (b0 >> 6) & 0x03;
        const unsigned pt = b1;                      // payload type is the whole byte
        const unsigned rc = b0 & 0x1f;               // report count
        const uint16_t wc = (uint16_t(data[offset + 2]) << 8) | data[offset + 3];
        const size_t total = (size_t(wc) + 1) * 4;   // in bytes
        if (version != 2 || total == 0 || offset + total > len) return worst;
        if (pt == 201) {                             // Receiver Report
            // 4 (header) + 4 (sender ssrc)
            size_t blk = offset + 8;
            const size_t n = std::min<size_t>(rc, (total - 8) / 24);
            for (size_t i = 0; i < n; ++i, blk += 24) {
                const double frac = double(data[blk + 4]) / 256.0;   // frac_lost
                worst = std::max(worst, frac);
            }
        }
        offset += total;
    }
    return worst;
}

// --- Adaptive controller ----------------------------------------------------

class BitrateController {
public:
    struct Params {
        uint32_t min_bitrate_kbps = 30;     // ignore anything below (drop calls, don't stall)
        uint32_t max_bitrate_kbps = 1000;   // budget cap (video-from-teacher to student)
        uint32_t start_bitrate_kbps = 800;
        double loss_high = 0.10;            // losses above this shave the budget
        double loss_low  = 0.02;            // below this we probe back up
        double backoff = 0.5;               // multiplicative steps down
        double probe = 0.1;                 // additive steps up (kbps per healthy window)
        uint32_t window_ok_ms = 4000;       // healthy time to probe up
    };

    BitrateController() : BitrateController(Params{}) {}
    explicit BitrateController(Params p) : params_(p), current_(p.start_bitrate_kbps) {}

    uint32_t current_kbps() const { return current_; }

    // Feed one RTCP loss sample; returns true when the budget changed.
    bool observe_loss(double loss, std::chrono::steady_clock::duration since_last =
                          std::chrono::milliseconds(100)) {
        const auto now = std::chrono::steady_clock::now();
        healthy_since_ = loss <= params_.loss_low
                             ? std::max(healthy_since_, now - since_last)
                             : now;
        if (loss >= params_.loss_high) {
            // On a child's 2G link, better to give them *frame rate + audio*
            // than a pixelated slideshow.
            uint32_t next = static_cast<uint32_t>(current_ * (1.0 - params_.backoff));
            next = std::max(params_.min_bitrate_kbps, next);
            if (next < current_) {
                current_ = next;
                return true;
            }
        } else if (loss <= params_.loss_low &&
                   now - healthy_since_ >= std::chrono::milliseconds(params_.window_ok_ms)) {
            uint32_t next = current_ + params_.probe;
            if (next < params_.max_bitrate_kbps) {
                current_ = std::min(next, params_.max_bitrate_kbps);
                return true;
            }
        }
        return false;
    }

    // Which simulcast layer index fits the current budget (used in relay).
    // Ascending scan: the highest layer whose nominal upper bound is <= budget.
    int layer_for_budget(const std::array<uint32_t, 3>& layer_kbps_bounds) const {
        int layer = 0;
        for (size_t i = 0; i < layer_kbps_bounds.size(); ++i) {
            if (current_ >= layer_kbps_bounds[i]) layer = static_cast<int>(i);
            else break;
        }
        return layer;
    }

    Params& params() { return params_; }

private:
    Params params_;
    uint32_t current_;
    std::chrono::steady_clock::time_point healthy_since_ =
        std::chrono::steady_clock::now();
};

}  // namespace tazagojo