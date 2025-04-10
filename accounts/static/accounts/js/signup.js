// Signup page specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Signup page JS loaded');
    
    // Handle form validation
    setupSignupFormValidation();
    
    // Add animation to the form
    animateSignupForm();
});

// Function to set up form validation
function setupSignupFormValidation() {
    const signupForm = document.querySelector('.signup-form');
    
    if (!signupForm) return;
    
    const emailInput = signupForm.querySelector('input[type="email"]');
    const passwordInput = signupForm.querySelector('input[name="password1"]');
    const passwordConfirmInput = signupForm.querySelector('input[name="password2"]');
    
    // Real-time validation for email format
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            validateEmail(emailInput);
        });
    }
    
    // Password strength indicator
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            checkPasswordStrength(passwordInput);
        });
    }
    
    // Password matching validation
    if (passwordInput && passwordConfirmInput) {
        passwordConfirmInput.addEventListener('input', function() {
            checkPasswordsMatch(passwordInput, passwordConfirmInput);
        });
    }
    
    // Form submission validation
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Validate email
            if (emailInput && !validateEmail(emailInput)) {
                isValid = false;
            }
            
            // Validate password strength
            if (passwordInput && !checkPasswordStrength(passwordInput)) {
                isValid = false;
            }
            
            // Check passwords match
            if (passwordInput && passwordConfirmInput && 
                !checkPasswordsMatch(passwordInput, passwordConfirmInput)) {
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

// Password strength checker
function checkPasswordStrength(passwordInput) {
    const password = passwordInput.value;
    let strength = 0;
    
    if (password.length >= 8) strength += 1;
    if (password.match(/[a-z]+/)) strength += 1;
    if (password.match(/[A-Z]+/)) strength += 1;
    if (password.match(/[0-9]+/)) strength += 1;
    if (password.match(/[^a-zA-Z0-9]+/)) strength += 1;
    
    // Find or create strength indicator
    let strengthIndicator = passwordInput.parentNode.querySelector('.password-strength');
    if (!strengthIndicator) {
        strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'password-strength help-text';
        passwordInput.parentNode.appendChild(strengthIndicator);
    }
    
    // Update indicator based on strength
    if (password.length === 0) {
        strengthIndicator.textContent = '';
        return true;
    } else if (strength < 3) {
        strengthIndicator.textContent = 'Weak password';
        strengthIndicator.style.color = '#e74c3c';
        return false;
    } else if (strength === 3) {
        strengthIndicator.textContent = 'Medium strength password';
        strengthIndicator.style.color = '#f39c12';
        return true;
    } else {
        strengthIndicator.textContent = 'Strong password';
        strengthIndicator.style.color = '#27ae60';
        return true;
    }
}

// Check if passwords match
function checkPasswordsMatch(passwordInput, passwordConfirmInput) {
    const passwordsMatch = passwordInput.value === passwordConfirmInput.value;
    
    if (!passwordsMatch && passwordConfirmInput.value) {
        passwordConfirmInput.classList.add('is-invalid');
        // Find or create error message
        let errorDiv = passwordConfirmInput.parentNode.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            passwordConfirmInput.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = 'Passwords do not match';
    } else {
        passwordConfirmInput.classList.remove('is-invalid');
        const errorDiv = passwordConfirmInput.parentNode.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.textContent = '';
        }
    }
    
    return passwordsMatch || !passwordConfirmInput.value;
}

// Animate signup form elements
function animateSignupForm() {
    const formElements = document.querySelectorAll('.signup-form .form-row');
    
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