// Spaces page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Spaces page loaded');
    
    // Example: Dynamically load spaces when we have them
    // This would be replaced with an actual API call in a real implementation
    loadUserSpaces();
    
    // Add animation to spaces cards
    animateSpacesPage();
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
        spacesList.style.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))';
        spacesList.style.gap = '25px';
        
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

// Function to add animations to the spaces page
function animateSpacesPage() {
    // Add a fade-in animation to the spaces container
    const spacesContainer = document.querySelector('.spaces-container');
    if (spacesContainer) {
        spacesContainer.style.opacity = '0';
        spacesContainer.style.transform = 'translateY(10px)';
        spacesContainer.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
            spacesContainer.style.opacity = '1';
            spacesContainer.style.transform = 'translateY(0)';
        }, 100);
    }
    
    // Add hover effect to any space cards that might be added in the future
    document.addEventListener('mouseover', function(e) {
        if (e.target.closest('.space-card')) {
            const card = e.target.closest('.space-card');
            card.style.transform = 'translateY(-5px)';
            card.style.boxShadow = '0 8px 15px rgba(0, 0, 0, 0.1)';
        }
    });
    
    document.addEventListener('mouseout', function(e) {
        if (e.target.closest('.space-card')) {
            const card = e.target.closest('.space-card');
            card.style.transform = '';
            card.style.boxShadow = '';
        }
    });
} 