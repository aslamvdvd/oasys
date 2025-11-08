// Create Space JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Create Space JS loaded');
    
    // Get the create space button
    const createSpaceBtn = document.getElementById('create-space-btn');
    
    if (createSpaceBtn) {
        // Add event listener to the create space button
        createSpaceBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Create Space button clicked');
            
            // In a real implementation, this would either:
            // 1. Redirect to a space creation page
            // window.location.href = '/spaces/create/';
            
            // 2. Or open a modal dialog to create a space
            showCreateSpaceModal();
        });
    }
});

// Function to simulate showing a modal for space creation
function showCreateSpaceModal() {
    // In a real implementation, this would create and show
    // a modal dialog with a form to create a new space
    
    // For demonstration purposes, we'll just create a simple alert
    alert('Create Space functionality would open a modal here.');
    
    // Alternatively, a more sophisticated approach would be to:
    // 1. Create a modal element
    // 2. Append it to the body
    // 3. Show the modal with a form
    // 4. Handle form submission
    
    /* Example of what this might look like:
    
    // Create modal container
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-btn">&times;</span>
            <h2>Create New Space</h2>
            <form id="create-space-form">
                <div class="form-group">
                    <label for="space-name">Space Name</label>
                    <input type="text" id="space-name" name="name" required>
                </div>
                <div class="form-group">
                    <label for="space-description">Description</label>
                    <textarea id="space-description" name="description" rows="4"></textarea>
                </div>
                <button type="submit" class="btn btn-create-space">Create Space</button>
            </form>
        </div>
    `;
    
    // Append to body
    document.body.appendChild(modal);
    
    // Add close functionality
    const closeBtn = modal.querySelector('.close-btn');
    closeBtn.addEventListener('click', function() {
        document.body.removeChild(modal);
    });
    
    // Add form submit handling
    const form = modal.querySelector('#create-space-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form data
        const spaceName = document.getElementById('space-name').value;
        const spaceDescription = document.getElementById('space-description').value;
        
        // Submit data via AJAX or similar
        console.log('Creating space:', spaceName, spaceDescription);
        
        // Close modal
        document.body.removeChild(modal);
    });
    */
} 