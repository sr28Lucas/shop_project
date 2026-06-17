document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('chatbot-toggle');
    if (!toggleBtn) return;

    // Simple Markdown to HTML parser for links and bold
    function renderMarkdown(text) {
        let html = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" class="text-brand underline">$1</a>')
            .replace(/\n/g, '<br>');
        return html;
    }

    // Create Modal UI
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-[100] flex items-center justify-center bg-black/50 hidden';
    modal.innerHTML = `
        <div class="bg-white rounded-2xl w-96 max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
            <div class="p-4 border-b flex justify-between items-center">
                <h3 class="font-bold text-lg text-brand">VIVID 導購助手</h3>
                <button id="close-chatbot" class="text-gray-500 hover:text-gray-800"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div id="chat-messages" class="flex-1 p-4 overflow-y-auto space-y-3 bg-gray-50">
                <div class="text-sm text-gray-700 bg-white p-3 rounded-xl border">您好！我是您的導購助手，請問您在尋找什麼樣的商品嗎？</div>
            </div>
            <div class="p-4 border-t">
                <form id="chat-form" class="flex space-x-2">
                    <input type="text" id="chat-input" class="flex-1 border rounded-full px-4 py-2 text-sm focus:ring-2 focus:ring-brand outline-none" placeholder="例如：我想找一件適合跑步的外套...">
                    <button type="submit" class="bg-brand text-white px-4 py-2 rounded-full text-sm font-bold">發送</button>
                </form>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Toggle Modal
    toggleBtn.addEventListener('click', () => modal.classList.remove('hidden'));
    document.getElementById('close-chatbot').addEventListener('click', () => modal.classList.add('hidden'));

    // Handle Chat
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('chat-input');
        const query = input.value.trim();
        if (!query) return;

        const messages = document.getElementById('chat-messages');
        messages.innerHTML += `<div class="text-sm text-white bg-brand p-3 rounded-xl self-end">${query}</div>`;
        input.value = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await response.json();
            const formattedResponse = renderMarkdown(data.response || data.error);
            messages.innerHTML += `<div class="text-sm text-gray-700 bg-white p-3 rounded-xl border">${formattedResponse}</div>`;
            messages.scrollTop = messages.scrollHeight;
        } catch (err) {
            messages.innerHTML += `<div class="text-sm text-red-700 bg-red-50 p-3 rounded-xl border">抱歉，目前無法連線至服務。</div>`;
        }
    });
});
