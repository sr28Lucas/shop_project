let allImages = [];
let deletedIds = [];
let container, input;

function initProductEdit(initialImages) {
    allImages = initialImages;
    container = document.getElementById('preview-container');
    input = document.getElementById('img-input');

    if (!container || !input) return;

    // 初始化拖拽
    new Sortable(container, {
        animation: 150,
        onEnd: function() {
            const newOrder = Array.from(container.querySelectorAll('.preview-item')).map(item => parseInt(item.dataset.idx));
            allImages = newOrder.map(idx => allImages[idx]);
            renderPreview();
        }
    });

    // 選擇新檔案
    input.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        files.forEach(file => {
            allImages.push({ type: 'new', file: file, previewUrl: URL.createObjectURL(file) });
        });
        renderPreview();
        input.value = '';
    });

    // 提交表單
    document.getElementById('product-form').onsubmit = async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        let imageOrder = [];
        let newFileCount = 0;

        allImages.forEach(img => {
            if (img.type === 'old') {
                imageOrder.push(`old_${img.id}`);
            } else {
                imageOrder.push(`new_${newFileCount}`);
                formData.append('images', img.file);
                newFileCount++;
            }
        });

        formData.append('image_order', imageOrder.join(','));
        formData.append('deleted_ids', deletedIds.join(','));

        const response = await fetch(window.location.href, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            alert('修改成功！');
            window.location.href = document.getElementById('product-form').dataset.redirectUrl;
        } else {
            alert('更新失敗，請稍後再試');
        }
    };

    renderPreview();
}

function renderPreview() {
    if (!container) return;
    container.innerHTML = '';
    allImages.forEach((imgObj, index) => {
        const div = document.createElement('div');
        div.className = 'preview-item';
        div.dataset.idx = index;
        
        const img = document.createElement('img');
        img.src = imgObj.type === 'old' ? imgObj.url : imgObj.previewUrl;
        
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.innerHTML = '×';
        btn.className = 'remove-btn';
        btn.onclick = () => {
            if (imgObj.type === 'old') {
                deletedIds.push(imgObj.id);
            }
            allImages.splice(index, 1);
            renderPreview();
        };

        const tag = document.createElement('span');
        tag.className = 'tag-badge ' + (imgObj.type === 'old' ? 'tag-old' : 'tag-new');
        tag.innerText = imgObj.type === 'old' ? '現有' : '新上傳';

        div.appendChild(img);
        div.appendChild(btn);
        div.appendChild(tag);
        container.appendChild(div);
    });
}
