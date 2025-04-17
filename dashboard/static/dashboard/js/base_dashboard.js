// Base Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
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
}); 