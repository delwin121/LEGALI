// --- STEALTH MEMORY ---
let currentSessionId = sessionStorage.getItem('sessionId') || crypto.randomUUID();
sessionStorage.setItem('sessionId', currentSessionId);
let chatHistory = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');

    // Handle Enter Key & Button Click
    if (searchInput && searchButton) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleSearch(searchInput.value);
        });
        searchButton.addEventListener('click', () => {
            handleSearch(searchInput.value);
        });
    }

    // Handle "Try Asking" Chips
    const chips = document.querySelectorAll('.suggested-chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query) {
                if (searchInput) searchInput.value = query;
                handleSearch(query);
            }
        });
    });
});

async function handleSearch(query) {
    if (!query || !query.trim()) return;
    query = query.trim();

    // Grab DOM Elements
    const heroSection = document.getElementById('heroSection');
    const chipsContainer = document.getElementById('chipsContainer');
    const resultsSection = document.getElementById('resultsSection');
    const answerContent = document.getElementById('answerContent');
    const citationsWrapper = document.getElementById('citationsWrapper');
    const citationsContainer = document.getElementById('citationsContainer');

    // 1. SINGLE PAGE UI TRANSITION (No Redirect!)
    if (heroSection) heroSection.classList.add('hidden');
    if (chipsContainer) chipsContainer.classList.add('hidden');
    if (resultsSection) resultsSection.classList.remove('hidden');
    if (citationsWrapper) citationsWrapper.classList.add('hidden');

    answerContent.innerHTML = `
        <div class="animate-pulse flex space-x-4">
            <div class="flex-1 space-y-4 py-1">
                <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div class="space-y-2">
                    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                </div>
            </div>
        </div>`;

    // 2. Save User Query to Memory
    chatHistory.push({ "role": "user", "content": query });
    sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));

    try {
        // 3. Trigger Backend Stream
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, history: chatHistory, session_id: currentSessionId })
        });

        if (!response.ok) throw new Error("Server Error");

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullAiText = "";
        answerContent.innerHTML = ""; // Clear the loading pulse

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunkData = decoder.decode(value);
            const lines = chunkData.split('\n\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const dataObj = JSON.parse(line.substring(6));

                        // Stream the AI Text
                        if (dataObj.chunk) {
                            fullAiText += dataObj.chunk;
                            let formattedText = fullAiText.replace(/\[(Section\s+[A-Za-z0-9\.]+)\]/g, '<span class="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-bold text-primary ring-1 ring-inset ring-blue-700/10 mx-1">[$1]</span>');
                            formattedText = formattedText.replace(/\n/g, '<br>');
                            answerContent.innerHTML = formattedText;
                        }

                        // Display Citations
                        if (dataObj.citations && dataObj.citations.length > 0) {
                            citationsWrapper.classList.remove('hidden');
                            renderCitations(dataObj.citations, citationsContainer);
                        }
                    } catch (e) { } // Ignore partial chunk parsing errors
                }
            }
        }

        // 4. Save AI Answer to Memory
        chatHistory.push({ "role": "assistant", "content": fullAiText });
        sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));

    } catch (error) {
        console.error("Stream failed:", error);
        answerContent.innerHTML = `<span class="text-red-500">Connection Error. Please ensure your backend is running.</span>`;
    }
}

// Render Citation Cards neatly using Tailwind
function renderCitations(citations, container) {
    container.innerHTML = '';
    citations.forEach(cit => {
        container.innerHTML += `
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800 hover:border-primary transition-colors">
                <div class="mb-2 flex items-center justify-between">
                    <span class="rounded bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 ring-1 ring-inset ring-blue-700/10">${cit.act}</span>
                </div>
                <h4 class="font-bold text-gray-900 dark:text-white">Section ${cit.section}</h4>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">${cit.chapter}</p>
            </div>
        `;
    });
}