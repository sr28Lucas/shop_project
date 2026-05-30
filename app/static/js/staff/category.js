function toggleEdit(id) {
    const span = document.getElementById('name-' + id);
    const form = document.getElementById('form-' + id);
    if (span && form) {
        span.classList.toggle('hidden');
        form.classList.toggle('active');
    }
}
