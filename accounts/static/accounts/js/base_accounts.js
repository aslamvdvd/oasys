// Base JavaScript for accounts app

document.addEventListener('DOMContentLoaded', function() {
    console.log('Accounts app base JS loaded');
    
    // Setup messages auto-dismissal
    setupMessages();
    
    // Setup navigation active state - REMOVED as handled server-side
    // setActiveNavLink(); 
});

// Function to handle messages display and dismissal
function setupMessages() {
    const messages = document.querySelectorAll('.message');
    
    messages.forEach(message => {
        // Add close button
        const closeButton = document.createElement('span');
        closeButton.innerHTML = '&times;';
        closeButton.className = 'message-close';
        closeButton.style.cssText = 'float:right; cursor:pointer; font-size:20px; margin-left:10px; font-weight:bold;';
        
        message.insertBefore(closeButton, message.firstChild);
        
        // Close on click
        closeButton.addEventListener('click', function() {
            fadeOutMessage(message);
        });
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            fadeOutMessage(message);
        }, 5000);
    });
}

// Helper to fade out and remove messages
function fadeOutMessage(message) {
    message.style.transition = 'opacity 0.5s ease';
    message.style.opacity = '0';
    
    setTimeout(() => {
        message.style.display = 'none';
    }, 500);
}

// Function to set active class on the correct navigation link - REMOVED
/*
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
*/