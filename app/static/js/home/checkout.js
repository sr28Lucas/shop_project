const regionSelect = document.querySelector('select[name="region"]');
const localitySelect = document.querySelector('select[name="locality"]');

function loadLocalities(regionId, currentLocality = null) {
    fetch("/api/localities/" + regionId)
        .then(response => response.json())
        .then(data => {
            localitySelect.innerHTML = '<option value="">請選擇鄉鎮市區</option>';
            data.localities.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc;
                option.textContent = loc;
                if (loc === currentLocality) {
                    option.selected = true;
                }
                localitySelect.appendChild(option);
            });
        });
}

function initRegionSelect(currentRegion = '', currentLocality = '') {
    if (!regionSelect) return;
    
    fetch("/api/regions")
        .then(response => response.json())
        .then(data => {
            data.regions.forEach(region => {
                const option = document.createElement('option');
                option.value = region.name;
                option.dataset.id = region.id;
                option.textContent = region.name;
                if (region.name === currentRegion) {
                    option.selected = true;
                    loadLocalities(region.id, currentLocality);
                }
                regionSelect.appendChild(option);
            });
        });

    regionSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        localitySelect.innerHTML = '<option value="">請選擇鄉鎮市區</option>';
        if (selectedOption.dataset.id) {
            loadLocalities(selectedOption.dataset.id);
        }
    });
}
