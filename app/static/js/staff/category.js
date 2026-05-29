function toggleEdit(id) {
    const span = document.getElementById('name-' + id);
    const form = document.getElementById('form-' + id);
    if (form.style.display === 'none' || form.style.display === '') {
        form.style.display = 'inline-block';
        span.style.display = 'none';
    } else {
        form.style.display = 'none';
        span.style.display = 'inline';
    }
}
