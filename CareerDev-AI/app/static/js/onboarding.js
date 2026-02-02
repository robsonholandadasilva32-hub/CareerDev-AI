function toggleBillingAddress() {
    const checkbox = document.getElementById('billing_same_as_residential');
    const container = document.getElementById('billing_address_container');
    const fields = document.querySelectorAll('.billing-field');

    if (checkbox.checked) {
        container.style.display = 'none';
        fields.forEach(field => field.required = false);
    } else {
        container.style.display = 'block';
        fields.forEach(field => field.required = true);
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    const checkbox = document.getElementById('billing_same_as_residential');
    if (checkbox) {
         toggleBillingAddress();
    }
});
