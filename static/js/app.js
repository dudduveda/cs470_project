const API_URL = '/api';
let restaurantRatings = new Map();
let cuisineRatings = new Map();
// let dayofRatings = new Map(); // {key: 'r-{id}' or 'c-{cuisine}', value: {type, id, rating}}
let dayofRatingsByUser = new Map();
let selectedUsers = new Set();
let currentScreen = 'create';
let allRestaurants = [];
let allCuisines = [];
let allUsers = [];
let lastSelectedUser = -1;
let matching = [];
// Helper functions
function showAlert(elementId, message, type) {
    const alertDiv = document.getElementById(elementId);
    alertDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => alertDiv.innerHTML = '', 5000);
}

function getPriceSymbol(price) {
    return '$'.repeat(price);
}

// Navigation
function switchScreen(newScreen) {
    console.log(newScreen);
    // showAlert('createAlert', newScreen, 'error');

    if (newScreen) {
        currentScreen = 'matching';
        document.getElementById('listScreen').classList.remove('active');
        document.getElementById('createScreen').classList.remove('active');
        document.getElementById('matchingScreen').classList.add('active');
        return;
    }
    if (currentScreen === 'create') {
        currentScreen = 'list';
        document.getElementById('createScreen').classList.remove('active');
        document.getElementById('matchingScreen').classList.remove('active');
        document.getElementById('listScreen').classList.add('active');
        document.getElementById('navBtn').textContent = 'Create New User';
        loadUsers();
    } else {
        currentScreen = 'create';
        document.getElementById('listScreen').classList.remove('active');
        document.getElementById('matchingScreen').classList.remove('active');
        document.getElementById('createScreen').classList.add('active');
        document.getElementById('navBtn').textContent = 'View All Users';
        restaurantRatings.clear();
        cuisineRatings.clear();
        selectedUsers.clear();
        // dayofRatings.clear();
        document.getElementById('dayofSection').style.display = 'none';
        renderCuisines();
        renderRestaurants();
        renderSelected();
    }
}

document.getElementById('navBtn').addEventListener('click', () => switchScreen());
// document.getElementById('match');


// ==================== Cuisines ====================
function extractCuisines() {
    const cuisineSet = new Set();
    allRestaurants.forEach(r => {
        const cuisines = r.cuisine.split(',').map(c => c.trim());
        cuisines.forEach(c => {
            if (c) cuisineSet.add(c);
        });
    });
    allCuisines = Array.from(cuisineSet).sort();
}

function renderCuisines() {
    const grid = document.getElementById('cuisineGrid');
    if (allCuisines.length === 0) {
        grid.innerHTML = '<div class="empty-state">No cuisines available</div>';
        return;
    }
    grid.innerHTML = allCuisines.map(cuisine => `
        <div class="cuisine-card ${cuisineRatings.has(cuisine) ? 'selected' : ''}" 
             onclick="toggleCuisine('${cuisine.replace(/'/g, "\\'")}')">
            <h3>${cuisine}</h3>
        </div>
    `).join('');
}

function toggleCuisine(cuisine) {
    if (cuisineRatings.has(cuisine)) {
        cuisineRatings.delete(cuisine);
    } else {
        cuisineRatings.set(cuisine, 5.0);
    }
    renderCuisines();
    renderSelected();
}

function updateCuisineRating(cuisine, value) {
    const floatValue = parseFloat(value);
    cuisineRatings.set(cuisine, floatValue);
    const elementId = `cuisine-rating-${cuisine.replace(/\s+/g, '-')}`;
    document.getElementById(elementId).textContent = `${floatValue.toFixed(1)}/10`;
}

function removeCuisine(cuisine) {
    cuisineRatings.delete(cuisine);
    renderCuisines();
    renderSelected();
}

// ==================== Restaurants ====================
async function loadRestaurants() {
    try {
        const res = await fetch(`${API_URL}/restaurants`);
        allRestaurants = await res.json();
        extractCuisines();
        renderCuisines();
        renderRestaurants();
    } catch (err) {
        console.error('Error loading restaurants:', err);
        showAlert('createAlert', 'Error loading restaurants', 'error');
    }
}

function renderRestaurants() {
    const grid = document.getElementById('restaurantGrid');
    if (allRestaurants.length === 0) {
        grid.innerHTML = '<div class="empty-state">No restaurants available</div>';
        return;
    }
    grid.innerHTML = allRestaurants.map(rest => `
        <div class="restaurant-card ${restaurantRatings.has(rest.id) ? 'selected' : ''}" 
             onclick="toggleRestaurant(${rest.id})">
            <h3>${rest.name}</h3>
            <p>
                <span class="cuisine-badge">${rest.cuisine}</span>
                <span class="price-indicator">${getPriceSymbol(rest.price)}</span>
            </p>
        </div>
    `).join('');
}

function toggleRestaurant(id) {
    if (restaurantRatings.has(id)) {
        restaurantRatings.delete(id);
    } else {
        restaurantRatings.set(id, 5.0);
    }
    renderRestaurants();
    renderSelected();
}

function updateRating(id, value) {
    const floatValue = parseFloat(value);
    restaurantRatings.set(id, floatValue);
    document.getElementById(`rating-${id}`).textContent = `${floatValue.toFixed(1)}/10`;
}

function removeRestaurant(id) {
    restaurantRatings.delete(id);
    renderRestaurants();
    renderSelected();
}

function renderSelected() {
    const container = document.getElementById('selectedCuisines');
    if (cuisineRatings.size === 0 && restaurantRatings.size === 0) {
        container.innerHTML = '<div class="empty-state">No items selected</div>';
        return;
    }

    let html = '';
    if (cuisineRatings.size > 0) {
        html += '<h4 style="color: #ff6b6b; margin-bottom: 10px; font-size: 14px; text-transform: uppercase;">Cuisines</h4>';
        cuisineRatings.forEach((rating, cuisine) => {
            const safeId = cuisine.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '');
            html += `
                <div class="selected-cuisine-item">
                    <h4>${cuisine}</h4>
                    <div class="rating-slider-container">
                        <input type="range" class="rating-slider" min="1" max="10" step="0.1" value="${rating}"
                               oninput="updateCuisineRating('${cuisine.replace(/'/g, "\\'")}', this.value)">
                        <div class="rating-display">
                            <span>Rating:</span>
                            <span class="rating-value" id="cuisine-rating-${safeId}">${rating.toFixed(1)}/10</span>
                            <button type="button" class="remove-btn" onclick="removeCuisine('${cuisine.replace(/'/g, "\\'")}')">Remove</button>
                        </div>
                    </div>
                </div>
            `;
        });
    }

    if (restaurantRatings.size > 0) {
        html += '<h4 style="color: #28a745; margin: 20px 0 10px 0; font-size: 14px; text-transform: uppercase;">Restaurants</h4>';
        restaurantRatings.forEach((rating, id) => {
            const restaurant = allRestaurants.find(r => r.id === id);
            html += `
                <div class="selected-item">
                    <h4>${restaurant.name}</h4>
                    <p>
                        <span class="cuisine-badge">${restaurant.cuisine}</span>
                        <span class="price-indicator">${getPriceSymbol(restaurant.price)}</span>
                    </p>
                    <div class="rating-slider-container">
                        <input type="range" class="rating-slider" min="1" max="10" step="0.1" value="${rating}"
                               oninput="updateRating(${id}, this.value)">
                        <div class="rating-display">
                            <span>Rating:</span>
                            <span class="rating-value" id="rating-${id}">${rating.toFixed(1)}/10</span>
                            <button type="button" class="remove-btn" onclick="removeRestaurant(${id})">Remove</button>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    container.innerHTML = html;
}

// ==================== Users ====================
async function createUser(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;

    if (restaurantRatings.size === 0 && cuisineRatings.size === 0) {
        showAlert('createAlert', 'Please select at least one restaurant or cuisine', 'error');
        return;
    }

    const restaurantPreferences = Array.from(restaurantRatings.entries()).map(([id, rating]) => ({
        restaurant_id: id,
        rating: rating
    }));

    const cuisinePreferences = Array.from(cuisineRatings.entries()).map(([cuisine, rating]) => ({
        cuisine: cuisine,
        rating: rating
    }));

    try {
        const res = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                username,
                preferences: restaurantPreferences,
                cuisine_preferences: cuisinePreferences
            })
        });

        if (res.ok) {
            const totalPrefs = restaurantRatings.size + cuisineRatings.size;
            showAlert('createAlert', `User created with ${totalPrefs} preferences!`, 'success');
            document.getElementById('userForm').reset();
            restaurantRatings.clear();
            cuisineRatings.clear();
            renderCuisines();
            renderRestaurants();
            renderSelected();
        } else {
            const error = await res.json();
            showAlert('createAlert', error.error || 'Error creating user', 'error');
        }
    } catch (err) {
        showAlert('createAlert', 'Error creating user', 'error');
    }
}

async function loadUsers() {
    try {
        const res = await fetch(`${API_URL}/users`);
        allUsers = await res.json();
        renderUsers();
    } catch (err) {
        console.error('Error loading users:', err);
        showAlert('listAlert', 'Error loading users', 'error');
    }
}

function renderUsers() {
    const grid = document.getElementById('userListGrid');
    if (allUsers.length === 0) {
        grid.innerHTML = '<div class="empty-state">No users yet. Create some first!</div>';
        return;
    }

    grid.innerHTML = allUsers.map(user => {
        let preferencesHTML = '';
        
        if (user.cuisine_preferences && user.cuisine_preferences.length > 0) {
            preferencesHTML += `
                <div class="preferences-list">
                    <div style="font-size: 10px; color: #ff6b6b; font-weight: bold; margin-bottom: 5px;">CUISINES</div>
                    ${user.cuisine_preferences.map(pref => `
                        <span class="pref-tag" style="background: #ffe0e0; color: #d63031;">
                            ${pref.cuisine}
                            <span class="rating-badge" style="background: #ff6b6b; color: white;">${pref.rating.toFixed(1)}</span>
                        </span>
                    `).join('')}
                </div>
            `;
        }
        
        if (user.preferences && user.preferences.length > 0) {
            preferencesHTML += `
                <div class="preferences-list">
                    <div style="font-size: 10px; color: #28a745; font-weight: bold; margin-bottom: 5px;">RESTAURANTS</div>
                    ${user.preferences.map(pref => {
                        const restaurant = allRestaurants.find(r => r.id === pref.restaurant_id);
                        if (!restaurant) return '';
                        return `
                            <span class="pref-tag">
                                ${restaurant.name}
                                <span class="rating-badge">${pref.rating.toFixed(1)}</span>
                            </span>
                        `;
                    }).join('')}
                </div>
            `;
        }

        if (user.day_of_ratings && user.day_of_ratings.length > 0) {
            preferencesHTML += `
                <div class="preferences-list">
                    <div style="font-size: 10px; color: #ffa500; font-weight: bold; margin-bottom: 5px;">🎯 DAY-OF RATINGS</div>
                    ${user.day_of_ratings.map(rating => {
                        if (rating.restaurant_id) {
                            const restaurant = allRestaurants.find(r => r.id === rating.restaurant_id);
                            return restaurant ? `
                                <span class="dayof-tag">
                                    ${restaurant.name}
                                    <span class="rating-badge" style="background: #ffa500;">${rating.rating.toFixed(1)}</span>
                                </span>
                            ` : '';
                        } else {
                            return `
                                <span class="dayof-tag">
                                    ${rating.cuisine}
                                    <span class="rating-badge" style="background: #ffa500;">${rating.rating.toFixed(1)}</span>
                                </span>
                            `;
                        }
                    }).join('')}
                </div>
            `;
        }
        
        if (!preferencesHTML) {
            preferencesHTML = '<p style="color: #999; margin-top: 10px;">No preferences</p>';
        }
        
        return `
            <div class="user-card ${selectedUsers.has(user.id) ? 'selected' : ''}" 
                 onclick="toggleUser(${user.id})">
                <div class="selection-indicator">
                    ${selectedUsers.has(user.id) ? '✓' : ''}
                </div>
                <h3>${user.username}</h3>
                <p>Created: ${new Date(user.created_at).toLocaleDateString()}</p>
                ${preferencesHTML}
            </div>
        `;
    }).join('');

    updateSelectedCount();
}

function toggleUser(id) {
    
    if (selectedUsers.has(id)) {
        selectedUsers.delete(id);
        lastSelectedUser = -1;
    } else {
        selectedUsers.add(id);
        lastSelectedUser = id;
        // if (dayofRatingsByUser.has(id)) {
        //     dayofRatings = dayofRatingsByUser.get(id);
        // } else {
        //     dayofRatings = new Map();
        // }
    }
    const matchbtn = document.getElementById("matchbtn");
    if (selectedUsers.size >= 2) {
        matchbtn.style.display = 'inline-block';
    } else {
        matchbtn.style.display = 'none';
    }
    console.log(lastSelectedUser);
    renderUsers();
    updateDayofSection();
}

function selectAllUsers() {
    allUsers.forEach(user => selectedUsers.add(user.id));
    renderUsers();
    updateDayofSection();
}

function deselectAllUsers() {
    selectedUsers.clear();
    lastSelectedUser = -1;
    // dayofRatings.clear();
    renderUsers();
    updateDayofSection();
}

function updateSelectedCount() {
    const countDiv = document.getElementById('selectedCount');
    if (selectedUsers.size > 0) {
        countDiv.style.display = 'inline-block';
        countDiv.textContent = `${selectedUsers.size} user${selectedUsers.size > 1 ? 's' : ''} selected`;
    } else {
        countDiv.style.display = 'none';
    }
}

async function deleteSelectedUsers() {
    if (selectedUsers.size === 0) {
        showAlert('listAlert', 'No users selected', 'error');
        return;
    }

    if (!confirm(`Delete ${selectedUsers.size} user(s)?`)) {
        return;
    }

    let successCount = 0;
    for (const userId of selectedUsers) {
        try {
            const res = await fetch(`${API_URL}/users/${userId}`, { method: 'DELETE' });
            if (res.ok) successCount++;
        } catch (err) {
            console.error('Delete error:', err);
        }
    }

    showAlert('listAlert', `Successfully deleted ${successCount} user(s)`, 'success');
    selectedUsers.clear();
    // dayofRatings.clear();
    loadUsers();
    updateDayofSection();
}

// ==================== Day-of Ratings ====================
function updateDayofSection() {
    const section = document.getElementById('dayofSection');
    if (selectedUsers.size === 0 || lastSelectedUser === -1) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    loadUserDayofRatings(lastSelectedUser);
    
}

async function loadUserDayofRatings(userId) {
    try {
        // const userRatings = dayofRatingsByUser.get(userId);
        // if (userRatings) {
        //     dayofRatings = userRatings
        //     // user.day_of_ratings.forEach(rating => {
        //     //     if (rating.restaurant_id) {
        //     //         dayofRatings.set(`r-${rating.restaurant_id}`, {
        //     //             type: 'restaurant',
        //     //             id: rating.restaurant_id,
        //     //             rating: rating.rating
        //     //         });
        //     //     } else {
        //     //         dayofRatings.set(`c-${rating.cuisine}`, {
        //     //             type: 'cuisine',
        //     //             id: rating.cuisine,
        //     //             rating: rating.rating
        //     //         });
        //     //     }
        //     // });
        // } else {

        // }
        renderDayofCuisines();
        renderDayofRestaurants();
        renderDayofSelected();
    } catch (err) {
        console.error('Error loading day-of ratings:', err);
    }
}

function renderDayofCuisines() {
    const grid = document.getElementById('dayofCuisineGrid');
    if (allCuisines.length === 0) {
        grid.innerHTML = '<div class="empty-state">No cuisines</div>';
        return;
    }
    let dayofRatings = new Map();
    if (dayofRatingsByUser.has(lastSelectedUser)) {
        dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    }
    // console.log(lastSelectedUser);

    grid.innerHTML = allCuisines.map(cuisine => {
        const key = `c-${cuisine}`;
        
        const isSelected = dayofRatings.has(key);
        return `
            <div class="cuisine-card ${isSelected ? 'dayof-selected' : ''}" 
                 onclick="toggleDayofCuisine('${cuisine.replace(/'/g, "\\'")}')">
                <h3>${cuisine}</h3>
            </div>
        `;
    }).join('');
}

function renderDayofRestaurants() {
    const grid = document.getElementById('dayofRestaurantGrid');
    if (allRestaurants.length === 0) {
        grid.innerHTML = '<div class="empty-state">No restaurants</div>';
        return;
    }
    let dayofRatings = new Map();
    if (dayofRatingsByUser.has(lastSelectedUser)) {
        dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    }
    // console.log(lastSelectedUser);
    grid.innerHTML = allRestaurants.map(rest => {
        const key = `r-${rest.id}`;
        const isSelected = dayofRatings.has(key);
        return `
            <div class="restaurant-card ${isSelected ? 'dayof-selected' : ''}" 
                 onclick="toggleDayofRestaurant(${rest.id})">
                <h3>${rest.name}</h3>
                <p>
                    <span class="cuisine-badge">${rest.cuisine}</span>
                    <span class="price-indicator">${getPriceSymbol(rest.price)}</span>
                </p>
            </div>
        `;
    }).join('');
}

function toggleDayofCuisine(cuisine) {
    const key = `c-${cuisine}`;
    // if (!dayofRatings.get(userId)) {
    //     showAlert("invalid user somehow");
    //     return;
    // }
    // let dayofRatings = new Map();
    if (!dayofRatingsByUser.has(lastSelectedUser)) {
        dayofRatingsByUser.set(lastSelectedUser, new Map());
    } 
    dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    console.log(lastSelectedUser);
    if (dayofRatings.has(key)) {
        removeDayofRating(key);
    } else {
        if (dayofRatings.size >= 3) {
            showAlert('dayofAlert', 'Maximum 3 day-of ratings allowed!', 'warning');
            return;
        }
        dayofRatings.set(key, {
            type: 'cuisine',
            id: cuisine,
            rating: 5.0
        });
    }
    renderDayofCuisines();
    renderDayofSelected();
}

function toggleDayofRestaurant(id) {
    // if (!dayofRatingsByUser.get(userId)) {
    //     showAlert("invalid user somehow");
    //     return;
    // }
    const key = `r-${id}`;
    
    if (!dayofRatingsByUser.has(lastSelectedUser)) {
        dayofRatingsByUser.set(lastSelectedUser, new Map());
    } 
    dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    if (dayofRatings.has(key)) {
        removeDayofRating(key);
    } else {
        if (dayofRatings.size >= 3) {
            showAlert('dayofAlert', 'Maximum 3 day-of ratings allowed!', 'warning');
            return;
        }
        dayofRatings.set(key, {
            type: 'restaurant',
            id: id,
            rating: 5.0
        });
    }
    renderDayofRestaurants();
    renderDayofSelected();
}

function updateDayofRating(key, value) {
    if (!dayofRatingsByUser.has(lastSelectedUser)) {
        return;
    }
    let dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    const rating = dayofRatings.get(key);
    
    if (rating) {
        rating.rating = parseFloat(value);
        document.getElementById(`dayof-rating-${key}`).textContent = `${rating.rating.toFixed(1)}/10`;
    }
}

function removeDayofRating(key) {
    if (!dayofRatingsByUser.has(lastSelectedUser)) {
        return;
    }
    let dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    dayofRatings.delete(key);
    renderDayofCuisines();
    renderDayofRestaurants();
    renderDayofSelected();
}

// async function callMagic() {
//     if (selectedUsers.size < 2) return;
//     const payloads = [];
//     dayofRatingsByUser.forEach(user => {
//         if (selectedUsers.find(u => u === user)) {
//             payloads.push(user);
//         }
//     });
//     try {
//         const res = await fetch(`${API_URL}/matching`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify(payloads)
//         });

//         const matches = await res.json();
//         switchScreen("matching");
//         renderMatchingList();

//     } catch (err) {
//         console.error('Error generating matches:', err);
//         showAlert('matchingAlert', err.message || 'Error generating matches', 'error');
//         document.getElementById('matchingResults').innerHTML = 
//             '<div class="empty-state">Failed to generate matches. Try again.</div>';
//     }
// }

async function callMagic() {
    if (selectedUsers.size < 2) {
        showAlert('listAlert', 'Please select at least 2 users to generate matches', 'error');
        return;
    }
    console.log(dayofRatingsByUser);
    console.log("dayofByUser");
    const userIds = Array.from(selectedUsers);
    
    // Build the user_ratings payload
    const userRatings = userIds.map(userId => {
        const ratings = [];
        
        // Check if this user has day-of ratings
        if (dayofRatingsByUser.has(userId)) {
            const dayofRatings = dayofRatingsByUser.get(userId);
            
            dayofRatings.forEach((rating, key) => {
                if (rating.type === 'restaurant') {
                    ratings.push({
                        restaurant_id: rating.id,
                        rating: rating.rating
                    });
                } else if (rating.type === 'cuisine') {
                    ratings.push({
                        cuisine: rating.id,
                        rating: rating.rating
                    });
                }
            });
        }
        
        // If no day-of ratings, send empty array (backend will use base preferences)
        return {
            user_id: userId,
            ratings: ratings
        };
    });
    console.log(userIds);
    console.log("userIds");
    try {
        // Show loading state
        showAlert('listAlert', 'Generating matches...', 'success');
        
        const res = await fetch(`${API_URL}/matching`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_ratings: userRatings })
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.error || 'Failed to generate matches');
        }

        matching = await res.json();
        console.log(matching);
        
        // Switch to matching screen and render results
        switchScreen('matching');
        renderMatchingList();
        
    } catch (err) {
        console.error('Error generating matches:', err);
        showAlert('listAlert', err.message || 'Error generating matches', 'error');
    }
}

function renderMatchingList() {
    const container = document.getElementById('matchingResults');
    
    if (!matching || matching.length === 0) {
        container.innerHTML = '<div class="empty-state">No matching restaurants found</div>';
        console.error("this shouldn't happen, should list at least some places");
        return;
    }
    const currMax = Math.max(...matching.map(restaurant => restaurant[2]));

    const html = matching.map((match, index) => {
        const restaurant = match[0];
        
        // const restaurant = allRestaurants.find(r => r.id === restaurantId);
        const cuisine = match[1];
        const rating = 10 * match[2] / currMax;
        console.log("rating", match[2], currMax);
        // Color coding based on rating
        let scoreClass = 'score-high';
        let scoreColor = '#28a745';
        if (rating < 5) {
            scoreClass = 'score-low';
            scoreColor = '#dc3545';
        } else if (rating < 7) {
            scoreClass = 'score-medium';
            scoreColor = '#ffc107';
        }

        return `
            <div class="match-card">
                <div class="match-rank" style="background: ${index < 3 ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}">
                    #${index + 1}
                </div>
                <div class="match-content">
                    <h3>${restaurant}</h3>
                    <div style="margin: 10px 0;">
                        <span class="cuisine-badge">${restaurant}</span>
                        <span class="price-indicator">${getPriceSymbol(restaurant.price)}</span>
                    </div>
                    <div class="match-score">
                        <span class="score-label">Match Score:</span>
                        <span class="score-value ${scoreClass}" style="color: ${scoreColor}">
                            ${rating.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).filter(Boolean).join('');

    if (!html) {
        container.innerHTML = '<div class="empty-state">No valid restaurants found</div>';
        return;
    }

    container.innerHTML = html;
}



// async function saveDayofRating(key) {
//     if (selectedUsers.size !== 1) return;
//     const userId = Array.from(selectedUsers)[0];
//     const rating = dayofRatings.get(key);
    
//     try {
//         const payload = {
//             user_id: userId,
//             rating: rating.rating
//         };
        
//         if (rating.type === 'restaurant') {
//             payload.restaurant_id = rating.id;
//         } else {
//             payload.cuisine = rating.id;
//         }

//         const res = await fetch(`${API_URL}/day-of-ratings`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify(payload)
//         });

//         if (res.ok) {
//             showAlert('dayofAlert', 'Day-of rating saved!', 'success');
//             await loadUsers();
//             renderUsers();
//         } else {
//             const error = await res.json();
//             showAlert('dayofAlert', error.error || 'Error saving rating', 'error');
//             console.log(error.error)
//         }
//     } catch (err) {
//         showAlert('dayofAlert', 'Error saving rating', 'error');
//     }
// }

async function saveAllDayofRatings() {
    if (selectedUsers.size !== 1) return;
    
    const userId = Array.from(selectedUsers)[0];
    const payloads = [];
    if (!dayofRatingsByUser.has(lastSelectedUser)) {
        return;
    }
    let dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    // Construct array of payloads
    dayofRatings.forEach(rating => {
        const entry = {
            user_id: userId,
            rating: rating.rating
        };

        if (rating.type === 'restaurant') {
            entry.restaurant_id = rating.id;
        } else {
            entry.cuisine = rating.id;
        }

        payloads.push(entry);
    });

    try {
        // If your API supports bulk requests:
        const res = await fetch(`${API_URL}/day-of-ratings/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ratings: payloads })
        });

        // // Otherwise, send individually
        // for (const entry of payloads) {
        //     const res = await fetch(`${API_URL}/day-of-ratings`, {
        //         method: 'POST',
        //         headers: { 'Content-Type': 'application/json' },
        //         body: JSON.stringify(entry)
        //     });

        //     if (!res.ok) {
        //         const error = await res.json();
        //         showAlert('dayofAlert', error.error || 'Error saving rating', 'error');
        //         return;
        //     }
        // }

        showAlert('dayofAlert', 'All day-of ratings saved!', 'success');
        await loadUsers();
        renderUsers();

    } catch (err) {
        showAlert('dayofAlert', 'Error saving ratings', 'error');
        console.error(err);
    }
}


function renderDayofSelected() {
    const container = document.getElementById('dayofSelectedItems');
    const counter = document.getElementById('dayofCounter');

    // If no user selected OR no ratings stored
    if (!dayofRatingsByUser.has(lastSelectedUser)) {
        counter.textContent = "0/3";
        container.innerHTML = '<div class="empty-state">No items selected</div>';
        return;
    }

    const dayofRatings = dayofRatingsByUser.get(lastSelectedUser);
    counter.textContent = `${dayofRatings.size}/3`;
    let html = '';
    dayofRatings.forEach((rating, key) => {
        const safeKey = key.replace(/[^a-zA-Z0-9-]/g, '_');
        if (rating.type === 'cuisine') {
            html += `
                <div class="dayof-item">
                    <h4>${rating.id}</h4>
                    <p style="color: #ff6b6b; font-size: 12px; font-weight: bold;">CUISINE</p>
                    <div class="rating-slider-container">
                        <input type="range" class="rating-slider" min="1" max="10" step="0.1" 
                               value="${rating.rating}"
                               oninput="updateDayofRating('${key}', this.value)">
                        <div class="rating-display">
                            <span>Rating:</span>
                            <span class="rating-value" id="dayof-rating-${key}">${rating.rating.toFixed(1)}/10</span>
                            <button type="button" class="remove-btn" onclick="removeDayofRating('${key}')">Remove</button>
                        </div>
                    </div>
                </div>
            `;
        } else {
            const restaurant = allRestaurants.find(r => r.id === rating.id);
            if (restaurant) {
                html += `
                    <div class="dayof-item">
                        <h4>${restaurant.name}</h4>
                        <p>
                            <span class="cuisine-badge">${restaurant.cuisine}</span>
                            <span class="price-indicator">${getPriceSymbol(restaurant.price)}</span>
                        </p>
                        <div class="rating-slider-container">
                            <input type="range" class="rating-slider" min="1" max="10" step="0.1" 
                                   value="${rating.rating}"
                                   oninput="updateDayofRating('${key}', this.value)">
                            <div class="rating-display">
                                <span>Rating:</span>
                                <span class="rating-value" id="dayof-rating-${key}">${rating.rating.toFixed(1)}/10</span>
                                <button type="button" class="remove-btn" onclick="removeDayofRating('${key}')">Remove</button>
                            </div>
                        </div>
                    </div>
                `;
            }
        }
    });
    // if (dayofRatings.size > 0) {
    //     html += `
    //         <button type="button" id="submitAllDayofBtn" 
    //                 class="primary-btn" 
    //                 style="margin-top: 20px; width: 100%; padding: 10px; font-size: 16px;"
    //                 onclick="saveAllDayofRatings()">
    //             Submit All Ratings
    //         </button>
    //     `;
    // }
    container.innerHTML = html;

}

// Event listeners
document.getElementById('userForm').addEventListener('submit', createUser);

// Initialize
loadRestaurants();