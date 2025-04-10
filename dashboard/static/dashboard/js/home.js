// Dashboard Home Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard home page loaded');
    
    // Example: Dynamically load spaces when we have them
    // This would be replaced with an actual API call in a real implementation
    loadUserSpaces();
    
    // Add animation to welcome message
    animateWelcomeSection();
});

// Function to load user spaces
function loadUserSpaces() {
    // This is a placeholder for demonstration
    // In a real app, this would fetch data from an API endpoint
    
    const spacesData = []; // Empty array representing no spaces
    
    // Check if user has spaces
    if (spacesData.length > 0) {
        // Hide empty state and show spaces
        document.querySelector('.empty-spaces').style.display = 'none';
        const spacesList = document.querySelector('.spaces-list');
        spacesList.style.display = 'grid';
        
        // Render spaces
        spacesData.forEach(space => {
            const spaceCard = createSpaceCard(space);
            spacesList.appendChild(spaceCard);
        });
    } else {
        // Show empty state (already visible by default)
        console.log('No spaces to display');
    }
}

// Function to create a space card element
function createSpaceCard(space) {
    // This function would create a DOM element for a space
    // For demonstration purposes only
    const card = document.createElement('div');
    card.className = 'space-card';
    
    // This is just a template - in a real app the space object
    // would contain actual data
    card.innerHTML = `
        <h4 class="space-title">${space.name}</h4>
        <p class="space-description">${space.description}</p>
        <div class="space-footer">
            <span class="space-members">${space.memberCount} members</span>
            <a href="/spaces/${space.id}/" class="btn btn-small btn-manage">Manage</a>
        </div>
    `;
    
    return card;
}

// Function to animate the welcome section
function animateWelcomeSection() {
    const welcomeSection = document.querySelector('.welcome-section');
    if (welcomeSection) {
        welcomeSection.style.opacity = '0';
        welcomeSection.style.transform = 'translateY(10px)';
        
        // Trigger animation after a small delay
        setTimeout(function() {
            welcomeSection.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
            welcomeSection.style.opacity = '1';
            welcomeSection.style.transform = 'translateY(0)';
        }, 100);
    }
} 