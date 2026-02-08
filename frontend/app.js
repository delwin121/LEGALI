document.addEventListener('DOMContentLoaded', () => {
    // 1. Unified Search Handler
    handleSearchInput('searchInput', 'searchButton');
    handleSearchInput('resultsSearchInput', 'resultsSearchButton'); // Pass null if button doesn't exist, or add ID

    // 2. Suggested Chips Handler
    const chips = document.querySelectorAll('.suggested-chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query) {
                window.location.href = `search.html?q=${encodeURIComponent(query)}`;
            }
        });
    });

    // 3. Search Page Logic
    if (window.location.pathname.includes('search.html')) {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');

        // Initial UI State: Loading
        const answerContent = document.getElementById('answerContent');
        if (answerContent && query) {
            // Clear existing content (the placeholder text)
            answerContent.innerHTML = `
                <div class="animate-pulse flex flex-col gap-4">
                    <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/6"></div>
                </div>
            `;

            // Set input value
            const resultsInput = document.getElementById('resultsSearchInput');
            if (resultsInput) resultsInput.value = decodeURIComponent(query);

            // Fetch Result
            fetchAnswer(decodeURIComponent(query));
        }

        // View Sources Scroll
        const viewSourcesBtn = document.getElementById('viewSources');
        if (viewSourcesBtn) {
            viewSourcesBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const citations = document.getElementById('citationsSection');
                if (citations) citations.scrollIntoView({ behavior: 'smooth' });
            });
        }

        // Copy Button
        const copyBtn = document.getElementById('copyButton');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const text = document.querySelector('.prose')?.innerText;
                if (text) {
                    navigator.clipboard.writeText(text).then(() => {
                        // Optional: Show tooltip or change icon temporarily
                        const icon = copyBtn.querySelector('span');
                        icon.textContent = 'check';
                        setTimeout(() => icon.textContent = 'content_copy', 2000);
                    });
                }
            });
        }
    }
});

function handleSearchInput(inputId, buttonId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);

    if (input) {
        // Enter key support
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = input.value.trim();
                if (query) {
                    window.location.href = `search.html?q=${encodeURIComponent(query)}`;
                }
            }
        });
    }

    if (button) {
        // Click support
        button.addEventListener('click', () => {
            const query = input?.value.trim();
            if (query) {
                window.location.href = `search.html?q=${encodeURIComponent(query)}`;
            }
        });
    }
}

async function fetchAnswer(query) {
    const answerContainer = document.getElementById('answerContent');
    const citationsContainer = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-3');
    const statusText = document.querySelector('p.text-xs.font-medium.leading-normal');

    try {
        const response = await fetch('http://localhost:8000/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            // If we have a JSON error body, use it
            if (data && (data.detail || data.error)) {
                // FastAPI standard error is in 'detail', our custom logic might be in 'error' or 'detail.reason'
                if (typeof data.detail === 'object') {
                    throw new Error(data.detail.reason || data.detail.error || "Unknown Error");
                }
                throw new Error(data.detail || data.error || response.statusText);
            }
            throw new Error(`API Error: ${response.statusText}`);
        }

        // Handle API-returned errors (e.g., validation failure defined in successful 200 OK json? No, we switched to 4xx/5xx)
        if (data.error) {
            throw new Error(data.reason || data.error);
        }

        // Update Answer
        if (answerContainer) {
            let formattedAnswer = data.answer.replace(/\n/g, '<br>');
            formattedAnswer = formattedAnswer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

            answerContainer.innerHTML = `
                <h1 class="text-2xl md:text-3xl font-bold tracking-tight text-gray-900 dark:text-white mb-2">
                    Result for "${query}"
                </h1>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-6 font-medium">
                    Detailed explanation based on the Bharatiya Nagarik Suraksha Sanhita.
                </p>
                <div class="prose prose-slate dark:prose-invert max-w-none text-base leading-7 text-gray-700 dark:text-gray-300">
                    <p class="mb-4">
                        ${formattedAnswer}
                    </p>
                </div>
            `;
        }

        // Update Verification Status
        if (statusText) {
            statusText.textContent = "AI Generated • Verified Citations";
        }

        // Update Citations
        if (citationsContainer && data.citations) {
            citationsContainer.innerHTML = '';

            if (data.citations.length === 0) {
                citationsContainer.innerHTML = '<p class="text-gray-500">No specific citations found.</p>';
            } else {
                data.citations.forEach(citation => {
                    const card = document.createElement('div');
                    card.className = "group relative flex flex-col justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1a222d] p-4 transition-all hover:border-primary hover:shadow-md cursor-pointer";

                    // Construct a link to the act page (placeholder logic for now)
                    const actLink = `acts.html?act=${encodeURIComponent(citation.act)}&section=${encodeURIComponent(citation.section)}`;

                    card.innerHTML = `
                        <div class="mb-3">
                            <div class="flex items-start justify-between mb-2">
                                <span class="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-900/30 px-2 py-1 text-xs font-bold text-primary ring-1 ring-inset ring-blue-700/10">
                                    ${citation.act}
                                </span>
                                <a href="${actLink}" class="text-gray-400 group-hover:text-primary transition-colors" title="Open Act">
                                    <span class="material-symbols-outlined" style="font-size: 20px;">open_in_new</span>
                                </a>
                            </div>
                            <h4 class="font-bold text-gray-900 dark:text-white text-lg group-hover:text-primary transition-colors">
                                Section ${citation.section}
                            </h4>
                            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">${citation.chapter}</p>
                        </div>
                    `;
                    citationsContainer.appendChild(card);
                });
            }
        }

        // Update Suggested Questions
        const suggestedContainer = document.querySelector('section[aria-label="Related Questions"] > div');
        if (suggestedContainer && data.suggested_questions && data.suggested_questions.length > 0) {
            suggestedContainer.innerHTML = ''; // Clear existing chips

            data.suggested_questions.forEach(q => {
                const btn = document.createElement('button');
                btn.className = "suggested-chip group flex h-9 items-center justify-center gap-2 rounded-lg bg-white dark:bg-[#1a222d] border border-gray-200 dark:border-gray-700 px-4 transition-all hover:border-primary/50 hover:bg-primary/5 active:bg-primary/10";
                btn.setAttribute('data-query', q);

                btn.innerHTML = `
                    <span class="material-symbols-outlined text-primary text-lg">search</span>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-primary">${q}</span>
                `;

                // Add click listener purely for this new element
                btn.addEventListener('click', () => {
                    const query = btn.getAttribute('data-query');
                    if (query) {
                        window.location.href = `search.html?q=${encodeURIComponent(query)}`;
                    }
                });

                suggestedContainer.appendChild(btn);
            });
        }

    } catch (error) {
        console.error('Error fetching answer:', error);
        if (answerContainer) {
            answerContainer.innerHTML = `
                <div class="p-4 bg-red-50 text-red-700 rounded-lg">
                    <p class="font-bold">Failed to load answer</p>
                    <p>${error.message || 'Please check your connection or try again later.'}</p>
                </div>
            `;
        }
    }
}
