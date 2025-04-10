// Base Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentPath) {
            link.classList.add('active');
        } else if (linkPath !== '#' && currentPath.startsWith(linkPath)) {
            link.classList.add('active');
        }
    });
    
    // Handle logout button
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Logout clicked');
            // In a real implementation, this would navigate to the logout URL
            // window.location.href = '/logout/';
        });
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