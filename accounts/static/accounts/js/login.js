// Login page specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Login page JS loaded');
    
    // Handle form validation
    setupLoginFormValidation();
    
    // Add animation to the form
    animateLoginForm();
    
    // Handle forgot password link
    setupForgotPasswordLink();
});

// Function to set up form validation
function setupLoginFormValidation() {
    const loginForm = document.querySelector('.login-form');
    
    if (!loginForm) return;
    
    const emailInput = loginForm.querySelector('input[type="email"]');
    const passwordInput = loginForm.querySelector('input[type="password"]');
    
    // Real-time validation for email format
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            validateEmail(emailInput);
        });
    }
    
    // Ensure password is not empty
    if (passwordInput) {
        passwordInput.addEventListener('blur', function() {
            validatePassword(passwordInput);
        });
    }
    
    // Form submission validation
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Validate email
            if (emailInput && !validateEmail(emailInput)) {
                isValid = false;
            }
            
            // Validate password
            if (passwordInput && !validatePassword(passwordInput)) {
                isValid = false;
            }
            
            if (!isValid) {
                e.preventDefault();
                console.log('Form validation failed');
            }
        });
    }
}

// Email validation function
function validateEmail(emailInput) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const isValid = emailRegex.test(emailInput.value);
    
    if (!isValid && emailInput.value) {
        emailInput.classList.add('is-invalid');
        // Find or create error message
        let errorDiv = emailInput.parentNode.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            emailInput.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = 'Please enter a valid email address';
    } else {
        emailInput.classList.remove('is-invalid');
        const errorDiv = emailInput.parentNode.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.textContent = '';
        }
    }
    
    return isValid;
}

// Password validation function (just checks if it's not empty)
function validatePassword(passwordInput) {
    const isValid = passwordInput.value.length > 0;
    
    if (!isValid) {
        passwordInput.classList.add('is-invalid');
        // Find or create error message
        let errorDiv = passwordInput.parentNode.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            passwordInput.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = 'Password cannot be empty';
    } else {
        passwordInput.classList.remove('is-invalid');
        const errorDiv = passwordInput.parentNode.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.textContent = '';
        }
    }
    
    return isValid;
}

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