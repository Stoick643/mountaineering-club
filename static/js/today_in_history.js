/**
 * Today in History Widget JavaScript
 * Handles loading and displaying historical events
 */

// Global state
let currentEvent = null;
let isLoading = false;

// Widget state management
const HistoryWidget = {
    
    // Show different widget states
    showLoading() {
        document.getElementById('history-loading').style.display = 'block';
        document.getElementById('history-content').style.display = 'none';
        document.getElementById('history-error').style.display = 'none';
        document.getElementById('history-empty').style.display = 'none';
    },
    
    showContent() {
        document.getElementById('history-loading').style.display = 'none';
        document.getElementById('history-content').style.display = 'block';
        document.getElementById('history-error').style.display = 'none';
        document.getElementById('history-empty').style.display = 'none';
    },
    
    showError() {
        document.getElementById('history-loading').style.display = 'none';
        document.getElementById('history-content').style.display = 'none';
        document.getElementById('history-error').style.display = 'block';
        document.getElementById('history-empty').style.display = 'none';
    },
    
    showEmpty() {
        document.getElementById('history-loading').style.display = 'none';
        document.getElementById('history-content').style.display = 'none';
        document.getElementById('history-error').style.display = 'none';
        document.getElementById('history-empty').style.display = 'block';
    },
    
    // Populate widget with event data
    populateEvent(event) {
        currentEvent = event;
        
        // Basic event info
        document.getElementById('event-year').textContent = event.year || '?';
        document.getElementById('event-title').textContent = event.title || 'Neznan dogodek';
        document.getElementById('event-description').textContent = event.description || 'Opis ni na voljo';
        document.getElementById('event-location').textContent = event.location || 'Neznana lokacija';
        
        // Event category badge
        const categoryElement = document.getElementById('event-category');
        const categoryInfo = EVENT_CATEGORIES[event.category] || { label: 'Splošno', class: 'bg-secondary' };
        categoryElement.textContent = categoryInfo.label;
        categoryElement.className = `badge ${categoryInfo.class}`;
        
        // People involved (optional)
        const peopleContainer = document.getElementById('event-people-container');
        const peopleElement = document.getElementById('event-people');
        if (event.people && event.people.length > 0) {
            peopleElement.textContent = event.people.join(', ');
            peopleContainer.style.display = 'block';
        } else {
            peopleContainer.style.display = 'none';
        }
        
        // Source information (optional)
        const sourceContainer = document.getElementById('event-source-container');
        const sourceElement = document.getElementById('event-source');
        if (event.source && event.source !== 'unknown') {
            const sourceLabels = {
                'AI-generated': 'Ustvarjeno z AI',
                'historical': 'Zgodovinski vir',
                'fallback': 'Privzeto'
            };
            sourceElement.textContent = sourceLabels[event.source] || event.source;
            sourceContainer.style.display = 'block';
        } else {
            sourceContainer.style.display = 'none';
        }
        
        // Show content with animation
        this.showContent();
        document.getElementById('history-content').classList.add('fade-in');
        
        // Update like count if available
        const likeCount = document.getElementById('like-count');
        likeCount.textContent = event.like_count || '0';
    }
};

// API calls
async function fetchTodayEvent() {
    try {
        isLoading = true;
        HistoryWidget.showLoading();
        
        const response = await fetch('/api/today-in-history');
        const data = await response.json();
        
        if (data.success && data.event) {
            HistoryWidget.populateEvent(data.event);
            console.log('✅ Loaded today\'s historical event:', data.event.title);
        } else {
            console.warn('⚠️ No event found for today');
            HistoryWidget.showEmpty();
        }
        
    } catch (error) {
        console.error('❌ Error fetching today\'s event:', error);
        HistoryWidget.showError();
    } finally {
        isLoading = false;
    }
}

async function fetchEventByDate(date) {
    try {
        isLoading = true;
        HistoryWidget.showLoading();
        
        const response = await fetch(`/api/history/${date}`);
        const data = await response.json();
        
        if (data.success && data.event) {
            HistoryWidget.populateEvent(data.event);
            console.log(`✅ Loaded event for ${date}:`, data.event.title);
        } else {
            console.warn(`⚠️ No event found for ${date}`);
            HistoryWidget.showEmpty();
        }
        
    } catch (error) {
        console.error(`❌ Error fetching event for ${date}:`, error);
        HistoryWidget.showError();
    } finally {
        isLoading = false;
    }
}

async function fetchRandomEvent() {
    try {
        isLoading = true;
        HistoryWidget.showLoading();
        
        const response = await fetch('/api/history/random');
        const data = await response.json();
        
        if (data.success && data.event) {
            HistoryWidget.populateEvent(data.event);
            console.log('✅ Loaded random historical event:', data.event.title);
        } else {
            console.warn('⚠️ No random event found');
            HistoryWidget.showEmpty();
        }
        
    } catch (error) {
        console.error('❌ Error fetching random event:', error);
        HistoryWidget.showError();
    } finally {
        isLoading = false;
    }
}

// Widget action functions
function refreshTodayEvent() {
    if (isLoading) return;
    
    // Add spin animation to refresh icon
    const refreshIcon = document.getElementById('refresh-icon');
    refreshIcon.classList.add('fa-spin');
    
    // Remove spin after animation completes
    setTimeout(() => {
        refreshIcon.classList.remove('fa-spin');
    }, 1000);
    
    fetchTodayEvent();
}

function getRandomEvent() {
    if (isLoading) return;
    fetchRandomEvent();
}

function shareEvent() {
    if (!currentEvent) return;
    
    const shareText = `${currentEvent.year} - ${currentEvent.title}\n\n${currentEvent.description}\n\nVir: Planinsko društvo`;
    
    if (navigator.share) {
        // Use native sharing if available
        navigator.share({
            title: `Na današnji dan - ${currentEvent.title}`,
            text: shareText,
            url: window.location.href
        }).catch(err => console.log('Error sharing:', err));
    } else {
        // Fallback to clipboard
        navigator.clipboard.writeText(shareText).then(() => {
            showToast('Dogodek kopiran v odložišče!', 'success');
        }).catch(() => {
            // Final fallback - show modal with text to copy
            showShareModal(shareText);
        });
    }
}

function viewMoreHistory() {
    // Navigate to dedicated history page (future feature)
    window.location.href = '/history';
}

function likeEvent() {
    if (!currentEvent) return;
    
    // Animate like button
    const likeButton = document.querySelector('.event-feedback .btn');
    likeButton.classList.add('pulse');
    
    setTimeout(() => {
        likeButton.classList.remove('pulse');
    }, 600);
    
    // Update like count (local only for now)
    const likeCount = document.getElementById('like-count');
    const currentCount = parseInt(likeCount.textContent) || 0;
    likeCount.textContent = currentCount + 1;
    
    // TODO: Send like to server
    console.log('👍 Liked event:', currentEvent.title);
}

// Utility functions
function showToast(message, type = 'info') {
    // Create simple toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : 'info'} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 3000);
}

function showShareModal(text) {
    // Simple modal for sharing text
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Deli dogodek</h5>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <textarea class="form-control" rows="6" readonly>${text}</textarea>
                    <p class="mt-2 text-muted">Kopiraj besedilo zgoraj za deljenje.</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Zapri</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Select text for easy copying
    const textarea = modal.querySelector('textarea');
    textarea.select();
}

// Date navigation (future enhancement)
function navigateToDate(direction) {
    // direction: 'prev' or 'next'
    // TODO: Implement date navigation
    console.log(`Navigate ${direction} day`);
}

// Initialize widget when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏔️ Initializing Today in History widget...');
    
    // Load today's event
    fetchTodayEvent();
    
    // Set up periodic refresh (every 6 hours)
    setInterval(fetchTodayEvent, 6 * 60 * 60 * 1000);
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 'r':
                e.preventDefault();
                refreshTodayEvent();
                break;
            case 'h':
                e.preventDefault();
                getRandomEvent();
                break;
        }
    }
});

// Export functions for global access
window.refreshTodayEvent = refreshTodayEvent;
window.getRandomEvent = getRandomEvent;
window.shareEvent = shareEvent;
window.viewMoreHistory = viewMoreHistory;
window.likeEvent = likeEvent;