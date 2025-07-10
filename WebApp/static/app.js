// static/app.js
let spineChart;

document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('spineChart').getContext('2d');
    spineChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Original Data',
                    data: [],
                    backgroundColor: 'rgba(75, 192, 192, 0.6)'
                },
                {
                    label: 'Predicted Data',
                    data: [],
                    backgroundColor: 'rgba(255, 99, 132, 0.6)'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Spine'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Poundage'
                    }
                }
            }
        }
    });

    document.getElementById('calculate').addEventListener('click', calculateAndUpdateChart);
});

async function calculateAndUpdateChart() {
    const arrowLength = document.getElementById('arrowLength').value;
    const poundageType = document.getElementById('poundageType').value;

    try {
        const response = await axios.post('/api/calculate', {
            arrowLength: parseFloat(arrowLength),
            poundageType: poundageType
        });

        const { original_data, predicted_data, coef, intercept } = response.data;

        spineChart.data.datasets[0].data = original_data.map(d => ({ x: d.Spine, y: d[`${poundageType}Poundage`] }));
        spineChart.data.datasets[1].data = predicted_data.map(d => ({ x: d.Spine, y: d[`${poundageType}Poundage`] }));
        
        spineChart.options.plugins.title = {
            display: true,
            text: `Arrow Length: ${arrowLength}", Poundage Type: ${poundageType}`
        };
        spineChart.update();

        console.log(`Linear Regression: y = ${coef.toFixed(4)}x + ${intercept.toFixed(4)}`);
    } catch (error) {
        console.error('Error calculating data:', error);
    }
}