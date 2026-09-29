/* =========================================================
   BISATHI
   FRONTEND LOGIC
   ========================================================= */


/* =========================================================
   CONFIGURATION
   ========================================================= */

const API_BASE_URL = "http://127.0.0.1:8000";

const API_ASK_URL = `${API_BASE_URL}/api/ask`;
const API_SEARCH_URL = `${API_BASE_URL}/api/search-standard`;
const API_CERTIFICATION_URL = `${API_BASE_URL}/api/certification-guide`;
const API_DOCUMENT_URL = `${API_BASE_URL}/api/document-checklist`;
const API_ISI_URL = `${API_BASE_URL}/api/verify-isi`;


/* =========================================================
   DEBUG
   ========================================================= */

console.log("BISathi API Base URL:", API_BASE_URL);
console.log("BISathi Search API:", API_SEARCH_URL);


/* =========================================================
   ELEMENTS
   ========================================================= */

const modal = document.getElementById("assistantModal");
const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");

let selectedUserType = "consumer";


/* =========================================================
   OPEN ASSISTANT
   ========================================================= */

function openAssistant(initialQuestion = "") {
    if (!modal) {
        return;
    }

    modal.classList.add("show");
    document.body.classList.add("modal-open");

    if (userInput) {
        if (initialQuestion) {
            userInput.value = initialQuestion;
        }

        setTimeout(function () {
            userInput.focus();
        }, 150);
    }
}


/* =========================================================
   CLOSE ASSISTANT
   ========================================================= */

function closeAssistant() {
    if (!modal) {
        return;
    }

    modal.classList.remove("show");
    document.body.classList.remove("modal-open");
}


/* =========================================================
   OUTSIDE CLICK
   ========================================================= */

if (modal) {
    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeAssistant();
        }
    });
}


/* =========================================================
   ESC KEY
   ========================================================= */

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        closeAssistant();
    }
});


/* =========================================================
   MOBILE NAVIGATION
   ========================================================= */

function toggleMobileNav() {
    const mobileNav = document.getElementById("mobileNav");

    if (!mobileNav) {
        return;
    }

    mobileNav.classList.toggle("show");
}


function closeMobileNav() {
    const mobileNav = document.getElementById("mobileNav");

    if (!mobileNav) {
        return;
    }

    mobileNav.classList.remove("show");
}


/* =========================================================
   USER TYPE
   ========================================================= */

function selectUserType(type) {
    selectedUserType = type;

    const consumerBtn = document.getElementById("consumerBtn");
    const industryBtn = document.getElementById("industryBtn");

    if (consumerBtn) {
        consumerBtn.classList.remove("active");
    }

    if (industryBtn) {
        industryBtn.classList.remove("active");
    }

    if (type === "consumer") {
        if (consumerBtn) {
            consumerBtn.classList.add("active");
        }
    } else {
        if (industryBtn) {
            industryBtn.classList.add("active");
        }
    }
}


/* =========================================================
   SEND CHAT MESSAGE
   ========================================================= */

async function sendMessage() {
    if (!userInput) {
        return;
    }

    const message = userInput.value.trim();

    if (!message) {
        return;
    }

    addUserMessage(message);
    userInput.value = "";
    showThinking();

    try {
        console.log(
            "Sending Ask AI request to:",
            API_ASK_URL
        );

        const response = await fetch(API_ASK_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: message,
                user_type: selectedUserType
            })
        });

        if (!response.ok) {
            throw new Error(
                "Server returned HTTP " + response.status
            );
        }

        const data = await response.json();

        removeThinking();

        if (data.success) {
            addAIMessage(
                data.answer,
                data.official_sources ||
                data.sources ||
                []
            );
        } else {
            addAIMessage(
                data.answer ||
                "Sorry, I could not process your question right now.",
                data.official_sources ||
                data.sources ||
                []
            );
        }

    } catch (error) {
        console.error("BISathi API Error:", error);

        removeThinking();

        addAIMessage(
            "I could not connect to the BISathi AI service. Please try again."
        );
    }
}


/* =========================================================
   ENTER KEY
   ========================================================= */

function handleEnter(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
}


/* =========================================================
   QUICK QUESTION
   ========================================================= */

function askQuestion(question) {
    openAssistant();

    if (userInput) {
        userInput.value = question;

        setTimeout(function () {
            sendMessage();
        }, 100);
    }
}


/* =========================================================
   ADD USER MESSAGE
   ========================================================= */

function addUserMessage(message) {
    if (!chatArea) {
        return;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "message user-message";

    const messageBox = document.createElement("div");
    messageBox.className = "message-box";
    messageBox.textContent = message;

    wrapper.appendChild(messageBox);
    chatArea.appendChild(wrapper);

    scrollChat();
}


/* =========================================================
   MARKDOWN FORMATTER
   ========================================================= */

function formatMarkdown(message) {
    if (!message) {
        return "";
    }

    const escaped = escapeHTML(message);
    const lines = escaped.split(/\r?\n/);
    const output = [];

    let insideList = false;

    function closeList() {
        if (insideList) {
            output.push("</ul>");
            insideList = false;
        }
    }

    lines.forEach(function (rawLine) {
        const line = rawLine.trim();

        if (!line) {
            closeList();
            return;
        }

        if (/^---+$/.test(line)) {
            closeList();
            return;
        }

        if (/^###\s+/.test(line)) {
            closeList();

            const heading = line.replace(
                /^###\s+/,
                ""
            );

            output.push(`<h4>${heading}</h4>`);
            return;
        }

        if (/^##\s+/.test(line)) {
            closeList();

            const heading = line.replace(
                /^##\s+/,
                ""
            );

            output.push(`<h3>${heading}</h3>`);
            return;
        }

        if (/^[-*]\s+/.test(line)) {
            const item = line
                .replace(/^[-*]\s+/, "")
                .trim();

            if (!item) {
                return;
            }

            if (!insideList) {
                output.push("<ul>");
                insideList = true;
            }

            output.push(`<li>${item}</li>`);
            return;
        }

        if (/^\d+[.)]\s+/.test(line)) {
            const item = line
                .replace(/^\d+[.)]\s+/, "")
                .trim();

            if (!item) {
                return;
            }

            if (!insideList) {
                output.push("<ul>");
                insideList = true;
            }

            output.push(`<li>${item}</li>`);
            return;
        }

        closeList();

        output.push(`<p>${line}</p>`);
    });

    closeList();

    let formatted = output.join("");

    formatted = formatted.replace(
        /\*\*(.*?)\*\*/g,
        "<strong>$1</strong>"
    );

    formatted = formatted.replace(
        /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    formatted = formatted.replace(
        /\\([*_])/g,
        "$1"
    );

    return formatted.trim();
}


/* =========================================================
   OFFICIAL BIS SOURCES
   ========================================================= */

function formatOfficialSources(sources) {
    if (
        !sources ||
        !Array.isArray(sources) ||
        sources.length === 0
    ) {
        return "";
    }

    let html = `
        <div class="official-sources">
            <h4>Official BIS Sources</h4>
            <div class="official-source-list">
    `;

    sources.forEach(function (source) {
        if (!source || !source.url) {
            return;
        }

        const title =
            source.title ||
            "Official BIS Source";

        html += `
            <a
                href="${escapeHTML(source.url)}"
                target="_blank"
                rel="noopener noreferrer"
                class="official-source-link"
            >
                <span class="source-icon">↗</span>
                <span>${escapeHTML(title)}</span>
            </a>
        `;
    });

    html += `
            </div>
        </div>
    `;

    return html;
}


/* =========================================================
   ADD AI MESSAGE
   ========================================================= */

function addAIMessage(message, sources = []) {
    if (!chatArea) {
        return;
    }

    const wrapper = document.createElement("div");

    wrapper.className = "message ai-message";

    wrapper.innerHTML = `
        <div class="small-avatar"></div>
        <div class="message-box"></div>
    `;

    const messageBox =
        wrapper.querySelector(".message-box");

    if (messageBox) {
        messageBox.innerHTML =
            formatMarkdown(message) +
            formatOfficialSources(sources);
    }

    chatArea.appendChild(wrapper);

    scrollChat();
}


/* =========================================================
   THINKING
   ========================================================= */

function showThinking() {
    if (!chatArea) {
        return;
    }

    removeThinking();

    const wrapper = document.createElement("div");

    wrapper.id = "thinking";
    wrapper.className =
        "message ai-message ai-response";

    wrapper.innerHTML = `
        <div class="small-avatar"></div>

        <div class="message-box loading-message">
            <span class="loading-dot"></span>
            <span>BISathi is thinking...</span>
        </div>
    `;

    chatArea.appendChild(wrapper);

    scrollChat();
}


/* =========================================================
   REMOVE THINKING
   ========================================================= */

function removeThinking() {
    const thinking =
        document.getElementById("thinking");

    if (thinking) {
        thinking.remove();
    }
}


/* =========================================================
   SCROLL CHAT
   ========================================================= */

function scrollChat() {
    if (!chatArea) {
        return;
    }

    chatArea.scrollTop =
        chatArea.scrollHeight;
}


/* =========================================================
   SCROLL TO SECTION
   ========================================================= */

function scrollToSection(id) {
    const section =
        document.getElementById(id);

    if (!section) {
        return;
    }

    closeMobileNav();

    section.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/* =========================================================
   HTML SECURITY
   ========================================================= */

function escapeHTML(text) {
    const div =
        document.createElement("div");

    div.textContent = String(text);

    return div.innerHTML;
}


/* =========================================================
   BIS STANDARD / PRODUCT SEARCH
   ========================================================= */

async function searchProduct() {
    const input =
        document.getElementById(
            "productSearchInput"
        );

    const result =
        document.getElementById(
            "standardsSearchResult"
        );

    if (!input || !result) {
        return;
    }

    const product =
        input.value.trim();

    if (!product) {
        result.innerHTML = `
            <div class="search-result-card">
                <p>
                    Please enter a product name to search.
                </p>
            </div>
        `;

        return;
    }

    let guidanceLabel =
        "Consumer Guidance";

    if (
        selectedUserType === "industry" ||
        selectedUserType === "manufacturer"
    ) {
        guidanceLabel =
            "Industry / Manufacturer Guidance";
    }

    result.innerHTML = `
        <div class="search-result-card">
            <div class="loading-message">
                <span class="loading-dot"></span>

                <span>
                    Searching official BIS information for
                    <strong>${escapeHTML(product)}</strong>
                </span>
            </div>
        </div>
    `;

    try {
        console.log(
            "Sending Standards Search request to:",
            API_SEARCH_URL
        );

        const response =
            await fetch(
                API_SEARCH_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        product: product,
                        user_type:
                            selectedUserType
                    })
                }
            );

        if (!response.ok) {
            throw new Error(
                "Server returned HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        console.log(
            "Standards Search Response:",
            data
        );

        if (!data.success) {
            result.innerHTML = `
                <div class="search-result-card">
                    <h3>
                        Unable to find product information
                    </h3>

                    <p>
                        ${escapeHTML(
                            data.answer ||
                            "BISathi could not process this product."
                        )}
                    </p>

                    ${formatOfficialSources(
                        data.official_sources ||
                        data.sources ||
                        []
                    )}
                </div>
            `;

            return;
        }


        /* =================================================
           SOURCE LABEL
           ================================================= */

        let sourceLabel =
            "BISathi AI";

        if (
            data.source ===
            "official_bis_live_search"
        ) {
            sourceLabel =
                "Official BIS Live Search";
        } else if (
            data.source ===
            "local_knowledge_base"
        ) {
            sourceLabel =
                "BISathi Product Knowledge Base";
        }


        /* =================================================
           MATCHED PRODUCT
           ================================================= */

        const matchedProduct =
            data.matched_product ||
            data.product ||
            product;


        /* =================================================
           TOTAL RECORDS
           ================================================= */

        const totalRecords =
            Number.isFinite(
                Number(data.total_records)
            )
                ? Number(data.total_records)
                : (
                    Array.isArray(
                        data.standards
                    )
                        ? data.standards.length
                        : 0
                );


        /* =================================================
           LIVE BIS BADGE
           ================================================= */

        let liveBadge = "";

        if (
            data.source ===
            "official_bis_live_search"
        ) {
            liveBadge = `
                <div class="live-bis-badge">
                    <span class="live-bis-dot"></span>
                    Live Official BIS Data
                </div>
            `;
        }


        /* =================================================
           FORMAT ANSWER
           ================================================= */

        const formatted =
            formatMarkdown(
                data.answer || ""
            );


        /* =================================================
           BUILD RESULT
           ================================================= */

        result.innerHTML = `
            <div class="search-result-card">

                <div class="search-result-header">

                    <div>

                        <h3>
                            ${escapeHTML(
                                matchedProduct
                            )}
                        </h3>

                        <div class="search-result-meta">

                            <span class="search-source">
                                ${escapeHTML(
                                    sourceLabel
                                )}
                            </span>

                            <span class="search-guidance-type">
                                ${escapeHTML(
                                    guidanceLabel
                                )}
                            </span>

                        </div>

                    </div>

                    ${liveBadge}

                </div>


                ${
                    totalRecords > 0
                        ? `
                            <div class="standards-count">

                                ${totalRecords}
                                BIS standard record${
                                    totalRecords === 1
                                        ? ""
                                        : "s"
                                }
                                found

                            </div>
                        `
                        : ""
                }


                <div class="search-ai-answer">
                    ${formatted}
                </div>


                ${formatOfficialSources(
                    data.official_sources ||
                    data.sources ||
                    []
                )}

            </div>
        `;

    } catch (error) {

        console.error(
            "BIS Standard Search Error:",
            error
        );

        result.innerHTML = `
            <div class="search-result-card error-box">

                <h3>
                    Unable to search right now
                </h3>

                <p>
                    BISathi could not connect to the local backend.
                    Please make sure FastAPI is running on
                    http://127.0.0.1:8000
                </p>

            </div>
        `;
    }
}


/* =========================================================
   CERTIFICATION GUIDANCE
   ========================================================= */

async function getCertificationGuidance() {

    const input =
        document.getElementById(
            "certificationProductInput"
        );

    const result =
        document.getElementById(
            "certificationResult"
        );

    if (!input || !result) {
        return;
    }

    const product =
        input.value.trim();

    if (!product) {

        result.innerHTML = `
            <div class="search-result-card">
                <p>
                    Please enter a product name.
                </p>
            </div>
        `;

        return;
    }

    result.innerHTML = `
        <div class="search-result-card">

            <div class="loading-message">

                <span class="loading-dot"></span>

                <span>
                    BISathi is preparing certification guidance...
                </span>

            </div>

        </div>
    `;

    try {

        console.log(
            "Sending Certification request to:",
            API_CERTIFICATION_URL
        );

        const response =
            await fetch(
                API_CERTIFICATION_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        product: product,
                        user_type:
                            "manufacturer"
                    })
                }
            );

        if (!response.ok) {
            throw new Error(
                "Server returned HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        if (!data.success) {

            result.innerHTML = `
                <div class="search-result-card error-box">

                    <p>
                        ${escapeHTML(
                            data.answer ||
                            "BISathi could not prepare the guidance."
                        )}
                    </p>

                    ${formatOfficialSources(
                        data.official_sources ||
                        data.sources ||
                        []
                    )}

                </div>
            `;

            return;
        }

        const formatted =
            formatMarkdown(
                data.answer || ""
            );

        result.innerHTML = `
            <div class="certification-result-card">

                ${formatted}

                ${formatOfficialSources(
                    data.official_sources ||
                    data.sources ||
                    []
                )}

            </div>
        `;

    } catch (error) {

        console.error(
            "Certification Guidance Error:",
            error
        );

        result.innerHTML = `
            <div class="search-result-card error-box">

                <h3>
                    Unable to load guidance
                </h3>

                <p>
                    BISathi could not connect to the local backend.
                </p>

            </div>
        `;
    }
}


/* =========================================================
   DOCUMENT CHECKLIST
   ========================================================= */

async function getDocumentChecklist() {

    const input =
        document.getElementById(
            "documentChecklistInput"
        );

    const result =
        document.getElementById(
            "documentChecklistResult"
        );

    if (!input || !result) {
        return;
    }

    const product =
        input.value.trim();

    if (!product) {

        result.innerHTML = `
            <div class="search-result-card">

                <p>
                    Please enter a product name.
                </p>

            </div>
        `;

        return;
    }

    result.innerHTML = `
        <div class="search-result-card">

            <div class="loading-message">

                <span class="loading-dot"></span>

                <span>
                    BISathi is preparing your document checklist...
                </span>

            </div>

        </div>
    `;

    try {

        console.log(
            "Sending Document Checklist request to:",
            API_DOCUMENT_URL
        );

        const response =
            await fetch(
                API_DOCUMENT_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        product: product,
                        user_type:
                            "manufacturer"
                    })
                }
            );

        if (!response.ok) {
            throw new Error(
                "Server returned HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        if (!data.success) {

            result.innerHTML = `
                <div class="search-result-card error-box">

                    <p>
                        ${escapeHTML(
                            data.answer ||
                            "BISathi could not prepare the checklist."
                        )}
                    </p>

                    ${formatOfficialSources(
                        data.official_sources ||
                        data.sources ||
                        []
                    )}

                </div>
            `;

            return;
        }

        const formatted =
            formatMarkdown(
                data.answer || ""
            );

        result.innerHTML = `
            <div class="certification-result-card">

                ${formatted}

                ${formatOfficialSources(
                    data.official_sources ||
                    data.sources ||
                    []
                )}

            </div>
        `;

    } catch (error) {

        console.error(
            "Document Checklist Error:",
            error
        );

        result.innerHTML = `
            <div class="search-result-card error-box">

                <h3>
                    Unable to load checklist
                </h3>

                <p>
                    BISathi could not connect to the local backend.
                </p>

            </div>
        `;
    }
}


/* =========================================================
   ISI MARK VERIFICATION
   ========================================================= */

async function verifyISI() {

    const input =
        document.getElementById(
            "isiVerificationInput"
        );

    const result =
        document.getElementById(
            "isiVerificationResult"
        );

    if (!input || !result) {
        return;
    }

    const question =
        input.value.trim();

    if (!question) {

        result.innerHTML = `
            <div class="search-result-card">

                <p>
                    Please enter your ISI Mark question.
                </p>

            </div>
        `;

        return;
    }

    result.innerHTML = `
        <div class="search-result-card">

            <div class="loading-message">

                <span class="loading-dot"></span>

                <span>
                    BISathi is checking ISI Mark guidance...
                </span>

            </div>

        </div>
    `;

    try {

        console.log(
            "Sending ISI Verification request to:",
            API_ISI_URL
        );

        const response =
            await fetch(
                API_ISI_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        question: question,
                        user_type:
                            "consumer"
                    })
                }
            );

        if (!response.ok) {
            throw new Error(
                "Server returned HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        if (!data.success) {

            result.innerHTML = `
                <div class="search-result-card error-box">

                    <p>
                        ${escapeHTML(
                            data.answer ||
                            "BISathi could not process the question."
                        )}
                    </p>

                    ${formatOfficialSources(
                        data.official_sources ||
                        data.sources ||
                        []
                    )}

                </div>
            `;

            return;
        }

        const formatted =
            formatMarkdown(
                data.answer || ""
            );

        result.innerHTML = `
            <div class="certification-result-card">

                ${formatted}

                ${formatOfficialSources(
                    data.official_sources ||
                    data.sources ||
                    []
                )}

            </div>
        `;

    } catch (error) {

        console.error(
            "ISI Verification Error:",
            error
        );

        result.innerHTML = `
            <div class="search-result-card error-box">

                <h3>
                    Unable to verify right now
                </h3>

                <p>
                    BISathi could not connect to the local backend.
                </p>

            </div>
        `;
    }
}


/* =========================================================
   GENERIC ENTER KEY SUPPORT
   ========================================================= */

function attachEnterHandler(elementId, callback) {

    const element =
        document.getElementById(elementId);

    if (!element) {
        return;
    }

    element.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {

                event.preventDefault();

                callback();
            }
        }
    );
}


attachEnterHandler(
    "productSearchInput",
    searchProduct
);

attachEnterHandler(
    "certificationProductInput",
    getCertificationGuidance
);

attachEnterHandler(
    "documentChecklistInput",
    getDocumentChecklist
);

attachEnterHandler(
    "isiVerificationInput",
    verifyISI
);


/* =========================================================
   NAVIGATION ACTIVE STATE
   ========================================================= */

const navLinks =
    document.querySelectorAll(
        ".main-nav a"
    );

window.addEventListener(
    "scroll",
    function () {

        let currentSection = "";

        document
            .querySelectorAll(
                "main section[id]"
            )
            .forEach(
                function (section) {

                    const sectionTop =
                        section.offsetTop - 180;

                    if (
                        window.scrollY >=
                        sectionTop
                    ) {

                        currentSection =
                            section.getAttribute(
                                "id"
                            );
                    }
                }
            );

        navLinks.forEach(
            function (link) {

                link.classList.remove(
                    "active"
                );

                if (
                    link.getAttribute(
                        "href"
                    ) ===
                    "#" + currentSection
                ) {

                    link.classList.add(
                        "active"
                    );
                }
            }
        );
    }
);


/* =========================================================
   CLOSE MOBILE NAV WHEN CLICKING OUTSIDE
   ========================================================= */

document.addEventListener(
    "click",
    function (event) {

        const mobileNav =
            document.getElementById(
                "mobileNav"
            );

        const menuButton =
            document.querySelector(
                ".mobile-menu-btn"
            );

        if (
            mobileNav &&
            mobileNav.classList.contains(
                "show"
            ) &&
            !mobileNav.contains(
                event.target
            ) &&
            !menuButton?.contains(
                event.target
            )
        ) {

            closeMobileNav();
        }
    }
);


/* =========================================================
   BODY MODAL SCROLL CONTROL
   ========================================================= */

const modalStyle =
    document.createElement("style");

modalStyle.textContent = `
    body.modal-open {
        overflow: hidden;
    }
`;

document.head.appendChild(modalStyle);