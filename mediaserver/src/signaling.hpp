// signaling.hpp — thin wrapper over libdatachannel's WebSocket client.
//
// The mediaserver joins a tutoring room the same way a browser does, tagged
// `device=mediaserver`, and simply relays SDP/ICE for both web peers while
// forwarding media between them. Speech reliability beats raw quality on 2G.

#pragma once

#include <functional>
#include <memory>
#include <string>
#include <atomic>
#include <iostream>

#include <rtc/rtc.hpp>
#include <nlohmann/json.hpp>

namespace tazagojo {

using Json = nlohmann::json;

class SignalingClient {
public:
    // url: ws(s)://host:port/ws/tutor/<id>/?device=mediaserver&token=...
    // on_message(json) is invoked for every signaling frame from the room.
    explicit SignalingClient(std::string url,
                             std::function<void(const Json&)> on_message,
                             std::function<void(bool connected)> on_state)
        : on_message_(std::move(on_message)), on_state_(std::move(on_state)) {
        ws_ = std::make_shared<rtc::WebSocket>();
        ws_->onOpen([this]() {
            state_ = true;
            if (on_state_) on_state_(true);
        });
        ws_->onClosed([this]() {
            state_ = false;
            if (on_state_) on_state_(false);
        });
        ws_->onError([this](std::string e) {
            std::cerr << "[signaling] error: " << e << std::endl;
            if (on_state_) on_state_(false);
        });
        ws_->onMessage([this](rtc::message_variant data) {
            if (std::holds_alternative<std::string>(data)) {
                auto text = std::get<std::string>(data);
                try {
                    auto j = Json::parse(text);
                    std::function<void(const Json&)> cb;
                    {
                        std::lock_guard<std::mutex> lock(mu_);
                        cb = on_message_;
                    }
                    if (cb) cb(j);
                } catch (const std::exception&) {
                    std::cerr << "[signaling] bad json" << std::endl;
                }
            }
        });
        ws_->open(url);
    }

    void send(const Json& j) {
        if (state_) ws_->send(j.dump());
    }

    // Allow rebinding the message handler after construction (main.cpp wires
    // the relay once both objects exist).
    void set_on_message(std::function<void(Json)> cb) {
        std::lock_guard<std::mutex> lock(mu_);
        on_message_ = std::move(cb);
    }

    bool connected() const { return state_; }

private:
    std::shared_ptr<rtc::WebSocket> ws_;
    std::function<void(const Json&)> on_message_;
    std::function<void(bool)> on_state_;
    std::mutex mu_;
    std::atomic<bool> state_{false};
};

}  // namespace tazagojo