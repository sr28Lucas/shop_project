// 全選功能
const selectAll = document.getElementById('select-all');
if (selectAll) {
    selectAll.addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('.product-checkbox');
        checkboxes.forEach(cb => cb.checked = this.checked);
    });
}

// 個別刪除功能
function deleteProduct(id, deleteUrlBase) {
    const form = document.getElementById('single-delete-form');
    if (form) {
        // 假設 deleteUrlBase 類似於 "/staff/product/delete/"
        form.action = deleteUrlBase + id;
        form.submit();
    }
}
