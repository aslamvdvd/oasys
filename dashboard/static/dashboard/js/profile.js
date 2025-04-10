// Profile page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile page loaded');
    
    // Profile image upload functionality
    setupImageUpload();
    
    // Form validation and submit handling
    setupFormValidation();
    
    // Change password functionality
    setupPasswordChange();
    
    // Delete account functionality
    setupDeleteAccount();
});

// Function to handle profile image uploads
function setupImageUpload() {
    const uploadButton = document.querySelector('.btn-upload-image');
    
    if (uploadButton) {
        uploadButton.addEventListener('click', function() {
            // Create a hidden file input
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
            
            // Trigger click on the file input
            fileInput.click();
            
            // Handle file selection
            fileInput.addEventListener('change', function() {
                if (this.files && this.files[0]) {
                    // In a real implementation, this would upload the file to the server
                    // For now, we'll just display a message
                    alert('Image selected: ' + this.files[0].name + '\nThis functionality will be implemented in a future update.');
                    
                    // Preview the image
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const profileImage = document.querySelector('.profile-image');
                        
                        // If there's a placeholder, replace it with an img element
                        if (profileImage.querySelector('.profile-placeholder')) {
                            profileImage.innerHTML = '<img src="' + e.target.result + '" alt="Profile Image">';
                        } else {
                            // Otherwise update the existing img
                            profileImage.querySelector('img').src = e.target.result;
                        }
                    };
                    reader.readAsDataURL(this.files[0]);
                }
                
                // Clean up
                document.body.removeChild(fileInput);
            });
        });
    }
}

// Function to handle form validation and submission
function setupFormValidation() {
    const profileForm = document.querySelector('.profile-form form');
    
    if (profileForm) {
        profileForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Simple validation
            const firstName = document.getElementById('first_name').value.trim();
            const lastName = document.getElementById('last_name').value.trim();
            
            if (!firstName || !lastName) {
                alert('First name and last name are required.');
                return;
            }
            
            // In a real implementation, this would submit the form to the server
            // For now, we'll just display a message
            alert('Profile updated successfully!\nThis functionality will be fully implemented in a future update.');
        });
    }
}

// Function to handle password change
function setupPasswordChange() {
    const passwordButton = document.querySelector('.btn-change-password');
    
    if (passwordButton) {
        passwordButton.addEventListener('click', function() {
            // In a real implementation, this would redirect to a password change page
            // or open a modal dialog
            alert('Password change functionality will be implemented in a future update.');
        });
    }
}

// Function to handle account deletion
function setupDeleteAccount() {
    const deleteButton = document.querySelector('.btn-danger');
    
    if (deleteButton) {
        deleteButton.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
                // In a real implementation, this would send a request to delete the account
                alert('Account deletion functionality will be implemented in a future update.');
            }
        });
    }
} 