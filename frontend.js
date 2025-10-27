const config = {
    apiBaseUrl: '/api.php?path=',
    maxRetries: 3,
    retryDelay: 1000
};

// Utility functions
const utils = {
    formatDateTime: (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('nl-NL', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    showError: (message, isWarning = false) => {
        const statusDiv = document.getElementById('status');
        statusDiv.innerHTML = `
            <div class="alert ${isWarning ? 'alert-warning' : 'alert-error'}">
                ${message}
            </div>
        `;
        console.error('ERROR:', message);
    },

    showSuccess: (message) => {
        const statusDiv = document.getElementById('status');
        statusDiv.innerHTML = `
            <div class="alert alert-success">
                ${message}
            </div>
        `;
        console.log('SUCCESS:', message);
    }
};

// API communication
const api = {
    async request(endpoint, options = {}) {
        const { method = 'GET', body = null, retryCount = 0 } = options;

        try {
            console.log('🔍 API Request Details:');
            console.log('  - Endpoint:', endpoint);
            console.log('  - Method:', method);
            console.log('  - Body:', body);
            console.log('  - Full URL:', `${config.apiBaseUrl}${endpoint}`);

            const fetchOptions = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            if (body) {
                fetchOptions.body = JSON.stringify(body);
                console.log('  - JSON Body:', JSON.stringify(body));
            }

            const response = await fetch(`${config.apiBaseUrl}${endpoint}`, fetchOptions);
            
            console.log('📡 Response Status:', response.status, response.statusText);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ API Response Data:', data);
            return data;

        } catch (error) {
            console.error(`❌ API Error (attempt ${retryCount + 1}):`, error);

            if (retryCount < config.maxRetries) {
                console.log(`🔄 Retrying in ${config.retryDelay}ms...`);
                await new Promise(resolve => setTimeout(resolve, config.retryDelay));
                return this.request(endpoint, { ...options, retryCount: retryCount + 1 });
            }

            throw error;
        }
    },

    async checkStatus() {
        return await this.request('status');
    },

    async getEntries() {
        return await this.request('api/entries');
    },

    async addEntry(data) {
        return await this.request('api/submit_callsign', {
            method: 'POST',
            body: data
        });
    },

    async deleteEntry(position) {
        return await this.request(`api/admin/delete/${position}`, {
            method: 'POST'
        });
    }
};

// SocketIO verbinding opzetten
const socket = io('http://.......136:5000');
socket.on('connect', () => {
    console.log('✅ SocketIO connected');
});
socket.on('entries_updated', () => {
    console.log('🔄 Entries updated, reloading...');
    app.loadEntries();
});

// UI Management
const ui = {
    updateServerStatus: (status) => {
        const statusElement = document.getElementById('serverStatus');
        const isOnline = status && status.status === 'running';

        statusElement.className = `server-status ${isOnline ? 'online' : 'offline'}`;
        statusElement.textContent = isOnline ? 'Server Online' : 'Server Offline';

        if (isOnline) {
            const info = `v${status.version} | Entries: ${status.entries_count} | ${utils.formatDateTime(status.timestamp)} UTC`;
            document.getElementById('serverInfo').textContent = info;
        } else {
            document.getElementById('serverInfo').textContent = 'No connection';
        }
    },

    renderConfig: (config) => {
        const configDiv = document.getElementById('configInfo');
        if (!configDiv) return;
        if (!config) {
            configDiv.innerHTML = '';
            return;
        }
        configDiv.innerHTML = `
            <div class="config-info">
                <strong>Operator:</strong> ${config.operator_name} <br>
                <strong>Frequency:</strong> ${config.frequency}
            </div>
        `;
    },

    renderEntries: (entries) => {
        console.log('🎨 Rendering entries:', entries);
        const container = document.getElementById('entriesContainer');
        let entriesArray = [];

        if (entries && typeof entries === 'object') {
            console.log('📋 Processing entries object...');
            entriesArray = Object.entries(entries)
                .filter(([position, callsign]) => {
                    const hasValue = callsign && callsign !== null && callsign !== '';
                    console.log(`  Position ${position}: "${callsign}" (has value: ${hasValue})`);
                    return hasValue;
                })
                .map(([position, callsign]) => ({
                    position: position,
                    callsign: callsign
                }));
        }

        console.log('📊 Final entries array:', entriesArray);

        if (!entriesArray.length) {
            container.innerHTML = '<p class="no-entries">Geen entries gevonden</p>';
            console.log('📭 No entries to display');
            return;
        }

        const entriesHtml = entriesArray.map(entry => `
            <div class="entry-card" data-id="${entry.position}">
                <div class="entry-header">
                    <span class="entry-timestamp">${entry.position}</span>
                    ${window.isAdmin ? `
                        <button class="delete-btn" onclick="app.deleteEntry('${entry.position}')" title="Verwijder entry">
                            ✕
                        </button>
                    ` : ''}
                </div>
                <div class="entry-content">
                    <p><strong>Callsign:</strong> ${entry.callsign}</p>
                </div>
            </div>
        `).join('');

        container.innerHTML = `<div class="entries-grid">${entriesHtml}</div>`;
        console.log('✅ Entries rendered to DOM');
    },

    clearForm: () => {
        document.getElementById('entryForm').reset();
        console.log('🧹 Form cleared');
    },

    updateLastRefresh: () => {
        const now = new Date();
        const el = document.getElementById('lastUpdate');
        if (el) {
            el.textContent = `Laatste update: ${now.toLocaleTimeString('nl-NL')}`;
        }
    }
};

// Main application
const app = {
    async init() {
        console.log('🚀 PUCS Application Starting...');

        window.isAdmin = false;

        const form = document.getElementById('entryForm');
        form.addEventListener('submit', (e) => this.handleFormSubmit(e));

        const refreshBtn = document.getElementById('refreshBtn');
        refreshBtn.addEventListener('click', () => this.loadEntries());

        await this.checkServerConnection();
        await this.loadEntries();

        // 🔄 Auto-refresh elke 10 seconden
        setInterval(() => {
            this.loadEntries();
        }, 10000);

        console.log('✅ PUCS Application Ready');
    },

    async checkServerConnection() {
        try {
            console.log('🔌 Checking server connection...');
            utils.showSuccess('Checking connection...');
            const status = await api.checkStatus();
            ui.updateServerStatus(status);
            utils.showSuccess('Connected to server');
        } catch (error) {
            console.error('❌ Server connection failed:', error);
            ui.updateServerStatus(null);
            utils.showError(`Error connecting to server: ${error.message}`);
        }
    },

    async loadEntries() {
        try {
            console.log('📥 Loading entries...');
            const response = await api.getEntries();
            console.log('📦 Full API response:', response);
            
            let entries = response.entries;
            let entryCount = 0;

            if (entries && typeof entries === 'object') {
                entryCount = Object.values(entries).filter(cs => cs !== null && cs !== '').length;
                console.log(`📊 Entry count: ${entryCount}`);
            }

            ui.renderConfig(response.config);
            ui.renderEntries(entries);
            utils.showSuccess(`${entryCount} entries loaded`);
            ui.updateLastRefresh();
        } catch (error) {
            console.error('❌ Failed to load entries:', error);
            utils.showError(`Failed to load entries: ${error.message}`);
            ui.renderEntries({});
        }
    },

    async handleFormSubmit(event) {
        event.preventDefault();
        console.log('📝 Form submitted');

        const formData = new FormData(event.target);
        const data = {
            callsign: formData.get('name') || '',
            location: formData.get('location') || '',
            comment: formData.get('comment') || ''
        };

        console.log('📄 Form data:', data);

        if (!data.callsign.trim()) {
            utils.showError('Callsign is minimum input requirement', true);
            return;
        }

        try {
            utils.showSuccess('Entry accepted...');
            console.log('📤 Submitting entry...');
            
            const result = await api.addEntry(data);
            console.log('✅ Submit result:', result);
            
            ui.clearForm();
            
            console.log('🔄 Reloading entries...');
            await this.loadEntries();
            
            utils.showSuccess('Entry accepted!');
        } catch (error) {
            console.error('❌ Failed to add entry:', error);
            utils.showError(`Failed to add entry: ${error.message}`);
        }
    },

    async deleteEntry(position) {
        if (!window.isAdmin) return;

        if (!confirm('Are you sure you want to remove this entry?')) {
            return;
        }

        try {
            utils.showSuccess('Entry will be removed...');
            await api.deleteEntry(position);
            await this.loadEntries();
            utils.showSuccess('Entry removed!');
        } catch (error) {
            console.error('Failed to delete entry:', error);
            utils.showError(`Failed to delete entry: ${error.message}`);
        }
    },

    showAdmin() {
        const password = prompt('Admin password:');
        if (!password) return;

        if (password === '<password>') {
            window.isAdmin = true;
            utils.showSuccess('Admin modus activated');
            this.loadEntries();
        } else {
            window.isAdmin = false;
            utils.showError('INvlaid password for admin');
            this.loadEntries();
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init().catch(error => {
        console.error('❌ Failed to initialize application:', error);
        utils.showError(`Failed to initialize application: ${error.message}`);
    });
});