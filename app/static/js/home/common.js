// 前台共用 JS
document.addEventListener('DOMContentLoaded', function() {
    console.log('Home Page Loaded');

    // Mobile Menu Toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Category Menu Toggle (Narrow Screens)
    const categoryMenuButton = document.getElementById('category-menu-button');
    const categoryMenu = document.getElementById('category-menu');

    if (categoryMenuButton && categoryMenu) {
        categoryMenuButton.addEventListener('click', function() {
            categoryMenu.classList.toggle('hidden');
            // Toggle icon direction if needed
            const icon = categoryMenuButton.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-chevron-down');
                icon.classList.toggle('fa-chevron-up');
            }
        });
    }
});
