let selectedService = null;

function selectService(service) {
    selectedService = service;
    
    // Update UI
    document.querySelectorAll('.service-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.querySelector(`.service-btn[onclick="selectService('${service}')"]`).classList.add('active');
}

function estimateFare() {
    if (!selectedService) {
        alert('Please select a service type (Auto, Bike, or Car)');
        return;
    }
    
    const source = document.getElementById('source').value;
    const destination = document.getElementById('destination').value;
    
    if (source === destination) {
        alert('Source and destination cannot be the same');
        return;
    }
    
    // API call to get fare estimate
    fetch('/api/estimate_fare', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            source: source,
            destination: destination,
            service_type: selectedService
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.fare) {
            document.getElementById('fare-amount').textContent = `₹${data.fare}`;
            document.getElementById('fare-display').classList.remove('hidden');
            
            // Enable book button
            document.getElementById('book-ride').disabled = false;
        } else {
            alert("Error calculating fare. Please try again.");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Something went wrong. Please try again later.");
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Disable book button until fare is calculated
    document.getElementById('book-ride').disabled = true;
    
    // Add event listener for book button
    document.getElementById('book-ride').addEventListener('click', function() {
        if (!selectedService) {
            alert('Please select a service type and get a fare estimate first');
            return;
        }
        
        const passengerId = document.querySelector('[data-passenger-id]').dataset.passengerId;
        const source = document.getElementById('source').value;
        const destination = document.getElementById('destination').value;
        
        // API call to book ride
        fetch('/api/book_ride', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                passenger_id: passengerId,
                source: source,
                destination: destination,
                service_type: selectedService
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Ride booked! Your driver ${data.driver.name} (${data.driver.vehicle}) will arrive shortly.`);
                // Redirect to ride status page (could be implemented later)
            } else {
                alert(data.message || "Booking failed. Please try again.");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Something went wrong. Please try again later.");
        });
    });
});
