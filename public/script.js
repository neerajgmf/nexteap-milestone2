// Initialize Supabase Client
// Note: These keys should be exposed in the frontend. 
// Ideally, we fetch them from an endpoint or inject them during build.
// For this prototype, we'll assume they are available or hardcoded for the demo if env vars aren't injected.
// Since we are running locally or on Vercel, we can try to use process.env if we were using a bundler.
// But this is vanilla JS.
// We will need to fetch the config or hardcode the public key.
// Let's fetch the config from a new endpoint or just hardcode the public key for now as it's safe to expose.
// Wait, I can't easily hardcode it without knowing it.
// I see the keys in .env file in the workspace.
// NEXT_PUBLIC_SUPABASE_URL=https://voiaanrfdzinxypwvzhs.supabase.co
// NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_kEcZSyvmAyPt2tP_zrKYnA_qLvJ-vWC

const SUPABASE_URL = 'https://voiaanrfdzinxypwvzhs.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_kEcZSyvmAyPt2tP_zrKYnA_qLvJ-vWC';

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// DOM Elements
const signInBtn = document.getElementById('sign-in-btn');
const signOutBtn = document.getElementById('sign-out-btn');
const authContainer = document.getElementById('auth-container');
const userProfile = document.getElementById('user-profile');
const userEmailSpan = document.getElementById('user-email');
const authModal = document.getElementById('auth-modal');
const closeModal = document.querySelector('.close');
const authForm = document.getElementById('auth-form');
const emailInput = document.getElementById('email-input');
const authStatus = document.getElementById('auth-status');
const appUrlInput = document.getElementById('app-url');
const analyzeBtn = document.getElementById('analyze-btn');
const authMessage = document.getElementById('auth-message');
const resultsSection = document.getElementById('results-section');
const loadingState = document.getElementById('loading-state');
const analysisContent = document.getElementById('analysis-content');
const reportBody = document.getElementById('report-body');

let currentUser = null;

// Event Listeners
signInBtn.addEventListener('click', () => {
    authModal.classList.remove('hidden');
});

closeModal.addEventListener('click', () => {
    authModal.classList.add('hidden');
});

window.addEventListener('click', (e) => {
    if (e.target === authModal) {
        authModal.classList.add('hidden');
    }
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = emailInput.value;
    authStatus.textContent = 'Sending magic link...';

    const { error } = await supabase.auth.signInWithOtp({ email });

    if (error) {
        authStatus.textContent = `Error: ${error.message}`;
        authStatus.style.color = '#ef4444';
    } else {
        authStatus.textContent = 'Check your email for the magic link!';
        authStatus.style.color = '#10b981';
        setTimeout(() => {
            authModal.classList.add('hidden');
            authStatus.textContent = '';
            emailInput.value = '';
        }, 3000);
    }
});

signOutBtn.addEventListener('click', async () => {
    await supabase.auth.signOut();
    updateAuthState(null);
});

analyzeBtn.addEventListener('click', async () => {
    const url = appUrlInput.value;
    if (!url) return;

    if (!currentUser) {
        alert('Please sign in first.');
        return;
    }

    // UI Updates
    resultsSection.classList.remove('hidden');
    loadingState.classList.remove('hidden');
    analysisContent.classList.add('hidden');
    analyzeBtn.disabled = true;

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                email: currentUser.email
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            renderAnalysis(data.data);
        } else {
            alert(`Error: ${data.message}`);
            resultsSection.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while analyzing.');
        resultsSection.classList.add('hidden');
    } finally {
        loadingState.classList.add('hidden');
        analyzeBtn.disabled = false;
    }
});

// Auth State Change
supabase.auth.onAuthStateChange((event, session) => {
    updateAuthState(session?.user || null);
});

function updateAuthState(user) {
    currentUser = user;
    if (user) {
        signInBtn.classList.add('hidden');
        userProfile.classList.remove('hidden');
        userEmailSpan.textContent = user.email;

        appUrlInput.disabled = false;
        analyzeBtn.disabled = false;
        authMessage.classList.add('hidden');
    } else {
        signInBtn.classList.remove('hidden');
        userProfile.classList.add('hidden');
        userEmailSpan.textContent = '';

        appUrlInput.disabled = true;
        analyzeBtn.disabled = true;
        authMessage.classList.remove('hidden');
    }
}

function renderAnalysis(data) {
    analysisContent.classList.remove('hidden');

    // Simple markdown to HTML conversion (very basic)
    // In a real app, use a library like marked.js
    // For now, we'll just replace newlines with <br> and headers

    let html = '';

    // Check if data is a string (markdown) or object
    let content = '';
    if (typeof data === 'string') {
        content = data;
    } else if (data.analysis) {
        content = data.analysis;
    } else {
        content = JSON.stringify(data, null, 2);
    }

    // Basic formatting
    html = content
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
        .replace(/\n/gim, '<br>');

    reportBody.innerHTML = html;
}

// Check initial session
supabase.auth.getSession().then(({ data: { session } }) => {
    updateAuthState(session?.user || null);
});
