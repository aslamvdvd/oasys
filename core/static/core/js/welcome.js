// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Welcome to OASYS!');
    
    // Add event listeners to buttons
    const loginButton = document.querySelector('.btn-login');
    const signupButton = document.querySelector('.btn-signup');
    
    if (loginButton) {
        loginButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Login button clicked');
            // Future functionality: Redirect to login page or show login modal
        });
    }
    
    if (signupButton) {
        signupButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Sign up button clicked');
            // Future functionality: Redirect to signup page or show signup modal
        });
    }
    
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
}); 