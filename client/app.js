document.addEventListener('DOMContentLoaded', function() {
    const fetchBtn = document.getElementById('fetchBtn');
    const result = document.getElementById('result');
    
    fetchBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('http://localhost:8000/');
            const data = await response.json();
            result.innerHTML = `<p>${data.message}</p>`;
        } catch (error) {
            result.innerHTML = `<p>Error: ${error.message}</p>`;
        }
    });
});