// Public Website JavaScript

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize hero slider if exists
    initHeroSlider();
    
    // Initialize smooth scrolling
    initSmoothScroll();
    
    // Initialize animations on scroll
    initScrollAnimations();
});

// Hero Slider Functionality
function initHeroSlider() {
    const slides = document.querySelectorAll('.hero-slide');
    if (slides.length <= 1) return;
    
    let currentSlide = 0;
    
    function nextSlide() {
        slides[currentSlide].classList.remove('active');
        currentSlide = (currentSlide + 1) % slides.length;
        slides[currentSlide].classList.add('active');
    }
    
    // Auto-play slider
    setInterval(nextSlide, 5000);
    
    // Pause on hover
    const slider = document.getElementById('heroSlider');
    if (slider) {
        let intervalId = setInterval(nextSlide, 5000);
        
        slider.addEventListener('mouseenter', function() {
            clearInterval(intervalId);
        });
        
        slider.addEventListener('mouseleave', function() {
            intervalId = setInterval(nextSlide, 5000);
        });
    }
}

// Smooth Scrolling
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
}

// Scroll Animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe elements with animation class
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

// Lightbox Function
function openLightbox(imageSrc, title) {
    const modal = document.getElementById('lightboxModal');
    const img = document.getElementById('lightboxImage');
    const titleEl = document.getElementById('lightboxTitle');
    
    if (img) img.src = imageSrc;
    if (titleEl) titleEl.textContent = title || '';
    
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Form Validation
function validateContactForm() {
    const form = document.getElementById('contactForm');
    if (!form) return false;
    
    const name = form.querySelector('[name="name"]');
    const message = form.querySelector('[name="message"]');
    
    let isValid = true;
    
    if (!name || !name.value.trim()) {
        showFieldError(name, 'Name is required');
        isValid = false;
    }
    
    if (!message || !message.value.trim()) {
        showFieldError(message, 'Message is required');
        isValid = false;
    }
    
    return isValid;
}

function showFieldError(field, message) {
    if (!field) return;
    
    field.classList.add('is-invalid');
    
    let errorDiv = field.parentElement.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        field.parentElement.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
}

// Remove error on input
document.addEventListener('input', function(e) {
    if (e.target.classList.contains('is-invalid')) {
        e.target.classList.remove('is-invalid');
    }
});

// Gallery Filter (if needed)
function filterGallery(category) {
    const items = document.querySelectorAll('.gallery-item');
    items.forEach(item => {
        const itemCategory = item.getAttribute('data-category');
        if (!category || itemCategory === category) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// Navbar scroll effect
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', function() {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 100) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
    
    lastScroll = currentScroll;
});

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Lazy loading images
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

