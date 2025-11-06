// API base URL
const API_BASE = 'http://localhost:5001/api';

// Initialize map centered on Mongolia
const map = L.map('map').setView([46.8625, 103.8467], 6);

// Add OpenStreetMap tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// Layer groups
const aimagLayer = L.layerGroup().addTo(map);
const sumLayer = L.layerGroup().addTo(map);
const highlightedLayer = L.layerGroup().addTo(map);

// Store loaded data
let aimags = [];
let sums = [];
let selectedSum = null;

// Load aimags
async function loadAimags() {
    try {
        const response = await fetch(`${API_BASE}/aimags`);
        aimags = await response.json();
        
        aimagLayer.clearLayers();
        
        aimags.forEach(aimag => {
            const geoJsonLayer = L.geoJSON(aimag.geometry, {
                style: {
                    color: '#3388ff',
                    weight: 2,
                    fillColor: '#3388ff',
                    fillOpacity: 0.1
                },
                onEachFeature: function(feature, layer) {
                    layer.bindPopup(`
                        <strong>Аймаг:</strong> ${aimag.name}<br>
                        <button onclick="showAimagSums(${aimag.id})">Сумуудыг харуулах</button>
                    `);
                }
            });
            
            geoJsonLayer.addTo(aimagLayer);
        });
    } catch (error) {
        console.error('Error loading aimags:', error);
    }
}

// Load sums
async function loadSums() {
    try {
        const response = await fetch(`${API_BASE}/sums`);
        sums = await response.json();
        
        sumLayer.clearLayers();
        
        sums.forEach(sum => {
            const geoJsonLayer = L.geoJSON(sum.geometry, {
                style: {
                    color: '#ff7800',
                    weight: 1,
                    fillColor: '#ff7800',
                    fillOpacity: 0.05
                },
                onEachFeature: function(feature, layer) {
                    layer.bindPopup(`
                        <strong>Сум:</strong> ${sum.sum_name}<br>
                        <strong>Аймаг:</strong> ${sum.aimag_name}<br>
                        <button onclick="highlightSum(${sum.id})">Сонгох</button>
                    `);
                }
            });
            
            geoJsonLayer.addTo(sumLayer);
        });
    } catch (error) {
        console.error('Error loading sums:', error);
    }
}

// Show sums for a specific aimag
async function showAimagSums(aimagId) {
    try {
        const response = await fetch(`${API_BASE}/aimags/${aimagId}/sums`);
        const aimagSums = await response.json();
        
        // Update info panel
        const infoContent = document.getElementById('infoContent');
        let html = `<strong>Аймаг:</strong> ${aimags.find(a => a.id === aimagId)?.name || 'Unknown'}<br><br>`;
        html += '<strong>Сумууд:</strong><br>';
        html += '<ul style="margin-left: 20px; margin-top: 5px;">';
        
        aimagSums.forEach(sum => {
            const center = sum.center.coordinates;
            html += `<li>${sum.name} - Төв: (${center[1].toFixed(4)}, ${center[0].toFixed(4)})</li>`;
        });
        
        html += '</ul>';
        infoContent.innerHTML = html;
    } catch (error) {
        console.error('Error loading aimag sums:', error);
    }
}

// Highlight a specific sum
async function highlightSum(sumId) {
    try {
        const response = await fetch(`${API_BASE}/sums/${sumId}`);
        const sum = await response.json();
        
        selectedSum = sum;
        
        // Clear previous highlight
        highlightedLayer.clearLayers();
        
        // Add highlighted sum
        const geoJsonLayer = L.geoJSON(sum.geometry, {
            style: {
                color: '#ff0000',
                weight: 3,
                fillColor: '#ff0000',
                fillOpacity: 0.3
            },
            onEachFeature: function(feature, layer) {
                layer.bindPopup(`
                    <strong>Сум:</strong> ${sum.sum_name}<br>
                    <strong>Аймаг:</strong> ${sum.aimag_name}
                `);
            }
        });
        
        geoJsonLayer.addTo(highlightedLayer);
        
        // Center map on sum
        const center = sum.center.coordinates;
        map.setView([center[1], center[0]], 10);
        
        // Update info panel
        const infoContent = document.getElementById('infoContent');
        infoContent.innerHTML = `
            <strong>Сонгогдсон сум:</strong> ${sum.sum_name}<br>
            <strong>Аймаг:</strong> ${sum.aimag_name}<br>
            <strong>Төвийн координат:</strong> (${center[1].toFixed(4)}, ${center[0].toFixed(4)})
        `;
    } catch (error) {
        console.error('Error highlighting sum:', error);
    }
}

// Search functionality
let searchTimeout;
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    
    if (query.length < 2) {
        searchResults.classList.remove('active');
        return;
    }
    
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
            const results = await response.json();
            
            displaySearchResults(results);
        } catch (error) {
            console.error('Error searching:', error);
        }
    }, 300);
});

function displaySearchResults(results) {
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item">Илэрц олдсонгүй</div>';
        searchResults.classList.add('active');
        return;
    }
    
    searchResults.innerHTML = results.map(result => `
        <div class="search-result-item" onclick="selectSearchResult(${result.id}, '${result.type}')">
            ${result.name}
            <span class="type">${result.type === 'aimag' ? 'Аймаг' : 'Сум'}</span>
        </div>
    `).join('');
    
    searchResults.classList.add('active');
}

function selectSearchResult(id, type) {
    searchInput.value = '';
    searchResults.classList.remove('active');
    
    if (type === 'aimag') {
        const aimag = aimags.find(a => a.id === id);
        if (aimag) {
            const bounds = L.geoJSON(aimag.geometry).getBounds();
            map.fitBounds(bounds);
            showAimagSums(id);
        }
    } else if (type === 'sum') {
        highlightSum(id);
    }
}

// Layer visibility controls
document.getElementById('layer1').addEventListener('change', function() {
    if (this.checked) {
        map.addLayer(aimagLayer);
    } else {
        map.removeLayer(aimagLayer);
    }
});

document.getElementById('layer2').addEventListener('change', function() {
    if (this.checked) {
        map.addLayer(sumLayer);
    } else {
        map.removeLayer(sumLayer);
    }
});

// Close search results when clicking outside
document.addEventListener('click', function(event) {
    if (!searchInput.contains(event.target) && !searchResults.contains(event.target)) {
        searchResults.classList.remove('active');
    }
});

// Initial load
loadAimags();
loadSums();

// Make functions available globally
window.showAimagSums = showAimagSums;
window.highlightSum = highlightSum;
window.selectSearchResult = selectSearchResult;

