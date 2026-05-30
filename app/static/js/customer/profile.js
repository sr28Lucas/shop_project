/**
 * 會員資料管理相關 JS
 */

function initDistrictSelectors(jsonPath, initialRegion = '', initialLocality = '') {
    let districtData = {};
    const regionSelect = document.querySelector('select[name="region"]');
    const localitySelect = document.querySelector('select[name="locality"]');

    if (!regionSelect || !localitySelect) return;

    fetch(jsonPath)
        .then(response => response.json())
        .then(data => {
            districtData = data;
            // 動態生成縣市選項
            regionSelect.innerHTML = '<option value="">請選擇縣市</option>';
            for (const region in districtData) {
                const option = document.createElement('option');
                option.value = region;
                option.textContent = region;
                if (region === initialRegion) {
                    option.selected = true;
                }
                regionSelect.appendChild(option);
            }
            
            // 如果有初始縣市，則觸發更新鄉鎮市區
            if (initialRegion) {
                updateLocalities(initialRegion, initialLocality);
            }
        })
        .catch(error => console.error('Error loading district data:', error));

    regionSelect.addEventListener('change', function() {
        updateLocalities(this.value);
    });

    function updateLocalities(region, selectedLocality = '') {
        const localities = districtData[region] || [];
        localitySelect.innerHTML = '<option value="">請選擇鄉鎮市區</option>';
        localities.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc;
            option.textContent = loc;
            if (loc === selectedLocality) {
                option.selected = true;
            }
            localitySelect.appendChild(option);
        });
    }
}
