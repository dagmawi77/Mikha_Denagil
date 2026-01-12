// Public Website JavaScript

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize navbar scroll effect
    initNavbarScroll();
    
    // Initialize hero slider if exists
    initHeroSlider();
    
    // Initialize smooth scrolling
    initSmoothScroll();
    
    // Initialize animations on scroll
    initScrollAnimations();
    
    // Initialize hero slider indicators
    initHeroIndicators();
});

// Hero Slider Functionality
function initHeroSlider() {
    const slides = document.querySelectorAll('.hero-slide');
    
    if (slides.length === 0) {
        console.log('[Hero Slider] No slides found');
        return;
    }
    
    console.log(`[Hero Slider] Found ${slides.length} slides`);
    
    // Fix image paths for hero slides - check if images exist and use fallback if needed
    slides.forEach(function(slide, index) {
        // Get computed style to check if background-image is set
        const computedStyle = window.getComputedStyle(slide);
        const bgImage = computedStyle.backgroundImage || slide.style.backgroundImage;
        const fallback = slide.getAttribute('data-bg-fallback');
        const imagePath = slide.getAttribute('data-image-path');
        
        console.log(`[Hero Slider] Slide ${index}:`, {
            bgImage: bgImage,
            inlineStyle: slide.style.backgroundImage,
            computedStyle: computedStyle.backgroundImage,
            fallback: fallback,
            imagePath: imagePath
        });
        
        // If we have an image path but no background image set, set it
        if (imagePath && (!bgImage || bgImage === 'none' || bgImage === '')) {
            const imageUrl = `/static/${imagePath}`;
            console.log(`[Hero Slider] Setting background image from data-image-path: ${imageUrl}`);
            slide.style.backgroundImage = `url('${imageUrl}')`;
        }
        
        // Now check if we have a background image to validate
        const currentBgImage = slide.style.backgroundImage || computedStyle.backgroundImage;
        
        if (currentBgImage && currentBgImage !== 'none' && currentBgImage.includes('url(')) {
            const img = new Image();
            const urlMatch = currentBgImage.match(/url\(['"]?([^'"]+)['"]?\)/);
            
            if (urlMatch) {
                const imageUrl = urlMatch[1];
                console.log(`[Hero Slider] Testing image: ${imageUrl}`);
                
                img.onload = function() {
                    console.log(`[Hero Slider] ✓ Image loaded successfully: ${imageUrl}`);
                };
                
                img.onerror = function() {
                    console.warn(`[Hero Slider] ✗ Image failed to load: ${imageUrl}`);
                    // If main image fails, try fallback
                    if (fallback) {
                        console.log(`[Hero Slider] Trying fallback: ${fallback}`);
                        const fallbackImg = new Image();
                        fallbackImg.onload = function() {
                            slide.style.backgroundImage = `url('${fallback}')`;
                            console.log(`[Hero Slider] ✓ Fallback image loaded: ${fallback}`);
                        };
                        fallbackImg.onerror = function() {
                            console.error(`[Hero Slider] ✗ Fallback also failed: ${fallback}`);
                            // Use gradient fallback
                            slide.style.backgroundImage = 'linear-gradient(135deg, #14860C 0%, #106b09 100%)';
                        };
                        fallbackImg.src = fallback;
                    } else if (imagePath) {
                        // Try direct path
                        const directPath = `/uploads/${imagePath}`;
                        console.log(`[Hero Slider] Trying direct path: ${directPath}`);
                        const directImg = new Image();
                        directImg.onload = function() {
                            slide.style.backgroundImage = `url('${directPath}')`;
                            console.log(`[Hero Slider] ✓ Direct path image loaded: ${directPath}`);
                        };
                        directImg.onerror = function() {
                            slide.style.backgroundImage = 'linear-gradient(135deg, #14860C 0%, #106b09 100%)';
                        };
                        directImg.src = directPath;
                    } else {
                        // No fallback, use gradient
                        slide.style.backgroundImage = 'linear-gradient(135deg, #14860C 0%, #106b09 100%)';
                    }
                };
                
                img.src = imageUrl;
            }
        } else {
            // Slide has no background image - check if it's intentional (gradient) or needs fixing
            if (imagePath && imagePath !== 'none' && imagePath !== 'None') {
                // We have an image path but no background - try to set it
                const tryUrl = `/static/${imagePath}`;
                console.log(`[Hero Slider] Attempting to set image: ${tryUrl}`);
                const img = new Image();
                img.onload = function() {
                    slide.style.backgroundImage = `url('${tryUrl}')`;
                    console.log(`[Hero Slider] ✓ Image loaded: ${tryUrl}`);
                };
                img.onerror = function() {
                    console.warn(`[Hero Slider] ✗ Image failed: ${tryUrl}`);
                    // Try fallback
                    if (fallback) {
                        slide.style.backgroundImage = `url('${fallback}')`;
                    } else {
                        slide.style.backgroundImage = 'linear-gradient(135deg, #14860C 0%, #106b09 100%)';
                    }
                };
                img.src = tryUrl;
            } else {
                // No image path - slide is using gradient background (intentional)
                console.log(`[Hero Slider] Slide ${index} using gradient background (no image uploaded)`);
                // Ensure gradient is set
                if (!slide.style.backgroundImage || slide.style.backgroundImage === 'none') {
                    slide.style.backgroundImage = 'linear-gradient(135deg, #14860C 0%, #106b09 100%)';
                }
            }
        }
    });
    
    if (slides.length <= 1) return;
    
    let currentSlide = 0;
    let sliderInterval = null;
    
    function nextSlide() {
        slides[currentSlide].classList.remove('active');
        currentSlide = (currentSlide + 1) % slides.length;
        slides[currentSlide].classList.add('active');
        updateIndicators();
    }
    
    function goToSlide(index) {
        slides[currentSlide].classList.remove('active');
        currentSlide = index;
        slides[currentSlide].classList.add('active');
        updateIndicators();
    }
    
    function updateIndicators() {
        const indicators = document.querySelectorAll('.hero-indicator');
        indicators.forEach((indicator, index) => {
            if (index === currentSlide) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        });
    }
    
    // Store functions globally for indicator clicks
    window.heroSliderNext = nextSlide;
    window.heroSliderGoTo = goToSlide;
    
    // Auto-play slider
    sliderInterval = setInterval(nextSlide, 6000);
    
    // Pause on hover
    const slider = document.getElementById('heroSlider');
    if (slider) {
        slider.addEventListener('mouseenter', function() {
            if (sliderInterval) clearInterval(sliderInterval);
        });
        
        slider.addEventListener('mouseleave', function() {
            sliderInterval = setInterval(nextSlide, 6000);
        });
    }
    
    // Initialize indicators
    updateIndicators();
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
function initNavbarScroll() {
    const navbar = document.getElementById('mainNavbar');
    if (!navbar) return;
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    }, { passive: true });
    
    // Set initial state
    if (window.pageYOffset > 50) {
        navbar.classList.add('scrolled');
    }
}

// Hero Slider Indicators
function initHeroIndicators() {
    const indicators = document.querySelectorAll('.hero-indicator');
    
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', function() {
            const slideIndex = parseInt(this.getAttribute('data-slide'));
            if (window.heroSliderGoTo) {
                window.heroSliderGoTo(slideIndex);
            }
        });
    });
}

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

