(function () {
    "use strict";

    var ACTIVE_STATUSES = ["pending", "processing"];
    var POLL_INTERVAL_MS = 3000;

    function statusLabel(status) {
        var labels = {
            pending: "В очереди",
            processing: "Обрабатывается",
            done: "Готово",
            failed: "Ошибка",
        };
        return labels[status] || status;
    }

    function updateRow(row, job) {
        var statusEl = row.querySelector("[data-job-status]");
        statusEl.className = "badge badge--" + job.status;
        statusEl.textContent = statusLabel(job.status);

        var sourceEl = row.querySelector("[data-job-source]");
        if (job.detected_source_format) {
            sourceEl.textContent = job.detected_source_format;
        }

        var resultEl = row.querySelector("[data-job-result]");
        if (job.status === "done" && job.result_file) {
            resultEl.innerHTML = '<a class="button" href="' + job.result_file + '">Скачать</a>';
        } else if (job.status === "failed") {
            resultEl.innerHTML = '<span class="help-text">' + (job.error_message || "") + "</span>";
        }
    }

    function poll() {
        var rows = document.querySelectorAll("[data-job-row]");
        var pending = [];

        rows.forEach(function (row) {
            var statusEl = row.querySelector("[data-job-status]");
            var isActive = ACTIVE_STATUSES.some(function (status) {
                return statusEl.classList.contains("badge--" + status);
            });
            if (isActive) {
                pending.push(row);
            }
        });

        if (pending.length === 0) {
            return;
        }

        pending.forEach(function (row) {
            fetch(row.getAttribute("data-job-url"), { credentials: "same-origin" })
                .then(function (response) { return response.json(); })
                .then(function (job) { updateRow(row, job); })
                .catch(function () {});
        });

        setTimeout(poll, POLL_INTERVAL_MS);
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(poll, POLL_INTERVAL_MS);
    });
})();
