(function (global) {
    "use strict";

    function getCookie(name) {
        var match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
        return match ? decodeURIComponent(match[2]) : null;
    }

    function base64urlToBuffer(value) {
        var padded = value.replace(/-/g, "+").replace(/_/g, "/");
        var padding = "=".repeat((4 - (padded.length % 4)) % 4);
        var binary = atob(padded + padding);
        var buffer = new Uint8Array(binary.length);
        for (var i = 0; i < binary.length; i++) {
            buffer[i] = binary.charCodeAt(i);
        }
        return buffer.buffer;
    }

    function bufferToBase64url(buffer) {
        var bytes = new Uint8Array(buffer);
        var binary = "";
        for (var i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    }

    function postJson(url, body) {
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: body ? JSON.stringify(body) : "{}",
        }).then(function (response) {
            if (!response.ok) {
                return response.json().then(function (data) {
                    throw new Error(data.error || "Request failed");
                });
            }
            return response.json();
        });
    }

    function decodeOptions(options, isRegistration) {
        options.challenge = base64urlToBuffer(options.challenge);
        if (isRegistration && options.user) {
            options.user.id = base64urlToBuffer(options.user.id);
        }
        var listKey = isRegistration ? "excludeCredentials" : "allowCredentials";
        if (Array.isArray(options[listKey])) {
            options[listKey] = options[listKey].map(function (cred) {
                return Object.assign({}, cred, { id: base64urlToBuffer(cred.id) });
            });
        }
        return options;
    }

    function registerPasskey(deviceName) {
        return postJson("/accounts/webauthn/register/begin/").then(function (options) {
            return navigator.credentials.create({
                publicKey: decodeOptions(options, true),
            });
        }).then(function (credential) {
            var payload = credentialToJson(credential);
            var url = "/accounts/webauthn/register/complete/?device_name=" + encodeURIComponent(deviceName || "");
            return postJson(url, payload);
        });
    }

    function loginWithPasskey() {
        return postJson("/accounts/webauthn/login/begin/").then(function (options) {
            return navigator.credentials.get({
                publicKey: decodeOptions(options, false),
            });
        }).then(function (credential) {
            var payload = credentialToJson(credential);
            return postJson("/accounts/webauthn/login/complete/", payload);
        }).then(function (result) {
            window.location.href = result.redirect || "/";
            return result;
        });
    }

    function credentialToJson(credential) {
        var response = credential.response;
        var json = {
            id: credential.id,
            rawId: bufferToBase64url(credential.rawId),
            type: credential.type,
            response: {
                clientDataJSON: bufferToBase64url(response.clientDataJSON),
            },
        };
        if (response.attestationObject) {
            json.response.attestationObject = bufferToBase64url(response.attestationObject);
        }
        if (response.authenticatorData) {
            json.response.authenticatorData = bufferToBase64url(response.authenticatorData);
        }
        if (response.signature) {
            json.response.signature = bufferToBase64url(response.signature);
        }
        if (response.userHandle) {
            json.response.userHandle = bufferToBase64url(response.userHandle);
        }
        return json;
    }

    global.SnpWebAuthn = {
        registerPasskey: registerPasskey,
        loginWithPasskey: loginWithPasskey,
    };
})(window);
