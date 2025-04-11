// Profile page JavaScript - COMPLETELY REWRITTEN

document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile page JS loaded');
    
    // Clean up any existing event listeners
    clearAllEventListeners();
    
    // Setup account deletion functionality
    setupDeleteAccountModal();
    
    // Setup password change button - just a placeholder
    const passwordButton = document.querySelector('.btn-change-password');
    if (passwordButton) {
        passwordButton.addEventListener('click', function() {
            console.log('Password change requested - not implemented yet');
            // Removed alert - replace with subtle message
            const message = document.createElement('div');
            message.className = 'message info';
            message.textContent = 'Password change functionality will be implemented in a future update.';
            document.querySelector('.messages') ? 
                document.querySelector('.messages').appendChild(message) : 
                document.querySelector('.dashboard-content .container').prepend(message);
            
            // Auto-remove the message after 5 seconds
            setTimeout(() => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 500);
            }, 5000);
        });
    }
    
    // Setup profile image upload - just a placeholder
    const uploadButton = document.querySelector('.btn-upload-image');
    if (uploadButton) {
        uploadButton.addEventListener('click', function() {
            console.log('Image upload requested - not implemented yet');
            // Removed alert - replace with subtle message
            const message = document.createElement('div');
            message.className = 'message info';
            message.textContent = 'Image upload will be implemented in a future update.';
            document.querySelector('.messages') ? 
                document.querySelector('.messages').appendChild(message) : 
                document.querySelector('.dashboard-content .container').prepend(message);
            
            // Auto-remove the message after 5 seconds
            setTimeout(() => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 500);
            }, 5000);
        });
    }
    
    // Remove any duplicate delete account UI
    removeDuplicateDeleteUI();
});

// Function to remove all existing event listeners by replacing elements
function clearAllEventListeners() {
    // Clear delete button event listeners
    const deleteButton = document.getElementById('delete-account-btn');
    if (deleteButton) {
        const newDeleteButton = deleteButton.cloneNode(true);
        deleteButton.parentNode.replaceChild(newDeleteButton, deleteButton);
        console.log('Cleared delete button event listeners');
    }
    
    // Clear all other buttons that might have alerts
    document.querySelectorAll('button').forEach(button => {
        if (button.textContent.includes('Delete Account') && button.id !== 'delete-account-btn') {
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
        }
    });
}

// Function to remove any duplicate delete account UI
function removeDuplicateDeleteUI() {
    // Look for any delete account sections outside the modal
    document.querySelectorAll('h3, div, button').forEach(el => {
        // Check if it's a heading or div with "Delete Account" text
        if (el.textContent.includes('Delete Account') && 
            !el.closest('#delete-account-modal') && 
            !el.closest('.account-actions') &&
            el.id !== 'delete-account-btn') {
            
            // Found a duplicate delete account section
            console.log('Found duplicate delete account section - removing');
            const section = el.closest('div');
            if (section && section.parentNode) {
                section.parentNode.removeChild(section);
            }
        }
    });
    
    // More aggressive approach - target the specific layout in the screenshot
    // Look for divs with "Delete Account" heading directly under main content
    document.querySelectorAll('.dashboard-content > .container > div').forEach(div => {
        if (div !== document.querySelector('.profile-container') && 
            (div.querySelector('h3') && div.querySelector('h3').textContent.includes('Delete Account'))) {
            console.log('Found another duplicate section - removing');
            div.parentNode.removeChild(div);
        }
    });
    
    // Most aggressive approach - look for elements at specific locations
    // Look for standalone Delete Account headings and buttons below the profile container
    const profileContainer = document.querySelector('.profile-container');
    if (profileContainer) {
        let next = profileContainer.nextElementSibling;
        while (next) {
            const current = next;
            next = current.nextElementSibling;
            
            // If this element has "Delete Account" text, remove it
            if (current.textContent.includes('Delete Account') || 
                current.textContent.includes('delete') || 
                current.textContent.includes('Delete')) {
                console.log('Found content below profile container - removing');
                current.parentNode.removeChild(current);
            }
        }
    }
}

// Function to handle the delete account modal
function setupDeleteAccountModal() {
    // Get fresh references to elements after clearing event listeners
    const deleteButton = document.getElementById('delete-account-btn');
    const deleteModal = document.getElementById('delete-account-modal');
    const closeButton = deleteModal.querySelector('.close');
    const confirmInput = document.getElementById('delete-confirmation');
    const confirmButton = document.getElementById('confirm-delete-btn');
    
    // Open modal when delete button is clicked
    if (deleteButton && deleteModal) {
        // Add the ONLY event listener for the delete button
        deleteButton.addEventListener('click', function(e) {
            // Stop any other event handlers
            e.stopPropagation();
            e.preventDefault();
            
            console.log('Delete button clicked - showing modal ONLY');
            
            // Show the modal
            deleteModal.classList.add('show');
            
            // Clear any previous confirmation text
            if (confirmInput) {
                confirmInput.value = '';
                confirmButton.disabled = true;
            }
            
            // Return false to prevent any default actions
            return false;
        });
    }
    
    // Close modal when close button is clicked
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            deleteModal.classList.remove('show');
            confirmInput.value = '';
        });
    }
    
    // Close modal when clicking outside of it
    window.addEventListener('click', function(event) {
        if (event.target === deleteModal) {
            deleteModal.classList.remove('show');
            confirmInput.value = '';
        }
    });
    
    // Enable/disable confirm button based on input value
    if (confirmInput && confirmButton) {
        confirmInput.addEventListener('input', function() {
            confirmButton.disabled = (this.value.toLowerCase() !== 'delete');
        });
    }
} 