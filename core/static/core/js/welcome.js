// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Welcome to OASYS!');
    
    // Add a simple animation for the welcome content
    const welcomeContent = document.querySelector('.welcome-content');
    if (welcomeContent) {
        welcomeContent.style.opacity = '0';
        welcomeContent.style.transform = 'translateY(20px)';
        
        // Trigger animation after a small delay
        setTimeout(function() {
            welcomeContent.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
            welcomeContent.style.opacity = '1';
            welcomeContent.style.transform = 'translateY(0)';
        }, 200);
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
}); 