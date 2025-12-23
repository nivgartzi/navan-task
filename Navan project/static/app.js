const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('nomad-message-input');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');

let chatHistory = [];

const INITIAL_MESSAGE = "Hello! I'm your Booking Hotels Assistant. I can help you find the perfect accommodations in any city. Where would you like to stay?";

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage('user', text);
    userInput.value = '';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, history: chatHistory })
        });

        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            throw new Error('Invalid response from server. Please try again.');
        }

        if (!response.ok) {
            throw new Error(data.detail || data.error || 'Server error');
        }

        let aiResponse = data.response;
        let claims = null;

        // Handle if response is JSON string
        try {
            const parsed = JSON.parse(aiResponse);
            if (parsed.response_to_user) {
                aiResponse = parsed.response_to_user;
                claims = parsed.claims;
                
                // Don't show hotel cards for thank you/goodbye messages
                const lowerResponse = aiResponse.toLowerCase();
                const isThankYouOrGoodbye = lowerResponse.includes('you\'re welcome') || 
                                          lowerResponse.includes('welcome') ||
                                          lowerResponse.includes('have a great') ||
                                          lowerResponse.includes('have a good') ||
                                          lowerResponse.includes('enjoy your') ||
                                          (lowerResponse.includes('thank') && lowerResponse.length < 100);
                
                if (isThankYouOrGoodbye && claims) {
                    // Clear hotel data to prevent showing cards
                    claims = { ...claims, top_hotels: [], hotels: [] };
                }
            }
        } catch (e) {
            // It was just text
        }

        appendMessage('assistant', aiResponse, claims);
        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: aiResponse });

    } catch (error) {
        // Handle different types of errors
        let errorMessage = 'Sorry, something went wrong. ';
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage += 'Unable to connect to the server. Please check your connection and try again.';
        } else if (error.message) {
            errorMessage += error.message;
        } else {
            errorMessage += 'Please try again.';
        }
        
        appendMessage('assistant', errorMessage);
    }
}

function appendMessage(role, content, claims = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerText = role === 'user' ? 'ME' : 'AI';

    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'content-wrapper';
    contentWrapper.style.flex = '1';
    contentWrapper.style.minWidth = '0';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    // Use innerHTML but handle basics/safety
    contentDiv.innerHTML = `<div class="text-response">${content.replace(/\n/g, '<br>')}</div>`;

    if (claims) {
        console.log("Booking Hotels Assistant: Preparing to render claims", claims);
        const recommendationsDiv = renderClaims(claims);
        if (recommendationsDiv) {
            contentDiv.appendChild(recommendationsDiv);
        } else {
            console.log("Booking Hotels Assistant: No renderable data found in claims.");
        }
    }

    contentWrapper.appendChild(contentDiv);

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentWrapper);
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function renderClaims(claims) {
    const container = document.createElement('div');
    container.className = 'recommendations-container';

    let hasData = false;

    // Hotels only
    const hotels = claims.top_hotels || claims.hotels || [];
    console.log("Booking Hotels Assistant: Rendering hotels count:", hotels.length);
    hotels.forEach(h => {
        hasData = true;
        const card = document.createElement('div');
        card.className = 'recommendation-card';
        
        // Get link or construct default search URL
        const link = h.link || `https://www.google.com/travel/hotels/${h.address || 'hotels'}?q=${encodeURIComponent(h.name)}`;
        
        // Store link in data attribute for reliable access
        card.setAttribute('data-hotel-link', link);
        
        // Build rating display
        let ratingHtml = '';
        if (h.rating) {
            const rating = parseFloat(h.rating) || 0;
            const stars = '⭐'.repeat(Math.floor(rating));
            ratingHtml = `<div class="hotel-rating">${stars} ${h.rating}${h.reviews ? ` (${h.reviews} reviews)` : ''}</div>`;
        }
        
        // Build address display
        let addressHtml = '';
        if (h.address) {
            addressHtml = `<div class="hotel-address">📍 ${h.address}</div>`;
        }
        
        card.innerHTML = `
            <div class="card-type">🏨 Hotel</div>
            <div class="card-title">${h.name}</div>
            <div class="card-subtitle">${h.type || 'Accommodation'}</div>
            ${ratingHtml}
            ${addressHtml}
            <div class="card-price">$${h.price} <span>/ night</span></div>
        `;
        
        // Add click handler AFTER innerHTML is set
        card.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const hotelLink = card.getAttribute('data-hotel-link') || link;
            window.open(hotelLink, '_blank', 'noopener,noreferrer');
        });
        
        // Also handle touch events for mobile
        card.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const hotelLink = card.getAttribute('data-hotel-link') || link;
            window.open(hotelLink, '_blank', 'noopener,noreferrer');
        });
        
        container.appendChild(card);
    });

    return hasData ? container : null;
}

function startNewChat() {
    chatHistory = [];
    chatWindow.innerHTML = '';
    appendMessage('assistant', INITIAL_MESSAGE);
    userInput.value = '';
    userInput.focus();
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

newChatBtn.addEventListener('click', startNewChat);
