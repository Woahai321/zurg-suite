// Make triggerAction globally available
window.triggerAction = async function(action) {
    const button = document.querySelector(`button[data-action="${action}"]`);
    if (!button || button.disabled) return;

    try {
        // Disable button and show loading state
        button.disabled = true;
        const content = button.querySelector('.button-content');
        const loading = button.querySelector('.button-loading');
        
        // Show loading spinner
        if (content && loading) {
            content.style.opacity = '0';
            loading.style.opacity = '1';
        }

        // Make the API call
        const response = await fetch(`/trigger/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        // Handle the response
        if (result.success) {
            // Show success state
            button.classList.remove('bg-purple-600', 'hover:bg-purple-700');
            button.classList.add('bg-green-600', 'hover:bg-green-700');
            if (content) {
                content.innerHTML = `
                    <span>Success</span>
                    <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                `;
                content.style.opacity = '1';
            }
            if (loading) {
                loading.style.opacity = '0';
            }

            // Add success notification
            if (typeof addNotification === 'function') {
                addNotification(`${action.replace(/_/g, ' ')} completed successfully`, 'success');
            }

            // Reset to original state after 2 seconds
            setTimeout(() => {
                button.classList.remove('bg-green-600', 'hover:bg-green-700');
                button.classList.add('bg-purple-600', 'hover:bg-purple-700');
                if (content) {
                    const originalContent = `
                        <span>${button.getAttribute('data-original-text') || 'Trigger'}</span>
                        <svg class="w-5 h-5 ml-2 transform group-hover:translate-x-1 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                    `;
                    content.innerHTML = originalContent;
                }
                button.disabled = false;
            }, 2000);
        } else {
            // Show error state
            button.classList.remove('bg-purple-600', 'hover:bg-purple-700');
            button.classList.add('bg-red-600', 'hover:bg-red-700');
            if (content) {
                content.innerHTML = `
                    <span>Failed</span>
                    <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                `;
                content.style.opacity = '1';
            }
            if (loading) {
                loading.style.opacity = '0';
            }

            // Add error notification
            if (typeof addNotification === 'function') {
                addNotification(result.error || 'Action failed', 'error');
            }

            // Reset to original state after 2 seconds
            setTimeout(() => {
                button.classList.remove('bg-red-600', 'hover:bg-red-700');
                button.classList.add('bg-purple-600', 'hover:bg-purple-700');
                if (content) {
                    const originalContent = `
                        <span>${button.getAttribute('data-original-text') || 'Trigger'}</span>
                        <svg class="w-5 h-5 ml-2 transform group-hover:translate-x-1 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                    `;
                    content.innerHTML = originalContent;
                }
                button.disabled = false;
            }, 2000);
        }
    } catch (error) {
        console.error('Error:', error);
        // Show error state
        button.classList.remove('bg-purple-600', 'hover:bg-purple-700');
        button.classList.add('bg-red-600', 'hover:bg-red-700');
        if (content) {
            content.innerHTML = `
                <span>Error</span>
                <svg class="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            `;
            content.style.opacity = '1';
        }
        if (loading) {
            loading.style.opacity = '0';
        }

        // Add error notification
        if (typeof addNotification === 'function') {
            addNotification(`Error: ${error.message}`, 'error');
        }

        // Reset to original state after 2 seconds
        setTimeout(() => {
            button.classList.remove('bg-red-600', 'hover:bg-red-700');
            button.classList.add('bg-purple-600', 'hover:bg-purple-700');
            if (content) {
                const originalContent = `
                    <span>${button.getAttribute('data-original-text') || 'Trigger'}</span>
                    <svg class="w-5 h-5 ml-2 transform group-hover:translate-x-1 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                `;
                content.innerHTML = originalContent;
            }
            button.disabled = false;
        }, 2000);
    }
}

// Store original button text when page loads
document.addEventListener('DOMContentLoaded', function() {
    const actionButtons = document.querySelectorAll('.action-button');
    actionButtons.forEach(button => {
        const textElement = button.querySelector('.button-content span');
        if (textElement) {
            button.setAttribute('data-original-text', textElement.textContent);
        }
    });
}); 