// Login page specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Login page JS loaded');
    
    // Add animation to the form
    animateLoginForm();
    
    // Handle forgot password link
    setupForgotPasswordLink();
});

// Animate login form elements
function animateLoginForm() {
    const formElements = document.querySelectorAll('.login-form .form-row, .auth-links p');
    
    formElements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        
        setTimeout(() => {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, 100 + (index * 100));
    });
}

// Handle forgot password link
function setupForgotPasswordLink() {
    const forgotPasswordLink = document.querySelector('.forgot-password-link');
    
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', function(e) {
            e.preventDefault();
            alert('Password reset functionality will be implemented in a future update.');
        });
    }
} 