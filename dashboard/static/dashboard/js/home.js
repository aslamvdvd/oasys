// Dashboard Home Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard home page loaded');
    
    // Add animation to welcome message
    animateWelcomeSection();
});

// Function to animate the welcome section
function animateWelcomeSection() {
    const welcomeSection = document.querySelector('.dashboard-welcome');
    if (welcomeSection) {
        welcomeSection.style.opacity = '0';
        welcomeSection.style.transform = 'translateY(10px)';
        
        // Trigger animation after a small delay
        setTimeout(function() {
            welcomeSection.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
            welcomeSection.style.opacity = '1';
            welcomeSection.style.transform = 'translateY(0)';
        }, 100);
    }
} 