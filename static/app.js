const API_BASE = "";

// Utils
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// State
let isPolling = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Start Poll
    setInterval(pollPendingReviews, 3000);
    pollPendingReviews();

    // Handle Start Form
    $('#start-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const payload = {
            invoice_id: formData.get('invoice_id'),
            vendor_name: formData.get('vendor_name'),
            amount: parseFloat(formData.get('amount')),
            // Add other mock data
            currency: "USD",
            line_items: []
        };

        setGlobalStatus("Starting workflow...", "info");

        try {
            const res = await fetch(`${API_BASE}/workflow/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.status === "COMPLETED") {
                setGlobalStatus(`Workflow Completed!`, "success");
            } else if (data.status === "PAUSED") {
                setGlobalStatus(`Workflow Paused: ${data.message}`, "warning");
                pollPendingReviews(); // Refresh immediately
            } else {
                setGlobalStatus(`Status: ${data.status}`, "info");
            }

            console.log(data);
        } catch (err) {
            setGlobalStatus(`Error: ${err.message}`, "error");
        }
    });
});

// Polling
async function pollPendingReviews() {
    try {
        const res = await fetch(`${API_BASE}/human-review/pending`);
        const data = await res.json();
        renderQueue(data.items);
    } catch (err) {
        console.error("Polling error", err);
    }
}

// Rendering
function renderQueue(items) {
    const list = $('#review-list');
    const count = $('#queue-count');

    count.textContent = `${items.length} Pending`;

    if (items.length === 0) {
        list.innerHTML = '<div class="text-sm text-gray-500 text-center py-4">Queue is empty.</div>';
        return;
    }

    list.innerHTML = items.map(item => `
        <div class="bg-white/5 p-4 rounded-lg border border-white/5 hover:bg-white/10 transition-colors flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-1">
                    <span class="font-semibold text-violet-200">${item.invoice_id}</span>
                    <span class="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">$${item.amount}</span>
                </div>
                <p class="text-xs text-red-300/80">${item.reason || "Review required"}</p>
            </div>
            <button onclick="openReviewModal('${item.checkpoint_id}')" class="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1.5 rounded transition-colors">
                Review
            </button>
        </div>
    `).join('');
}

// Status Display
function setGlobalStatus(message, type) {
    const display = $('#status-display');
    let color = "text-gray-400";
    if (type === "success") color = "text-green-400";
    if (type === "error") color = "text-red-400";
    if (type === "warning") color = "text-yellow-400";

    display.innerHTML = `<p class="${color} font-medium animate-pulse">${message}</p>`;
}

// Modal handling
function openReviewModal(checkpointId) {
    $('#modal-checkpoint-id').value = checkpointId;
    $('#modal-id').textContent = checkpointId.substring(0, 8) + '...';
    $('#decision-form').reset();
    document.getElementById('review-modal').showModal();
}

window.submitDecision = async function (decision) {
    const checkpointId = $('#modal-checkpoint-id').value;
    const notes = $('textarea[name="notes"]').value;

    try {
        const res = await fetch(`${API_BASE}/human-review/decision`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                checkpoint_id: checkpointId,
                decision: decision,
                notes: notes,
                reviewer_id: "user_ui"
            })
        });

        const data = await res.json();

        document.getElementById('review-modal').close();

        if (data.status === "RESUMED") {
            setGlobalStatus(`Decision '${decision}' applied. Workflow Resumed.`, "success");
        } else if (data.status === "PAUSED") {
            setGlobalStatus(`Decision sent. Workflow moved to ${data.next_stage}.`, "warning");
        }

        pollPendingReviews();

    } catch (err) {
        alert(`Failed to submit decision: ${err.message}`);
    }
};
