// Base Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
    // Set active class on navigation links based on current URL
    setActiveNavLink();
    
    // Auto-dismiss messages after 5 seconds
    const messages = document.querySelectorAll('.message');
    if (messages.length > 0) {
        setTimeout(function() {
            messages.forEach(function(message) {
                message.style.transition = 'opacity 0.5s ease';
                message.style.opacity = '0';
                
                // Remove the message from DOM after fade out
                setTimeout(function() {
                    message.remove();
                }, 500);
            });
        }, 5000);
    }
    
    // Initialize responsive menu for mobile
    setupResponsiveHeader();
});

// Function to set active class on the correct navigation link
function setActiveNavLink() {
    const navLinks = document.querySelectorAll('.nav-link');
    const currentPath = window.location.pathname;
    
    // First, remove all active classes
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // Then set active class only on the link that matches current path
    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentPath) {
            link.classList.add('active');
        }
    });
}

// Function to handle responsive header behavior
function setupResponsiveHeader() {
    // This would typically handle mobile menu toggle functionality
    // For a more complex implementation, a hamburger menu might be added
    
    // For demonstration purposes we'll just check the window width
    // and apply some basic adjustments
    function checkWidth() {
        if (window.innerWidth < 768) {
            console.log('Mobile view detected');
            // Mobile-specific behaviors could be added here
        } else {
            console.log('Desktop view detected');
            // Desktop-specific behaviors could be added here
        }
    }
    
    // Check on load
    checkWidth();
    
    // Check on resize
    window.addEventListener('resize', checkWidth);
} 