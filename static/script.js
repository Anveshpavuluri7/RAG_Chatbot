/* ═══════════════════════════════════════════════════════════
   RAG Chatbot — Frontend Logic
   ═══════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
    // ── DOM refs ────────────────────────────────────────
    const chatContainer  = document.getElementById("chat-container");
    const inputForm      = document.getElementById("input-form");
    const queryInput     = document.getElementById("query-input");
    const btnBrowse      = document.getElementById("btn-browse");
    const fileInput      = document.getElementById("file-input");
    const dropzone       = document.getElementById("dropzone");
    const uploadStatus   = document.getElementById("upload-status");
    const docList        = document.getElementById("doc-list");
    const welcome        = document.getElementById("welcome");
    const sidebar        = document.getElementById("sidebar");
    const sidebarToggle  = document.getElementById("sidebar-toggle");
    const sidebarOpen    = document.getElementById("sidebar-open");
    const btnClearAll    = document.getElementById("btn-clear-all");
    const btnClearChat   = document.getElementById("btn-clear-chat");

    let isQuerying = false;

    // ── Sidebar toggle (mobile) ────────────────────────
    if (sidebarOpen) {
        sidebarOpen.addEventListener("click", () => sidebar.classList.add("open"));
    }
    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", () => sidebar.classList.remove("open"));
    }

    // ── Clear actions ──────────────────────────────────
    if (btnClearChat) {
        btnClearChat.addEventListener("click", () => {
            // Remove all chat messages
            document.querySelectorAll(".message").forEach(el => el.remove());
            // Show welcome message again
            if (welcome) {
                welcome.style.display = "block";
            }
        });
    }

    if (btnClearAll) {
        btnClearAll.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to delete all uploaded documents and clear the database?")) return;
            showUploadStatus("loading", "Clearing all data…");
            try {
                const res = await fetch("/documents", { method: "DELETE" });
                const data = await res.json();
                if (res.ok) {
                    showUploadStatus("success", data.message);
                    refreshDocList();
                    if (btnClearChat) btnClearChat.click();
                } else {
                    showUploadStatus("error", data.detail || "Failed to clear data");
                }
            } catch (err) {
                showUploadStatus("error", `Network error: ${err.message}`);
            }
        });
    }

    // ── File upload — browse button ────────────────────
    btnBrowse.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length) uploadFiles(fileInput.files);
    });

    // ── Drag & drop ────────────────────────────────────
    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover",  (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
    dropzone.addEventListener("dragleave", ()  => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
    });

    // ── Suggestion chips ───────────────────────────────
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            queryInput.value = chip.dataset.q;
            submitQuery();
        });
    });

    // ── Form submit ────────────────────────────────────
    inputForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitQuery();
    });

    // ── Upload files ───────────────────────────────────
    async function uploadFiles(files) {
        for (const file of files) {
            showUploadStatus("loading", `Uploading ${file.name}…`);
            const formData = new FormData();
            formData.append("file", file);

            try {
                const res = await fetch("/upload", { method: "POST", body: formData });
                const data = await res.json();
                if (res.ok) {
                    showUploadStatus("success", data.message);
                    refreshDocList();
                } else {
                    showUploadStatus("error", data.detail || "Upload failed");
                }
            } catch (err) {
                showUploadStatus("error", `Network error: ${err.message}`);
            }
        }
        fileInput.value = "";
    }

    function showUploadStatus(type, message) {
        uploadStatus.innerHTML = `<div class="status-msg ${type}">${type === "loading" ? "⏳" : type === "success" ? "✓" : "✗"} ${message}</div>`;
        if (type !== "loading") {
            setTimeout(() => { uploadStatus.innerHTML = ""; }, 5000);
        }
    }

    // ── Refresh document list ──────────────────────────
    async function refreshDocList() {
        try {
            const res = await fetch("/documents");
            const data = await res.json();
            if (data.documents.length === 0) {
                docList.innerHTML = `<li class="doc-empty">No documents yet</li>`;
            } else {
                docList.innerHTML = data.documents.map(name => {
                    const ext = name.split(".").pop().toUpperCase();
                    return `<li><span class="doc-icon">📄</span><span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${name}</span> <span style="font-size:0.68rem;color:var(--text-muted)">${ext}</span><button class="doc-delete-btn" data-doc="${name}" title="Delete document">🗑️</button></li>`;
                }).join("");
                
                // Add event listeners for delete buttons
                document.querySelectorAll(".doc-delete-btn").forEach(btn => {
                    btn.addEventListener("click", async (e) => {
                        const docName = e.currentTarget.dataset.doc;
                        if (!confirm(`Delete document "${docName}"?`)) return;
                        
                        showUploadStatus("loading", `Deleting ${docName}…`);
                        try {
                            const res = await fetch(`/documents/${encodeURIComponent(docName)}`, { method: "DELETE" });
                            const result = await res.json();
                            if (res.ok) {
                                showUploadStatus("success", result.message);
                                refreshDocList();
                            } else {
                                showUploadStatus("error", result.detail || "Failed to delete");
                            }
                        } catch (err) {
                            showUploadStatus("error", `Network error: ${err.message}`);
                        }
                    });
                });
            }
        } catch (e) {
            // silently ignore
        }
    }

    // ── Submit query ───────────────────────────────────
    async function submitQuery() {
        const q = queryInput.value.trim();
        if (!q || isQuerying) return;
        isQuerying = true;

        // Hide welcome
        if (welcome) welcome.style.display = "none";

        // Add user message
        addMessage("user", q);
        queryInput.value = "";

        // Typing indicator
        const typingEl = addTypingIndicator();

        try {
            const res = await fetch("/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q }),
            });
            const data = await res.json();
            typingEl.remove();

            if (res.ok) {
                addMessage("assistant", data.answer, data.sources, data.used_documents);
            } else {
                addMessage("assistant", `⚠️ Error: ${data.detail || "Something went wrong."}`);
            }
        } catch (err) {
            typingEl.remove();
            addMessage("assistant", `⚠️ Network error: ${err.message}`);
        }

        isQuerying = false;
        queryInput.focus();
    }

    // ── Render a chat message ──────────────────────────
    function addMessage(role, text, sources = [], usedDocs = false) {
        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "user" ? "U" : "🤖";

        const body = document.createElement("div");
        body.className = "message-body";
        body.innerHTML = renderMarkdown(text);

        // Sources
        if (sources.length > 0) {
            const srcDiv = document.createElement("div");
            srcDiv.className = "sources";
            sources.forEach(s => {
                const tag = document.createElement("span");
                tag.className = "source-tag";
                tag.textContent = `📎 ${s}`;
                srcDiv.appendChild(tag);
            });
            body.appendChild(srcDiv);
        }

        wrapper.appendChild(avatar);
        wrapper.appendChild(body);
        chatContainer.appendChild(wrapper);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // ── Typing indicator ───────────────────────────────
    function addTypingIndicator() {
        const wrapper = document.createElement("div");
        wrapper.className = "message assistant";

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = "🤖";

        const indicator = document.createElement("div");
        indicator.className = "typing-indicator";
        indicator.innerHTML = "<span></span><span></span><span></span>";

        wrapper.appendChild(avatar);
        wrapper.appendChild(indicator);
        chatContainer.appendChild(wrapper);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return wrapper;
    }

    // ── Minimal Markdown renderer ──────────────────────
    function renderMarkdown(text) {
        if (!text) return "";
        let html = text
            // Code blocks
            .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
                `<pre><code>${escapeHtml(code.trim())}</code></pre>`)
            // Inline code
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            // Bold
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            // Italic
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            // Unordered lists
            .replace(/^\s*[-*]\s+(.+)$/gm, "<li>$1</li>")
            // Ordered lists
            .replace(/^\s*\d+\.\s+(.+)$/gm, "<li>$1</li>")
            // Line breaks  →  paragraphs
            .replace(/\n{2,}/g, "</p><p>")
            .replace(/\n/g, "<br>");

        // Wrap <li> runs in <ul>
        html = html.replace(/((<li>.*?<\/li>\s*)+)/g, "<ul>$1</ul>");

        return `<p>${html}</p>`;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // ── Initial doc list load ──────────────────────────
    refreshDocList();
});