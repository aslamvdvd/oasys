// Base Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
    // Remove any duplicate active classes from navigation links
    // Only one link should have the active class
    const navLinks = document.querySelectorAll('.nav-link');
    const activeLinks = document.querySelectorAll('.nav-link.active');
    
    // If there's more than one active link, remove all active classes
    // and let the template-defined one remain
    if (activeLinks.length > 1) {
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        // The template-defined active link will be re-applied
        const currentPath = window.location.pathname;
        navLinks.forEach(link => {
            const linkPath = link.getAttribute('href');
            if (linkPath === currentPath) {
                link.classList.add('active');
            }
        });
    }
    
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