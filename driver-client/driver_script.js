let currentStatus = 'offline';

function updateStatus(status) {
    currentStatus = status;
    
    // Update UI
    document.querySelectorAll('.toggle-buttons button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(`status-${status}`).classList.add('active');
    
    // In a real app, we would send this status to the server
    fetch('/api/update_driver_status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            driver_id: document.querySelector('[data-driver-id]').dataset.driverId,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Status updated:', data);
    })
    .catch(error => {
        console.error('Error updating status:', error);
    });
}

// Function to check for active rides
function checkActiveRides() {
    const driverId = document.querySelector('[data-driver-id]').dataset.driverId;
    
    fetch(`/api/active_ride/${driverId}`)
    .then(response => response.json())
    .then(data => {
        if (data.active_ride) {
            // Show ride details
            document.getElementById('no-ride-message').classList.add('hidden');
            document.getElementById('ride-details').classList.remove('hidden');
            
            // Populate ride details
            const rideDetails = document.getElementById('ride-details');
            rideDetails.innerHTML = `
                <p><strong>Passenger:</strong> ${data.passenger_name}</p>
                <p><strong>From:</strong> ${data.source}</p>
                <p><strong>To:</strong> ${data.destination}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                <button id="update-ride-status" data-booking-id="${data.booking_id}" 
                    data-next-status="${data.status === 'Confirmed' ? 'Ongoing' : 'Completed'}">
                    ${data.status === 'Confirmed' ? 'Start Ride' : 'Complete Ride'}
                </button>
            `;
            
            // Add event listener to status update button
            document.getElementById('update-ride-status').addEventListener('click', function() {
                const bookingId = this.dataset.bookingId;
                const nextStatus = this.dataset.nextStatus;
                
                fetch('/api/update_ride_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        booking_id: bookingId,
                        status: nextStatus
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Refresh ride information
                        checkActiveRides();
                    } else {
                        alert(data.message || "Failed to update ride status.");
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert("Something went wrong. Please try again later.");
                });
            });
        } else {
            // No active ride
            document.getElementById('no-ride-message').classList.remove('hidden');
            document.getElementById('ride-details').classList.add('hidden');
        }
    })
    .catch(error => {
        console.error('Error checking rides:', error);
    });
}

function acceptRide(bookingId) {
    fetch('/api/driver_accept_ride', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId })
    }).then(() => checkActiveRides());
}

function cancelRide(bookingId) {
    fetch('/api/driver_cancel_ride', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId })
    }).then(() => checkActiveRides());
}

function completeRide(bookingId) {
    fetch('/api/driver_complete_ride', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId })
    }).then(() => checkActiveRides());
}

// On page load
document.addEventListener('DOMContentLoaded', function() {
    // Set initial driver status
    updateStatus('offline');
    
    // Check for active rides
    checkActiveRides();
    
    // Set interval to periodically check for new rides (every 30 seconds)
    setInterval(checkActiveRides, 30000);
});
