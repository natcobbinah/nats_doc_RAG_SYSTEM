document.addEventListener("DOMContentLoaded", () => {
    const maxVisibleItems = 5;

    document.querySelectorAll("[data-card]").forEach((card) => {
        const list = card.querySelector("[data-card-list]");
        const items = Array.from(list.querySelectorAll(".card-list-item"));
        let startIndex = 0;

        const renderSlice = () => {
            items.forEach((item, index) => {
                const visible = index >= startIndex && index < startIndex + maxVisibleItems;
                item.hidden = !visible;
            });
        };

        card.querySelector("[data-card-prev]")?.addEventListener("click", () => {
            if (items.length <= maxVisibleItems) {
                return;
            }

            startIndex = Math.max(0, startIndex - maxVisibleItems);
            renderSlice();
        });

        card.querySelector("[data-card-next]")?.addEventListener("click", () => {
            if (items.length <= maxVisibleItems) {
                return;
            }

            if (startIndex + maxVisibleItems < items.length) {
                startIndex += maxVisibleItems;
            } else {
                startIndex = 0;
            }
            renderSlice();
        });

        renderSlice();
    });

    const voiceButtons = document.querySelectorAll("[data-voice-search]");
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    voiceButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const form = button.closest("form");
            const input = form?.querySelector("input[name='q']");

            if (!SpeechRecognition || !input || !form) {
                button.textContent = "Unavailable";
                return;
            }

            const recognition = new SpeechRecognition();
            recognition.lang = "en-US";
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            button.textContent = "Listening";

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript.trim();
                input.value = transcript;
                form.submit();
            };

            recognition.onerror = () => {
                button.textContent = "Voice";
            };

            recognition.onend = () => {
                button.textContent = "Voice";
            };

            recognition.start();
        });
    });
});