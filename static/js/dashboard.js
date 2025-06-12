document.addEventListener('DOMContentLoaded', function () {
    const billCtx = document.getElementById('billChart').getContext('2d');
    const paymentCtx = document.getElementById('paymentChart').getContext('2d');

    // Create charts with Chart.js
    const billChart = new Chart(billCtx, {
        type: 'bar',
        data: {
            labels: billData.map(bill => bill[2]), // Example for customer names
            datasets: [{
                label: 'Total Bill Amount',
                data: billData.map(bill => bill[9]), // Example for TotalBillAmount
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        }
    });

    const paymentChart = new Chart(paymentCtx, {
        type: 'line',
        data: {
            labels: paymentData.map(payment => payment[6]), // Example for Payment Date
            datasets: [{
                label: 'Payment Amount',
                data: paymentData.map(payment => payment[3]), // Example for Amount
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1
            }]
        }
    });
});
