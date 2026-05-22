let selectedFiles = []; // 用於存放 File 物件的陣列
const container = document.getElementById('preview-container');
const input = document.getElementById('img-input');

// 初始化拖拽功能
const sortable = new Sortable(container, {
    animation: 150,
    onEnd: function() {
        // 當拖拽結束時，根據 DOM 順序重新排列 selectedFiles
        const newOrder = Array.from(container.querySelectorAll('.preview-item')).map(item => parseInt(item.dataset.index));
        const reorderedFiles = newOrder.map(index => selectedFiles[index]);
        selectedFiles = reorderedFiles;
        renderPreview(); // 重新渲染以更新 dataset.index
    }
});

// 選擇檔案事件
input.addEventListener('change', function(e) {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        selectedFiles.push(file);
    });
    renderPreview();
    input.value = ''; // 清空 input 以便重複選擇同檔名檔案
});

// 渲染預覽圖
function renderPreview() {
    container.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const div = document.createElement('div');
        div.className = 'preview-item';
        div.dataset.index = index;
        
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        
        const btn = document.createElement('button');
        btn.innerText = 'X';
        btn.className = 'remove-btn';
        btn.onclick = (e) => {
            e.preventDefault();
            selectedFiles.splice(index, 1);
            renderPreview();
        };

        div.appendChild(img);
        div.appendChild(btn);
        container.appendChild(div);
    });
}

// 攔截表單提交
document.getElementById('product-form').onsubmit = async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    // 移除原生 input 裡的檔案，改用我們排序後的陣列
    formData.delete('images'); 
    selectedFiles.forEach(file => {
        formData.append('images', file);
    });

    // 使用 fetch 發送
    const response = await fetch(this.action, {
        method: 'POST',
        body: formData
    });

    if (response.ok) {
        const redirectUrl = this.getAttribute('data-redirect-url');
        window.location.href = redirectUrl;
    } else {
        alert('上傳失敗');
    }
};