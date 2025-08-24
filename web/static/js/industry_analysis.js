// Comprehensive Industry Analysis
class IndustryAnalysis {
    constructor() {
        this.charts = {};
        this.industryData = [];
        this.analysisType = 'all';
        this.sortBy = 'rs';
        this.benchmark = 'nifty500';
        
        this.quadrantColors = {
            'leaders': '#2ecc71',
            'improving': '#3498db',
            'weakening': '#f39c12',
            'laggards': '#e74c3c'
        };
        
        this.initializeEventListeners();
        this.loadAnalysis();
    }
    
    initializeEventListeners() {
        document.getElementById('analysisType').addEventListener('change', (e) => {
            this.analysisType = e.target.value;
            this.filterAndDisplayCharts();
        });
        
        document.getElementById('sortBy').addEventListener('change', (e) => {
            this.sortBy = e.target.value;
            this.filterAndDisplayCharts();
        });
        
        document.getElementById('benchmarkSelect').addEventListener('change', (e) => {
            this.benchmark = e.target.value;
            this.updateBenchmarkInfo();
        });
        
        document.getElementById('loadAnalysisBtn').addEventListener('click', () => {
            this.loadAnalysis();
        });
    }
    
    showLoading() {
        document.getElementById('loadingOverlay').classList.remove('hidden');
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }
    
    updateBenchmarkInfo() {
        const benchmarkName = {
            'nifty500': 'NIFTY 500',
            'nifty200': 'NIFTY 200'
        }[this.benchmark];
        
        document.getElementById('currentBenchmark').textContent = benchmarkName;
    }
    
    async loadAnalysis() {
        this.showLoading();
        
        try {
            // Load all industries
            const industriesResponse = await axios.get('/api/industries');
            if (!industriesResponse.data.success) {
                throw new Error('Failed to load industries');
            }
            
            const industries = industriesResponse.data.industries.map(ind => ind.industry);
            
            // Load journey data for all industries
            const params = new URLSearchParams();
            params.append('days', '30'); // Standard 30-day analysis
            industries.forEach(industry => {
                params.append('industries[]', industry);
            });
            
            const journeyResponse = await axios.get(`/api/quadrant-journey?${params.toString()}`);
            if (!journeyResponse.data.success) {
                throw new Error('Failed to load journey data');
            }
            
            this.industryData = journeyResponse.data.data;
            this.updateMarketSummary();
            this.filterAndDisplayCharts();
            this.updateRankings();
            
        } catch (error) {
            console.error('Error loading analysis:', error);
            this.showError('Failed to load industry analysis data');
        } finally {
            this.hideLoading();
        }
    }
    
    updateMarketSummary() {
        const summaryContainer = document.getElementById('marketSummary');
        
        const quadrantCounts = {
            leaders: 0,
            improving: 0,
            weakening: 0,
            laggards: 0
        };
        
        let totalMomentum = 0;
        let totalRS = 0;
        let positiveRS = 0;
        
        this.industryData.forEach(industry => {
            const lastPoint = industry.data_points[industry.data_points.length - 1];
            const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
            quadrantCounts[quadrant]++;
            
            totalMomentum += lastPoint.momentum;
            totalRS += lastPoint.relative_strength;
            
            if (lastPoint.relative_strength > 100) {
                positiveRS++;
            }
        });
        
        const totalIndustries = this.industryData.length;
        const avgMomentum = totalMomentum / totalIndustries;
        const avgRS = totalRS / totalIndustries;
        const rsPositivePercent = (positiveRS / totalIndustries) * 100;
        
        summaryContainer.innerHTML = `
            <div class="summary-stat">
                <div class="summary-stat-value">${totalIndustries}</div>
                <div class="summary-stat-label">Total Industries</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value ${avgMomentum >= 0 ? 'positive' : 'negative'}">${avgMomentum.toFixed(1)}%</div>
                <div class="summary-stat-label">Avg Momentum</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value ${avgRS >= 100 ? 'positive' : 'negative'}">${avgRS.toFixed(0)}</div>
                <div class="summary-stat-label">Avg Rel. Strength</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value">${rsPositivePercent.toFixed(0)}%</div>
                <div class="summary-stat-label">Above Benchmark</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value" style="color: ${this.quadrantColors.leaders}">${quadrantCounts.leaders}</div>
                <div class="summary-stat-label">Leaders</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value" style="color: ${this.quadrantColors.improving}">${quadrantCounts.improving}</div>
                <div class="summary-stat-label">Improving</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value" style="color: ${this.quadrantColors.weakening}">${quadrantCounts.weakening}</div>
                <div class="summary-stat-label">Weakening</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value" style="color: ${this.quadrantColors.laggards}">${quadrantCounts.laggards}</div>
                <div class="summary-stat-label">Laggards</div>
            </div>
        `;
    }
    
    filterAndDisplayCharts() {
        let filteredData = [...this.industryData];
        
        // Filter by analysis type
        if (this.analysisType !== 'all') {
            filteredData = filteredData.filter(industry => {
                const lastPoint = industry.data_points[industry.data_points.length - 1];
                const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
                return quadrant === this.analysisType;
            });
        }
        
        // Sort data
        filteredData.sort((a, b) => {
            const aLast = a.data_points[a.data_points.length - 1];
            const bLast = b.data_points[b.data_points.length - 1];
            
            switch (this.sortBy) {
                case 'momentum':
                    return bLast.momentum - aLast.momentum;
                case 'rs':
                    return bLast.relative_strength - aLast.relative_strength;
                case 'alphabetical':
                    return a.name.localeCompare(b.name);
                case 'quadrant':
                    const quadrantOrder = { leaders: 4, improving: 3, weakening: 2, laggards: 1 };
                    const aQuadrant = this.calculateQuadrant(aLast.relative_strength, aLast.momentum);
                    const bQuadrant = this.calculateQuadrant(bLast.relative_strength, bLast.momentum);
                    return quadrantOrder[bQuadrant] - quadrantOrder[aQuadrant];
                default:
                    return 0;
            }
        });
        
        this.displayCharts(filteredData);
    }
    
    displayCharts(data) {
        const container = document.getElementById('chartsContainer');
        
        if (data.length === 0) {
            container.innerHTML = `
                <div class="charts-loading">
                    <div class="loading-icon">
                        <i class="fas fa-search fa-3x"></i>
                    </div>
                    <h3>No Industries Found</h3>
                    <p>No industries match the current filter criteria.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        
        data.forEach((industry, index) => {
            this.createIndustryChart(industry, index);
        });
    }
    
    createIndustryChart(industryData, index) {
        const container = document.getElementById('chartsContainer');
        const lastPoint = industryData.data_points[industryData.data_points.length - 1];
        const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
        
        // Create chart card
        const chartCard = document.createElement('div');
        chartCard.className = 'industry-chart-card';
        chartCard.innerHTML = `
            <div class="chart-card-header">
                <div class="chart-title">${industryData.name}</div>
                <div class="chart-metrics">
                    <div class="chart-metric">
                        <div class="metric-label">Momentum</div>
                        <div class="metric-value ${lastPoint.momentum >= 0 ? 'positive' : 'negative'}">
                            ${lastPoint.momentum.toFixed(2)}%
                        </div>
                    </div>
                    <div class="chart-metric">
                        <div class="metric-label">Rel. Strength</div>
                        <div class="metric-value ${lastPoint.relative_strength >= 100 ? 'positive' : 'negative'}">
                            ${lastPoint.relative_strength.toFixed(1)}
                        </div>
                    </div>
                    <div class="chart-metric">
                        <div class="metric-label">Quadrant</div>
                        <div class="quadrant-indicator ${quadrant}">
                            ${this.formatQuadrantName(quadrant)}
                        </div>
                    </div>
                </div>
            </div>
            <div class="chart-card-body">
                <canvas id="chart_${index}" class="industry-chart"></canvas>
            </div>
        `;
        
        container.appendChild(chartCard);
        
        // Create Chart.js chart
        setTimeout(() => {
            this.renderChart(`chart_${index}`, industryData);
        }, 100);
    }
    
    renderChart(canvasId, industryData) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        // Prepare data points
        const dataPoints = industryData.data_points.map((point, i) => ({
            x: point.relative_strength,
            y: point.momentum,
            date: point.date,
            isStart: i === 0,
            isEnd: i === industryData.data_points.length - 1
        }));
        
        const chart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: industryData.name,
                    data: dataPoints,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.2)',
                    pointBackgroundColor: dataPoints.map(point => {
                        if (point.isStart) return '#2ecc71';
                        if (point.isEnd) return '#e74c3c';
                        return 'rgba(52, 152, 219, 0.6)';
                    }),
                    pointBorderColor: dataPoints.map(point => {
                        if (point.isStart) return '#27ae60';
                        if (point.isEnd) return '#c0392b';
                        return '#3498db';
                    }),
                    pointRadius: dataPoints.map(point => {
                        if (point.isStart || point.isEnd) return 8;
                        return 3;
                    }),
                    borderWidth: 3,
                    tension: 0.1,
                    showLine: true,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: (context) => {
                                const point = context[0].raw;
                                if (point.isStart) return '🟢 START';
                                if (point.isEnd) return '🔴 CURRENT';
                                return 'Journey Point';
                            },
                            label: (context) => {
                                const point = context.raw;
                                const quadrant = this.calculateQuadrant(point.x, point.y);
                                return [
                                    `Date: ${point.date}`,
                                    `Momentum: ${point.y.toFixed(2)}%`,
                                    `Rel. Strength: ${point.x.toFixed(1)}`,
                                    `Quadrant: ${this.formatQuadrantName(quadrant)}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Relative Strength',
                            font: { size: 12, weight: 'bold' }
                        },
                        min: 0,
                        max: 200,
                        grid: { color: 'rgba(0, 0, 0, 0.1)' }
                    },
                    y: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Momentum (%)',
                            font: { size: 12, weight: 'bold' }
                        },
                        min: -50,
                        max: 50,
                        grid: { color: 'rgba(0, 0, 0, 0.1)' },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            },
            plugins: [{
                id: 'quadrantBackground',
                beforeDraw: (chart) => {
                    const { ctx, chartArea, scales } = chart;
                    
                    if (!scales.x || !scales.y) return;
                    
                    ctx.save();
                    
                    // Calculate quadrant boundaries
                    const x100 = scales.x.getPixelForValue(100);
                    const y0 = scales.y.getPixelForValue(0);
                    
                    // Draw quadrant backgrounds
                    ctx.globalAlpha = 0.15;
                    
                    // Leaders (top-right)
                    ctx.fillStyle = this.quadrantColors.leaders;
                    ctx.fillRect(x100, chartArea.top, chartArea.right - x100, y0 - chartArea.top);
                    
                    // Improving (top-left)
                    ctx.fillStyle = this.quadrantColors.improving;
                    ctx.fillRect(chartArea.left, chartArea.top, x100 - chartArea.left, y0 - chartArea.top);
                    
                    // Weakening (bottom-right)
                    ctx.fillStyle = this.quadrantColors.weakening;
                    ctx.fillRect(x100, y0, chartArea.right - x100, chartArea.bottom - y0);
                    
                    // Laggards (bottom-left)
                    ctx.fillStyle = this.quadrantColors.laggards;
                    ctx.fillRect(chartArea.left, y0, x100 - chartArea.left, chartArea.bottom - y0);
                    
                    ctx.globalAlpha = 1;
                    
                    // Draw reference lines
                    ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([5, 5]);
                    
                    // Vertical line at RS = 100
                    ctx.beginPath();
                    ctx.moveTo(x100, chartArea.top);
                    ctx.lineTo(x100, chartArea.bottom);
                    ctx.stroke();
                    
                    // Horizontal line at Momentum = 0
                    ctx.beginPath();
                    ctx.moveTo(chartArea.left, y0);
                    ctx.lineTo(chartArea.right, y0);
                    ctx.stroke();
                    
                    ctx.setLineDash([]);
                    
                    // Add small quadrant labels
                    ctx.font = 'bold 10px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.globalAlpha = 0.6;
                    
                    // Calculate label positions
                    const leadersX = x100 + (chartArea.right - x100) / 2;
                    const leadersY = chartArea.top + (y0 - chartArea.top) / 2;
                    const improvingX = chartArea.left + (x100 - chartArea.left) / 2;
                    const improvingY = chartArea.top + (y0 - chartArea.top) / 2;
                    const weakeningX = x100 + (chartArea.right - x100) / 2;
                    const weakeningY = y0 + (chartArea.bottom - y0) / 2;
                    const laggardsX = chartArea.left + (x100 - chartArea.left) / 2;
                    const laggardsY = y0 + (chartArea.bottom - y0) / 2;
                    
                    ctx.fillStyle = '#2c3e50';
                    ctx.fillText('LEADERS', leadersX, leadersY);
                    ctx.fillText('IMPROVING', improvingX, improvingY);
                    ctx.fillText('WEAKENING', weakeningX, weakeningY);
                    ctx.fillText('LAGGARDS', laggardsX, laggardsY);
                    
                    ctx.restore();
                }
            }]
        });
        
        this.charts[canvasId] = chart;
    }
    
    updateRankings() {
        const container = document.getElementById('rankingsContent');
        
        // Prepare ranking data
        const momentumRanking = [...this.industryData].sort((a, b) => {
            const aLast = a.data_points[a.data_points.length - 1];
            const bLast = b.data_points[b.data_points.length - 1];
            return bLast.momentum - aLast.momentum;
        });
        
        const rsRanking = [...this.industryData].sort((a, b) => {
            const aLast = a.data_points[a.data_points.length - 1];
            const bLast = b.data_points[b.data_points.length - 1];
            return bLast.relative_strength - aLast.relative_strength;
        });
        
        container.innerHTML = `
            <div class="rankings-grid">
                <div class="ranking-section">
                    <h4>
                        <i class="fas fa-rocket"></i>
                        Top Momentum Leaders
                    </h4>
                    <ul class="ranking-list">
                        ${momentumRanking.slice(0, 5).map((industry, index) => {
                            const lastPoint = industry.data_points[industry.data_points.length - 1];
                            const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
                            return `
                                <li class="ranking-item">
                                    <div class="ranking-position">${index + 1}</div>
                                    <div class="ranking-info">
                                        <div class="ranking-name">${industry.name}</div>
                                        <div class="ranking-quadrant">${this.formatQuadrantName(quadrant)}</div>
                                    </div>
                                    <div class="ranking-value positive">${lastPoint.momentum.toFixed(2)}%</div>
                                </li>
                            `;
                        }).join('')}
                    </ul>
                </div>
                
                <div class="ranking-section">
                    <h4>
                        <i class="fas fa-muscle"></i>
                        Strongest Relative Strength
                    </h4>
                    <ul class="ranking-list">
                        ${rsRanking.slice(0, 5).map((industry, index) => {
                            const lastPoint = industry.data_points[industry.data_points.length - 1];
                            const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
                            return `
                                <li class="ranking-item">
                                    <div class="ranking-position">${index + 1}</div>
                                    <div class="ranking-info">
                                        <div class="ranking-name">${industry.name}</div>
                                        <div class="ranking-quadrant">${this.formatQuadrantName(quadrant)}</div>
                                    </div>
                                    <div class="ranking-value ${lastPoint.relative_strength >= 100 ? 'positive' : 'negative'}">
                                        ${lastPoint.relative_strength.toFixed(1)}
                                    </div>
                                </li>
                            `;
                        }).join('')}
                    </ul>
                </div>
                
                <div class="ranking-section">
                    <h4>
                        <i class="fas fa-arrow-down"></i>
                        Weakest Momentum
                    </h4>
                    <ul class="ranking-list">
                        ${momentumRanking.slice(-5).reverse().map((industry, index) => {
                            const lastPoint = industry.data_points[industry.data_points.length - 1];
                            const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
                            return `
                                <li class="ranking-item">
                                    <div class="ranking-position">${index + 1}</div>
                                    <div class="ranking-info">
                                        <div class="ranking-name">${industry.name}</div>
                                        <div class="ranking-quadrant">${this.formatQuadrantName(quadrant)}</div>
                                    </div>
                                    <div class="ranking-value negative">${lastPoint.momentum.toFixed(2)}%</div>
                                </li>
                            `;
                        }).join('')}
                    </ul>
                </div>
                
                <div class="ranking-section">
                    <h4>
                        <i class="fas fa-chart-line-down"></i>
                        Weakest Relative Strength
                    </h4>
                    <ul class="ranking-list">
                        ${rsRanking.slice(-5).reverse().map((industry, index) => {
                            const lastPoint = industry.data_points[industry.data_points.length - 1];
                            const quadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
                            return `
                                <li class="ranking-item">
                                    <div class="ranking-position">${index + 1}</div>
                                    <div class="ranking-info">
                                        <div class="ranking-name">${industry.name}</div>
                                        <div class="ranking-quadrant">${this.formatQuadrantName(quadrant)}</div>
                                    </div>
                                    <div class="ranking-value negative">${lastPoint.relative_strength.toFixed(1)}</div>
                                </li>
                            `;
                        }).join('')}
                    </ul>
                </div>
            </div>
        `;
    }
    
    calculateQuadrant(rs, momentum) {
        if (rs >= 100 && momentum >= 0) return 'leaders';
        if (rs < 100 && momentum >= 0) return 'improving';
        if (rs >= 100 && momentum < 0) return 'weakening';
        return 'laggards';
    }
    
    formatQuadrantName(quadrant) {
        const names = {
            'leaders': 'Leaders',
            'improving': 'Improving',
            'weakening': 'Weakening',
            'laggards': 'Laggards'
        };
        return names[quadrant] || quadrant;
    }
    
    showError(message) {
        const container = document.getElementById('chartsContainer');
        container.innerHTML = `
            <div class="charts-loading">
                <div class="loading-icon">
                    <i class="fas fa-exclamation-triangle fa-3x" style="color: var(--danger-color);"></i>
                </div>
                <h3>Error Loading Data</h3>
                <p>${message}</p>
            </div>
        `;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new IndustryAnalysis();
});