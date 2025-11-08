// Signup page specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Signup page JS loaded');
    
    // Set up password strength indicator listener
    setupPasswordStrengthListener();
    
    // Add animation to the form
    animateSignupForm();
});

// Function to set up relevant listeners (modified from setupSignupFormValidation)
function setupPasswordStrengthListener() {
    const signupForm = document.querySelector('.signup-form');
    if (!signupForm) return;
    
    const passwordInput = signupForm.querySelector('input[name="password1"]');
    
    // Password strength indicator feedback on input
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            displayPasswordStrength(passwordInput); // Changed function name for clarity
        });
    }
    
    // Removed email validation listener
    // Removed password match listener
    // Removed form submission validation listener (rely on server-side)
}

// Email validation function - REMOVED
/* ... */

// Password strength checker - MODIFIED to only display feedback
function displayPasswordStrength(passwordInput) {
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
        strengthIndicator.className = 'password-strength help-text'; // Use help-text class for styling
        // Insert after the input field or its help text if present
        let helpText = passwordInput.parentNode.querySelector('.help-text');
        if (helpText) {
             helpText.parentNode.insertBefore(strengthIndicator, helpText.nextSibling);
        } else { 
             passwordInput.parentNode.appendChild(strengthIndicator);
        }
    }
    
    // Update indicator based on strength
    if (password.length === 0) {
        strengthIndicator.textContent = ''; 
        strengthIndicator.style.color = 'inherit'; // Reset color
    } else if (strength < 3) {
        strengthIndicator.textContent = 'Weak';
        strengthIndicator.style.color = '#e74c3c'; // Red for weak
    } else if (strength < 5) { // Changed threshold slightly for medium/strong split
        strengthIndicator.textContent = 'Medium';
        strengthIndicator.style.color = '#f39c12'; // Orange for medium
    } else {
        strengthIndicator.textContent = 'Strong';
        strengthIndicator.style.color = '#27ae60'; // Green for strong
    }
    // REMOVED return true/false - no longer blocks submission
}

// Check if passwords match - REMOVED
/* ... */

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