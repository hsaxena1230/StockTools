// Momentum vs Relative Strength Chart Application
class MomentumRSChart {
    constructor() {
        this.chart = null;
        this.currentPeriod = '30d';
        this.data = [];
        this.industries = new Set();
        
        this.initializeEventListeners();
        this.loadIndustries();
        this.loadInitialData();
    }

    initializeEventListeners() {
        // Period selector
        document.getElementById('periodSelect').addEventListener('change', (e) => {
            this.currentPeriod = e.target.value;
            this.loadData();
        });

        // Industry filter
        document.getElementById('industrySelect').addEventListener('change', () => {
            this.updateChart();
        });

        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadData();
        });
    }

    showLoading() {
        document.getElementById('loadingOverlay').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }

    async loadInitialData() {
        this.showLoading();
        try {
            await this.loadData();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load initial data. Please check if the API server is running.');
        } finally {
            this.hideLoading();
        }
    }

    async loadData() {
        this.showLoading();
        
        try {
            // In a real application, this would be an API call
            // For now, we'll simulate the API response with sample data
            const response = await this.fetchMockData();
            
            this.data = response.data;
            this.updateIndustryFilter();
            this.updateChart();
            this.updateStats();
            
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    // Fetch data from API
    async fetchMockData() {
        try {
            const industryFilter = document.getElementById('industrySelect')?.value || 'all';
            const response = await axios.get(`/api/momentum-vs-rs`, {
                params: {
                    period: this.currentPeriod,
                    industry: industryFilter
                }
            });
            
            if (response.data.success) {
                return response.data;
            } else {
                throw new Error(response.data.error || 'Failed to fetch data');
            }
        } catch (error) {
            console.error('API Error:', error);
            
            // Fallback to mock data if API fails
            console.log('Falling back to mock data...');
            return this.generateMockData();
        }
    }

    // Fallback mock data generator
    generateMockData() {
        const industries = [
            'Information Technology', 'Financial Services', 'Pharmaceuticals',
            'Automotive', 'Energy', 'FMCG', 'Metals & Mining', 'Chemicals',
            'Real Estate', 'Media & Entertainment', 'Telecommunications',
            'Cement', 'Textiles', 'Power', 'Infrastructure'
        ];

        const data = industries.map(industry => ({
            industry: industry,
            momentum_30d: (Math.random() - 0.5) * 40, // -20 to +20
            momentum_90d: (Math.random() - 0.5) * 60, // -30 to +30
            momentum_180d: (Math.random() - 0.5) * 80, // -40 to +40
            relative_strength_30d: (Math.random() - 0.5) * 100, // -50 to +50
            relative_strength_90d: (Math.random() - 0.5) * 120, // -60 to +60
            relative_strength_180d: (Math.random() - 0.5) * 140, // -70 to +70
            current_price: Math.random() * 1000 + 100,
            volatility: Math.random() * 30 + 5
        }));

        return { data, success: true };
    }

    async loadIndustries() {
        try {
            const response = await axios.get('/api/industries');
            if (response.data.success) {
                this.populateIndustryFilter(response.data.industries);
            }
        } catch (error) {
            console.error('Failed to load industries:', error);
            // Keep the default "All Industries" option
        }
    }

    populateIndustryFilter(industries) {
        const industrySelect = document.getElementById('industrySelect');
        const currentValue = industrySelect.value;
        
        // Clear existing options except "All"
        industrySelect.innerHTML = '<option value="all">All Industries</option>';
        
        // Add industry options
        industries.forEach(industry => {
            const option = document.createElement('option');
            option.value = industry.industry;
            option.textContent = industry.name || industry.industry;
            industrySelect.appendChild(option);
        });
        
        // Restore previous selection if still valid
        if (Array.from(industrySelect.options).some(opt => opt.value === currentValue)) {
            industrySelect.value = currentValue;
        }
    }

    updateIndustryFilter() {
        const industrySelect = document.getElementById('industrySelect');
        const currentValue = industrySelect.value;
        
        // Clear existing options except "All"
        industrySelect.innerHTML = '<option value="all">All Industries</option>';
        
        // Get unique industries from data
        this.industries.clear();
        this.data.forEach(item => this.industries.add(item.industry));
        
        // Add industry options
        Array.from(this.industries).sort().forEach(industry => {
            const option = document.createElement('option');
            option.value = industry;
            option.textContent = industry;
            industrySelect.appendChild(option);
        });
        
        // Restore previous selection if still valid
        if (Array.from(industrySelect.options).some(opt => opt.value === currentValue)) {
            industrySelect.value = currentValue;
        }
    }

    getFilteredData() {
        const selectedIndustry = document.getElementById('industrySelect').value;
        
        if (selectedIndustry === 'all') {
            return this.data;
        }
        
        return this.data.filter(item => item.industry === selectedIndustry);
    }

    getQuadrantColor(momentum, relativeStrength) {
        // Determine color based on quadrant position
        if (momentum >= 0 && relativeStrength >= 100) {
            return '#2ecc71'; // Green - Top Right: High momentum + High RS (Best)
        } else if (momentum >= 0 && relativeStrength < 100) {
            return '#3498db'; // Blue - Top Left: High momentum + Low RS (Catching up)
        } else if (momentum < 0 && relativeStrength >= 100) {
            return '#f39c12'; // Orange - Bottom Right: Low momentum + High RS (Consolidating)
        } else {
            return '#e74c3c'; // Red - Bottom Left: Low momentum + Low RS (Weak)
        }
    }

    getQuadrantName(momentum, relativeStrength) {
        if (momentum >= 0 && relativeStrength >= 100) {
            return 'Leaders: High Momentum + Strong RS';
        } else if (momentum >= 0 && relativeStrength < 100) {
            return 'Improving: High Momentum + Weak RS';
        } else if (momentum < 0 && relativeStrength >= 100) {
            return 'Weakening: Low Momentum + Strong RS';
        } else {
            return 'Laggards: Low Momentum + Weak RS';
        }
    }

    updateChart() {
        const ctx = document.getElementById('momentumChart').getContext('2d');
        const filteredData = this.getFilteredData();
        
        if (this.chart) {
            this.chart.destroy();
        }

        const momentumField = `momentum_${this.currentPeriod}`;
        const rsField = `relative_strength_${this.currentPeriod}`;

        const chartData = filteredData.map(item => ({
            x: item[rsField] || 0,           // Relative Strength on X-axis
            y: item[momentumField] || 0,     // Momentum on Y-axis
            industry: item.industry,
            momentum: item[momentumField] || 0,
            relativeStrength: item[rsField] || 0,
            currentPrice: item.current_price || 0,
            volatility: item.volatility || 0
        }));

        this.chart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Industries',
                    data: chartData,
                    backgroundColor: chartData.map(point => 
                        this.getQuadrantColor(point.momentum, point.relativeStrength)
                    ),
                    borderColor: chartData.map(point => 
                        this.getQuadrantColor(point.momentum, point.relativeStrength)
                    ),
                    borderWidth: 1,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Relative Strength vs Momentum Analysis (${this.currentPeriod.toUpperCase()})`,
                        font: {
                            size: 18,
                            weight: 'bold'
                        },
                        color: '#2c3e50'
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false,
                        external: (context) => this.customTooltip(context)
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: `Mansfield Relative Strength (${this.currentPeriod})`,
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            color: '#2c3e50'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(1);
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: `Momentum (${this.currentPeriod})`,
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            color: '#2c3e50'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(1) + '%';
                            }
                        }
                    }
                },
                onHover: (event, activeElements) => {
                    event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const dataIndex = activeElements[0].index;
                        const industry = chartData[dataIndex].industry;
                        this.showIndustryDetails(industry);
                    }
                }
            }
        });

        // Add quadrant reference lines
        this.addQuadrantLines();
    }

    addQuadrantLines() {
        if (!this.chart) return;

        const ctx = this.chart.ctx;
        const chartArea = this.chart.chartArea;
        
        // Add reference lines for quadrant analysis
        Chart.register({
            id: 'quadrantLines',
            afterDraw: (chart) => {
                const { ctx, chartArea, scales } = chart;
                
                ctx.save();
                ctx.strokeStyle = 'rgba(0, 0, 0, 0.4)';
                ctx.lineWidth = 2;
                ctx.setLineDash([8, 4]);
                
                // RS baseline at 100 (vertical line) - divides strong/weak performance
                const baselineX = scales.x.getPixelForValue(100);
                if (baselineX >= chartArea.left && baselineX <= chartArea.right) {
                    ctx.beginPath();
                    ctx.moveTo(baselineX, chartArea.top);
                    ctx.lineTo(baselineX, chartArea.bottom);
                    ctx.stroke();
                    
                    // Add label for baseline
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.font = 'bold 14px Arial';
                    ctx.save();
                    ctx.translate(baselineX + 8, chartArea.top + 25);
                    ctx.rotate(-Math.PI / 2);
                    ctx.fillText('Market Baseline', 0, 0);
                    ctx.restore();
                }
                
                // Zero momentum line (horizontal) - divides positive/negative momentum
                const zeroY = scales.y.getPixelForValue(0);
                if (zeroY >= chartArea.top && zeroY <= chartArea.bottom) {
                    ctx.beginPath();
                    ctx.moveTo(chartArea.left, zeroY);
                    ctx.lineTo(chartArea.right, zeroY);
                    ctx.stroke();
                    
                    // Add label for zero momentum
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.font = 'bold 14px Arial';
                    ctx.fillText('Zero Momentum', chartArea.left + 10, zeroY - 8);
                }
                
                // Add quadrant watermarks
                ctx.save();
                ctx.font = 'bold 28px Arial';
                ctx.fillStyle = 'rgba(0, 0, 0, 0.08)';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Get the actual positions of the reference lines
                const rsBaseline = scales.x.getPixelForValue(100);
                const zeroMomentum = scales.y.getPixelForValue(0);
                
                // Calculate quadrant centers based on actual reference lines
                // Top-Right quadrant (High momentum, High RS)
                const topRightX = (rsBaseline + chartArea.right) / 2;
                const topRightY = (chartArea.top + zeroMomentum) / 2;
                ctx.fillText('LEADERS', topRightX, topRightY);
                
                // Top-Left quadrant (High momentum, Low RS)
                const topLeftX = (chartArea.left + rsBaseline) / 2;
                const topLeftY = (chartArea.top + zeroMomentum) / 2;
                ctx.fillText('IMPROVING', topLeftX, topLeftY);
                
                // Bottom-Right quadrant (Low momentum, High RS)
                const bottomRightX = (rsBaseline + chartArea.right) / 2;
                const bottomRightY = (zeroMomentum + chartArea.bottom) / 2;
                ctx.fillText('WEAKENING', bottomRightX, bottomRightY);
                
                // Bottom-Left quadrant (Low momentum, Low RS)
                const bottomLeftX = (chartArea.left + rsBaseline) / 2;
                const bottomLeftY = (zeroMomentum + chartArea.bottom) / 2;
                ctx.fillText('LAGGARDS', bottomLeftX, bottomLeftY);
                
                ctx.restore();
                
                ctx.restore();
            }
        });
    }

    customTooltip(context) {
        const tooltip = document.getElementById('tooltip');
        const tooltipModel = context.tooltip;

        if (tooltipModel.opacity === 0) {
            tooltip.style.display = 'none';
            return;
        }

        if (tooltipModel.dataPoints && tooltipModel.dataPoints.length > 0) {
            const dataPoint = tooltipModel.dataPoints[0];
            const data = dataPoint.raw;
            
            tooltip.innerHTML = `
                <div class="tooltip-industry">${data.industry}</div>
                <div class="tooltip-values">
                    <span class="tooltip-label">Quadrant:</span>
                    <span class="tooltip-value">${this.getQuadrantName(data.momentum, data.relativeStrength)}</span>
                    <span class="tooltip-label">Momentum:</span>
                    <span class="tooltip-value">${data.momentum.toFixed(2)}%</span>
                    <span class="tooltip-label">Relative Strength:</span>
                    <span class="tooltip-value">${data.relativeStrength.toFixed(1)}</span>
                    <span class="tooltip-label">Current Price:</span>
                    <span class="tooltip-value">₹${data.currentPrice.toFixed(2)}</span>
                    <span class="tooltip-label">Volatility:</span>
                    <span class="tooltip-value">${data.volatility.toFixed(2)}%</span>
                </div>
            `;
            
            tooltip.style.display = 'block';
            tooltip.style.left = tooltipModel.caretX + 'px';
            tooltip.style.top = tooltipModel.caretY + 'px';
        }
    }

    updateStats() {
        const filteredData = this.getFilteredData();
        const momentumField = `momentum_${this.currentPeriod}`;
        const rsField = `relative_strength_${this.currentPeriod}`;

        // Top Momentum
        const topMomentum = [...filteredData]
            .sort((a, b) => (b[momentumField] || 0) - (a[momentumField] || 0))
            .slice(0, 5);
        
        this.updateStatCard('topMomentum', topMomentum.map(item => ({
            name: item.industry,
            value: `${(item[momentumField] || 0).toFixed(2)}%`,
            isPositive: (item[momentumField] || 0) >= 0
        })));

        // Top Relative Strength
        const topRS = [...filteredData]
            .sort((a, b) => (b[rsField] || 0) - (a[rsField] || 0))
            .slice(0, 5);
        
        this.updateStatCard('topRelativeStrength', topRS.map(item => ({
            name: item.industry,
            value: (item[rsField] || 0).toFixed(2),
            isPositive: (item[rsField] || 0) >= 0
        })));

        // Best Combined (momentum + RS)
        const bestCombined = [...filteredData]
            .sort((a, b) => {
                const scoreA = (a[momentumField] || 0) + (a[rsField] || 0);
                const scoreB = (b[momentumField] || 0) + (b[rsField] || 0);
                return scoreB - scoreA;
            })
            .slice(0, 5);
        
        this.updateStatCard('bestCombined', bestCombined.map(item => ({
            name: item.industry,
            value: ((item[momentumField] || 0) + (item[rsField] || 0)).toFixed(2),
            isPositive: ((item[momentumField] || 0) + (item[rsField] || 0)) >= 0
        })));

        // Data Summary
        const avgMomentum = filteredData.reduce((sum, item) => sum + (item[momentumField] || 0), 0) / filteredData.length;
        const avgRS = filteredData.reduce((sum, item) => sum + (item[rsField] || 0), 0) / filteredData.length;
        
        document.getElementById('dataSummary').innerHTML = `
            <div class="industry-item">
                <span class="industry-name">Industries:</span>
                <span class="industry-value">${filteredData.length}</span>
            </div>
            <div class="industry-item">
                <span class="industry-name">Avg Momentum:</span>
                <span class="industry-value ${avgMomentum >= 0 ? 'positive' : 'negative'}">
                    ${avgMomentum.toFixed(2)}%
                </span>
            </div>
            <div class="industry-item">
                <span class="industry-name">Avg Rel. Strength:</span>
                <span class="industry-value ${avgRS >= 0 ? 'positive' : 'negative'}">
                    ${avgRS.toFixed(2)}
                </span>
            </div>
            <div class="industry-item">
                <span class="industry-name">Period:</span>
                <span class="industry-value">${this.currentPeriod.toUpperCase()}</span>
            </div>
        `;
    }

    updateStatCard(elementId, items) {
        const element = document.getElementById(elementId);
        element.innerHTML = items.map(item => `
            <div class="industry-item">
                <span class="industry-name">${item.name}</span>
                <span class="industry-value ${item.isPositive ? 'positive' : 'negative'}">
                    ${item.value}
                </span>
            </div>
        `).join('');
    }

    showIndustryDetails(industry) {
        const industryData = this.data.find(item => item.industry === industry);
        if (industryData) {
            alert(`Industry: ${industry}\n` +
                  `30d Momentum: ${(industryData.momentum_30d || 0).toFixed(2)}%\n` +
                  `90d Momentum: ${(industryData.momentum_90d || 0).toFixed(2)}%\n` +
                  `180d Momentum: ${(industryData.momentum_180d || 0).toFixed(2)}%\n` +
                  `30d RS: ${(industryData.relative_strength_30d || 0).toFixed(2)}\n` +
                  `90d RS: ${(industryData.relative_strength_90d || 0).toFixed(2)}\n` +
                  `180d RS: ${(industryData.relative_strength_180d || 0).toFixed(2)}\n` +
                  `Current Price: ₹${(industryData.current_price || 0).toFixed(2)}\n` +
                  `Volatility: ${(industryData.volatility || 0).toFixed(2)}%`);
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        const container = document.querySelector('.container');
        container.insertBefore(errorDiv, container.firstChild);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MomentumRSChart();
});