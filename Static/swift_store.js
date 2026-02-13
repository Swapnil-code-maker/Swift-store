// ========== DYNAMIC PRODUCTS FROM BACKEND ==========
let products = [];

// Fetch products from Flask API
fetch("/api/products")
    .then(response => response.json())
    .then(data => {
        products = data;
        renderProducts();
    })
    .catch(error => {
        console.error("Error loading products:", error);
    });

// ========== CART STATE ==========
let cart = [];
let currentFilter = 'all';

// ========== DOM ELEMENTS ==========
const productsSection = document.getElementById('productsSection');
const cartItemsContainer = document.getElementById('cartItemsContainer');
const cartTotalContainer = document.getElementById('cartTotalContainer');
const cartTotalPrice = document.getElementById('cartTotalPrice');
const cartItemCount = document.getElementById('cartItemCount');
const searchInput = document.getElementById('searchInput');
const themeToggle = document.getElementById('themeToggle');

// ========== THEME TOGGLE ==========
function initTheme() {
    const savedTheme = localStorage.getItem('swiftStoreTheme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggle.textContent = '☀️ Light';
    }
}

themeToggle.addEventListener('click', function () {
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-theme');
    localStorage.setItem('swiftStoreTheme', isDark ? 'dark' : 'light');
    themeToggle.textContent = isDark ? '☀️ Light' : '🌙 Dark';
});

// ========== STORE FILTER ==========
document.querySelectorAll('.store-item').forEach(item => {
    item.addEventListener('click', function () {
        document.querySelectorAll('.store-item').forEach(i => i.classList.remove('active'));
        this.classList.add('active');
        currentFilter = this.dataset.store;
        searchInput.value = '';
        renderProducts('');
    });
});

// ========== SEARCH ==========
searchInput.addEventListener('input', function (e) {
    renderProducts(e.target.value);
});

// ========== RENDER PRODUCTS ==========
function renderProducts(filterText = '') {
    let filtered = products;

    if (currentFilter !== 'all') {
        filtered = filtered.filter(p => p.store === currentFilter);
    }

    if (filterText.trim() !== '') {
        filtered = filtered.filter(p =>
            p.name.toLowerCase().includes(filterText.toLowerCase()) ||
            p.store.toLowerCase().includes(filterText.toLowerCase())
        );
    }

    const grouped = filtered.reduce((acc, product) => {
        if (!acc[product.store]) acc[product.store] = [];
        acc[product.store].push(product);
        return acc;
    }, {});

    let html = '';

    Object.keys(grouped).sort().forEach(store => {
        html += `<div class="category"><h2>${store}</h2><div class="product-grid">`;

        grouped[store].forEach(product => {
            const cartItem = cart.find(item => item.id === product.id);
            const qty = cartItem ? cartItem.quantity : 0;

            html += `
                <div class="product-card">
                    <img src="${product.image}" alt="${product.name}" class="product-img">
                    <span class="delivery-badge">10 min</span>
                    <div class="product-name">${product.name}</div>
                    <div class="product-store">${product.store}</div>
                    <div class="product-price">₹${product.price}</div>
                    <div class="cart-controls">
                        ${qty === 0
                            ? `<button class="add-btn" onclick="addToCart(${product.id})">Add to Cart</button>`
                            : `<button class="qty-btn minus" onclick="updateQuantity(${product.id}, -1)">−</button>
                               <span class="item-count">${qty}</span>
                               <button class="qty-btn plus" onclick="updateQuantity(${product.id}, 1)">+</button>`
                        }
                    </div>
                </div>
            `;
        });

        html += `</div></div>`;
    });

    productsSection.innerHTML = html || `
        <div style="text-align:center; padding:60px; color:var(--text-muted);">
            <h3>No products found</h3>
            <p>Add products from vendor dashboard</p>
        </div>
    `;
}

// ========== CART FUNCTIONS ==========
window.addToCart = function (productId) {
    const product = products.find(p => p.id === productId);
    const existing = cart.find(item => item.id === productId);

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ ...product, quantity: 1 });
    }

    updateUI();
};

window.updateQuantity = function (productId, delta) {
    const item = cart.find(i => i.id === productId);

    if (item) {
        item.quantity += delta;
        if (item.quantity <= 0) {
            cart = cart.filter(i => i.id !== productId);
        }
    }

    updateUI();
};

function renderCart() {
    if (cart.length === 0) {
        cartItemsContainer.innerHTML =
            '<div class="empty-cart"><p>Your cart is empty</p><small>Add items to get 10 min delivery</small></div>';
        cartTotalContainer.style.display = 'none';
        if (cartItemCount) cartItemCount.innerText = '0';
        return;
    }

    let itemsHtml = '<ul class="cart-items">';
    let total = 0;
    let totalItems = 0;

    cart.forEach(item => {
        total += item.price * item.quantity;
        totalItems += item.quantity;

        itemsHtml += `
            <li class="cart-item">
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.name} x${item.quantity}</div>
                    <div class="cart-item-store">${item.store}</div>
                </div>
                <div class="cart-item-price">₹${item.price * item.quantity}</div>
            </li>
        `;
    });

    itemsHtml += '</ul>';

    cartItemsContainer.innerHTML = itemsHtml;
    cartTotalPrice.innerText = `₹${total}`;
    if (cartItemCount) cartItemCount.innerText = totalItems;
    cartTotalContainer.style.display = 'block';
}

function updateUI() {
    renderProducts(searchInput.value);
    renderCart();
}

// ========== INITIALIZATION ==========
function init() {
    initTheme();
    renderCart();
}

init();
