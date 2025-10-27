// Radio Entry System - Frontend JavaScript

// Global state
let isSubmitting = false;
let lastUpdateTime = new Date();

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeEntrySystem();
});

function initializeEntrySystem() {
    console.log('🎙️ Radio Entry System initialized');
    
    // Focus op input veld als deze bestaat
    const activeInput = document.querySelector('.callsign-input');
    if (activeInput) {
        activeInput.focus();
        setupInputHandlers(activeInput);
    }
    
    // Update last update time
    updateLastUpdateTime();
    
    // Setup auto-refresh
    setupAutoRefresh();
    
    // Setup admin features als we op admin pagina zijn
    if (window.location.pathname.includes('/admin')) {
        setupAdminFeatures();
    }
}

function setupInputHandlers(input) {
    // Keypress handlers
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const position = extractPositionFromInput(this);
            if (position) {
                submitCallsign(position);
            }
        }
    });
    
    // Input validation - alleen geldige karakters
    input.addEventListener('input', function(e) {
        // Maak automatisch uppercase
        this.value = this.value.toUpperCase();
        
        // Verwijder ongeldige karakters
        this.value = this.value.replace(/[^A-Z0-9\/\-]/g, '');
        
        // Max length check
        if (this.value.length > 20) {
            this.value = this.value.substring(0, 20);
        }
    });
    
    // Paste handler
    input.addEventListener('paste', function(e) {
        setTimeout(() => {
            this.value = this.value.toUpperCase().replace(/[^A-Z0-9\/\-]/g, '');
            if (this.value.length > 20) {
                this.value = this.value.substring(0, 20);
            }
        }, 10);
    });
}

function extractPositionFromInput(input) {
    const id = input.id;
    const match = id.match(/callsign-input-(\d+)/);
    return match ? parseInt(match[1]) : null;
}

function submitCallsign(position) {
    if (isSubmitting) {
        console.log('⏳ Submit already in progress');
        return;
    }
    
    const input = document.getElementById(`callsign-input-${position}`);
    const button = document.querySelector('.submit-btn');
    const callsign = input.value.trim().toUpperCase();
    
    // Validatie
    if (!callsign) {
        showError('Voer een callsign in!');
        input.focus();
        return;
    }
    
    if (!/^[A-Z0-9\/\-]+$/.test(callsign)) {
        showError('Ongeldige callsign! Gebruik alleen letters, cijfers, "/" en "-"');
        input.focus();
        return;
    }
    
    if (callsign.length < 3) {
        showError('Callsign te kort (minimum 3 karakters)');
        input.focus();
        return;
    }
    
    // UI feedback
    isSubmitting = true;
    const originalButtonText = button.textContent;
    button.disabled = true;
    button.textContent = 'BEZIG...';
    button.classList.add('submitting');
    input.disabled = true;
    
    console.log(`📡 Submitting callsign: ${callsign} voor positie ${position}`);
    
    // API call
    fetch('/api/submit_callsign', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            callsign: callsign
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`✅ Callsign ${callsign} toegevoegd op positie ${data.position}`);
            showSuccess(`Callsign ${callsign} toegevoegd!`);
            
            // Refresh pagina na korte delay voor smooth UX
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error(data.error || 'Onbekende fout');
        }
    })
    .catch(error => {
        console.error('❌ Submit error:', error);
        showError(error.message || 'Netwerkfout - probeer opnieuw');
        
        // Reset UI
        isSubmitting = false;
        button.disabled = false;
        button.textContent = originalButtonText;
        button.classList.remove('submitting');
        input.disabled = false;
        input.focus();
    });
}

function showError(message) {
    console.log(`❌ Error: ${message}`);
    
    // Show browser alert als fallback
    alert(`❌ ${message}`);
    
    // Probeer toast notification als element bestaat
    showNotification(message, 'error');
}

function showSuccess(message) {
    console.log(`✅ Success: ${message}`);
    
    // Show browser alert als fallback  
    alert(`✅ ${message}`);
    
    // Probeer toast notification als element bestaat
    showNotification(message, 'success');
}

function showNotification(message, type = 'info') {
    // Maak tijdelijke notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#e74c3c' : type === 'success' ? '#27ae60' : '#3498db'};
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        z-index: 9999;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
    `;
    
    // Add CSS animation
    if (!document.getElementById('notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(styles);
    }
    
    document.body.appendChild(notification);
    
    // Auto remove
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 4000);
}

function updateLastUpdateTime() {
    const timeElement = document.getElementById('last-update-time');
    if (timeElement) {
        lastUpdateTime = new Date();
        timeElement.textContent = lastUpdateTime.toLocaleTimeString('nl-NL');
    }
}

function setupAutoRefresh() {
    // Auto-refresh elke 30 seconden (alleen als niet in admin)
    if (!window.location.pathname.includes('/admin')) {
        setInterval(() => {
            console.log('🔄 Auto-refresh pagina');
            window.location.reload();
        }, 30000);
    }
}

function setupAdminFeatures() {
    console.log('⚙️ Admin features initialized');
    
    // Confirmatie dialogen voor delete acties
    const deleteButtons = document.querySelectorAll('form[action*="delete_entry"]');
    deleteButtons.forEach(form => {
        form.addEventListener('submit', function(e) {
            const callsign = this.action.match(/position\/(\d+)/);
            const position = callsign ? callsign[1] : 'onbekend';
            
            if (!confirm(`Weet je zeker dat je de entry op positie ${position} wilt verwijderen?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Clear all confirmation
    const clearAllForm = document.querySelector('form[action*="clear_all"]');
    if (clearAllForm) {
        clearAllForm.addEventListener('submit', function(e) {
            if (!confirm('WAARSCHUWING: Dit verwijdert ALLE entries!\n\nWeet je het zeker?')) {
                e.preventDefault();
            }
        });
    }
    
    // Auto-refresh admin dashboard elke 30 seconden
    setTimeout(() => {
        window.location.reload();
    }, 30000);
}

// API Test functie voor admin
function testAPI() {
    const resultDiv = document.getElementById('api-result');
    if (!resultDiv) return;
    
    resultDiv.innerHTML = '⏳ Bezig met testen...';
    resultDiv.className = 'api-testing';
    
    fetch('/api/get_active_callsigns')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const callsigns = data.callsigns || [];
            resultDiv.innerHTML = `
                <div class="api-success">
                    ✅ API werkt! 
                    <br>Actieve callsigns: ${callsigns.length ? callsigns.join(', ') : 'Geen'}
                    <br>Test uitgevoerd: ${new Date().toLocaleTimeString('nl-NL')}
                </div>
            `;
        })
        .catch(error => {
            resultDiv.innerHTML = `
                <div class="api-error">
                    ❌ API fout: ${error.message}
                    <br>Test tijd: ${new Date().toLocaleTimeString('nl-NL')}
                </div>
            `;
        });
}

// Utility functies
function formatTime(date) {
    return date.toLocaleTimeString('nl-NL', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDate(date) {
    return date.toLocaleDateString('nl-NL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

// Export functies voor gebruik in templates
window.RadioEntrySystem = {
    submitCallsign,
    testAPI,
    showError,
    showSuccess,
    showNotification
};

console.log('📻 Radio Entry System JS loaded');