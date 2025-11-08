// Profile update specific functionality
// This is a minimal file to ensure profile updates work correctly

document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile update handler loaded');
    
    // Get the profile form
    const profileForm = document.getElementById('profile-form');
    
    if (profileForm) {
        console.log('Profile form found in dedicated handler');
        
        // Create a new submit handler
        profileForm.addEventListener('submit', function(event) {
            console.log('Form submit intercepted by dedicated handler');
            
            // Check if this is a profile update
            const submitButton = document.activeElement;
            if (submitButton && submitButton.name === 'action' && submitButton.value === 'update_profile') {
                console.log('Profile update action detected');
                
                // Let the form submit naturally
                // We're just adding this event listener to monitor the submission
                const formData = new FormData(profileForm);
                console.log('Form data being submitted:');
                for (let pair of formData.entries()) {
                    console.log(pair[0] + ': ' + pair[1]);
                }
            }
        });
        
        // Also add a click handler to the save button just to be sure
        const saveButton = profileForm.querySelector('button[value="update_profile"]');
        if (saveButton) {
            saveButton.addEventListener('click', function() {
                console.log('Save button clicked in dedicated handler');
            });
        }
    } else {
        console.error('Profile form not found in dedicated handler');
    }
}); 