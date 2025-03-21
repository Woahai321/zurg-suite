document.addEventListener('DOMContentLoaded', function() {
    const mobileNavTrigger = document.getElementById('mobile-nav-trigger');
    const mobileNav = document.getElementById('mobile-nav');
    const mobileNavOverlay = document.getElementById('mobile-nav-overlay');
    let isNavOpen = false;

    function toggleNav() {
        isNavOpen = !isNavOpen;
        
        if (isNavOpen) {
            // Open navigation
            mobileNav.classList.remove('-translate-x-full');
            mobileNavOverlay.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
            
            // Animate overlay
            requestAnimationFrame(() => {
                mobileNavOverlay.classList.add('bg-opacity-50');
                mobileNavOverlay.classList.remove('bg-opacity-0');
            });
        } else {
            // Close navigation
            mobileNav.classList.add('-translate-x-full');
            mobileNavOverlay.classList.add('bg-opacity-0');
            mobileNavOverlay.classList.remove('bg-opacity-50');
            document.body.classList.remove('overflow-hidden');
            
            // Hide overlay after animation
            setTimeout(() => {
                if (!isNavOpen) {
                    mobileNavOverlay.classList.add('hidden');
                }
            }, 300);
        }
    }

    // Toggle nav when hamburger is clicked
    mobileNavTrigger?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleNav();
    });

    // Close nav when overlay is clicked
    mobileNavOverlay?.addEventListener('click', (e) => {
        e.preventDefault();
        if (isNavOpen) {
            toggleNav();
        }
    });

    // Close nav when escape key is pressed
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isNavOpen) {
            toggleNav();
        }
    });

    // Handle window resize for responsive behavior
    function handleWindowResize() {
        // If Alpine.js is loaded
        if (window.Alpine) {
            // Get the Alpine.js component data
            const alpine = document.querySelector('body').__x;
            if (alpine) {
                const isMobile = window.innerWidth < 769;
                
                // On desktop: always show sidebar
                // On mobile: keep current state (open or closed)
                if (!isMobile) {
                    alpine.$data.sidebarOpen = true;
                }
                
                // Update layout classes based on current width
                const mainContent = document.querySelector('.main-content');
                if (mainContent) {
                    if (isMobile) {
                        mainContent.classList.remove('md:ml-64');
                        mainContent.classList.add('ml-0');
                    } else {
                        mainContent.classList.add('md:ml-64');
                        mainContent.classList.remove('ml-0');
                    }
                }
            }
        }
    }

    // Run once on page load
    setTimeout(handleWindowResize, 100);

    // Add window resize listener with debounce
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(handleWindowResize, 100);
    });

    // Handle loading states for buttons
    const buttons = document.querySelectorAll('button[data-loading]');
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            if (!button.disabled) {
                button.disabled = true;
                button.classList.add('loading');
                
                // Show loading spinner
                const content = button.querySelector('.button-content');
                const loading = button.querySelector('.button-loading');
                if (content && loading) {
                    content.style.opacity = '0';
                    loading.style.opacity = '1';
                }

                // Reset after 2 seconds (adjust based on your actual API calls)
                setTimeout(() => {
                    button.disabled = false;
                    button.classList.remove('loading');
                    if (content && loading) {
                        content.style.opacity = '1';
                        loading.style.opacity = '0';
                    }
                }, 2000);
            }
        });
    });
}); 