// Smoothed Quadrant Journey Visualization
class SmoothedQuadrantJourney {
    constructor() {
        this.chart = null;
        this.selectedIndustry = '';
        this.currentPeriod = 30;
        this.smoothingMode = 'ema';
        this.journeyData = [];
        this.smoothedData = [];
        
        this.colors = {
            original: '#3498db',
            smoothed: '#e74c3c'
        };
        
        this.quadrantColors = {
            'leaders': '#2ecc71',
            'improving': '#3498db',
            'weakening': '#f39c12',
            'laggards': '#e74c3c'
        };
        
        this.initializeEventListeners();
        setTimeout(() => {
            this.loadIndustries();
        }, 100);
    }
    
    initializeEventListeners() {
        // Period selector
        document.getElementById('periodSelect').addEventListener('change', (e) => {
            this.currentPeriod = parseInt(e.target.value);
            this.updateSmoothingParams();
            this.updateJourney();
        });
        
        // Industry selector
        document.getElementById('industrySelect').addEventListener('change', (e) => {
            this.selectedIndustry = e.target.value;
            if (this.selectedIndustry) {
                this.updateJourney();
            }
        });
        
        // Smoothing mode selector
        document.getElementById('smoothingMode').addEventListener('change', (e) => {
            this.smoothingMode = e.target.value;
            this.updateSmoothingParams();
            this.updateJourney();
        });
        
        // Update button
        document.getElementById('updateBtn').addEventListener('click', () => {
            this.updateJourney();
        });
    }
    
    updateSmoothingParams() {
        // Update displayed parameters based on period and mode
        const emaPeriods = {
            30: 5,
            90: 10,
            180: 15
        };
        
        const emaPeriod = emaPeriods[this.currentPeriod];
        document.getElementById('currentMode').textContent = {
            'none': 'No Smoothing',
            'ema': 'EMA Only',
            'lowess': 'LOWESS Only',
            'hybrid': 'Hybrid (EMA + LOWESS)',
            'conservative': 'Conservative (Endpoint-Preserving)'
        }[this.smoothingMode];
        
        document.getElementById('emaPeriod').textContent = `${emaPeriod} days`;
        document.getElementById('lowessBandwidth').textContent = '0.2';
    }
    
    showLoading() {
        document.getElementById('loadingOverlay').classList.remove('hidden');
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }
    
    async loadIndustries() {
        try {
            const response = await axios.get('/api/industries');
            
            if (response.data.success) {
                this.populateIndustryDropdown(response.data.industries);
                this.selectFirstIndustry();
                this.updateJourney();
            }
        } catch (error) {
            console.error('Failed to load industries:', error);
            this.populateWithFallbackIndustries();
            this.selectFirstIndustry();
            this.updateJourney();
        }
    }
    
    populateIndustryDropdown(industries) {
        const select = document.getElementById('industrySelect');
        select.innerHTML = '';
        
        industries.forEach(industry => {
            const option = document.createElement('option');
            option.value = industry.industry;
            option.textContent = industry.name || industry.industry;
            select.appendChild(option);
        });
    }
    
    populateWithFallbackIndustries() {
        const fallbackIndustries = [
            { industry: 'Agricultural Inputs', name: 'Agricultural Inputs Industry Index' },
            { industry: 'Auto Parts', name: 'Auto Parts Industry Index' },
            { industry: 'Steel', name: 'Steel Industry Index' },
            { industry: 'Information Technology Services', name: 'Information Technology Services Industry Index' },
            { industry: 'Pharmaceutical', name: 'Pharmaceutical Industry Index' },
            { industry: 'Banks - Private Sector', name: 'Banks - Private Sector Industry Index' }
        ];
        
        this.populateIndustryDropdown(fallbackIndustries);
    }
    
    selectFirstIndustry() {
        const select = document.getElementById('industrySelect');
        if (select.options.length > 0) {
            select.selectedIndex = 0;
            this.selectedIndustry = select.options[0].value;
        }
    }
    
    async updateJourney() {
        if (!this.selectedIndustry) {
            return;
        }
        
        this.showLoading();
        
        try {
            const params = new URLSearchParams();
            params.append('days', this.currentPeriod);
            params.append('industries[]', this.selectedIndustry);
            
            const response = await axios.get(`/api/quadrant-journey?${params.toString()}`);
            
            if (response.data.success) {
                this.journeyData = response.data.data;
                this.applySmoothing();
                this.updateChart();
                this.updateComparison();
            }
        } catch (error) {
            console.error('Error updating journey:', error);
        } finally {
            this.hideLoading();
        }
    }
    
    applySmoothing() {
        if (this.smoothingMode === 'none') {
            this.smoothedData = this.journeyData;
            this.checkQuadrantIntegrity();
            return;
        }
        
        this.smoothedData = this.journeyData.map(industryData => {
            const dataPoints = industryData.data_points;
            let smoothedPoints = [];
            
            if (this.smoothingMode === 'conservative') {
                smoothedPoints = this.applyConservativeSmoothing(dataPoints);
            } else if (this.smoothingMode === 'ema' || this.smoothingMode === 'hybrid') {
                smoothedPoints = this.applyEMA(dataPoints);
            } else {
                smoothedPoints = [...dataPoints];
            }
            
            if (this.smoothingMode === 'lowess' || this.smoothingMode === 'hybrid') {
                smoothedPoints = this.applyLOWESS(smoothedPoints);
            }
            
            return {
                ...industryData,
                data_points: smoothedPoints
            };
        });
        
        // Update data point count
        const totalPoints = this.smoothedData.reduce((sum, ind) => sum + ind.data_points.length, 0);
        document.getElementById('dataPointCount').textContent = totalPoints;
        
        // Check quadrant integrity
        this.checkQuadrantIntegrity();
    }
    
    checkQuadrantIntegrity() {
        let hasQuadrantChange = false;
        let warningMessages = [];
        
        this.journeyData.forEach((originalData, index) => {
            const smoothedData = this.smoothedData[index];
            const originalEnd = originalData.data_points[originalData.data_points.length - 1];
            const smoothedEnd = smoothedData.data_points[smoothedData.data_points.length - 1];
            
            const originalQuadrant = this.calculateQuadrant(
                originalEnd.relative_strength || originalEnd.rs_original,
                originalEnd.momentum || originalEnd.momentum_original
            );
            const smoothedQuadrant = this.calculateQuadrant(
                smoothedEnd.relative_strength,
                smoothedEnd.momentum
            );
            
            if (originalQuadrant !== smoothedQuadrant && this.smoothingMode !== 'none') {
                hasQuadrantChange = true;
                warningMessages.push({
                    industry: originalData.name,
                    from: originalQuadrant,
                    to: smoothedQuadrant
                });
            }
        });
        
        // Display warning if quadrant changed
        const comparisonContainer = document.getElementById('comparisonContent');
        if (hasQuadrantChange && comparisonContainer) {
            const warningHTML = `
                <div class="quadrant-warning">
                    <div class="warning-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="warning-content">
                        <h4>⚠️ Quadrant Classification Changed</h4>
                        <p>Smoothing has changed the final quadrant position, which may be misleading:</p>
                        <ul>
                            ${warningMessages.map(msg => `
                                <li>
                                    <strong>${msg.industry}</strong>: 
                                    <span class="quadrant-badge ${msg.from}">${this.formatQuadrantName(msg.from)}</span>
                                    → 
                                    <span class="quadrant-badge ${msg.to}">${this.formatQuadrantName(msg.to)}</span>
                                </li>
                            `).join('')}
                        </ul>
                        <p class="warning-note">Consider using a different smoothing method or reviewing the raw data for accurate analysis.</p>
                    </div>
                </div>
            ` + comparisonContainer.innerHTML;
            
            comparisonContainer.innerHTML = warningHTML;
        }
    }
    
    applyEMA(dataPoints) {
        const emaPeriods = {
            30: 5,
            90: 10,
            180: 15
        };
        
        const period = emaPeriods[this.currentPeriod];
        const alpha = 2 / (period + 1);
        
        const smoothedPoints = [...dataPoints];
        const n = dataPoints.length;
        
        // Store original values
        for (let i = 0; i < n; i++) {
            smoothedPoints[i].momentum_original = dataPoints[i].momentum;
            smoothedPoints[i].rs_original = dataPoints[i].relative_strength;
        }
        
        // Apply EMA to momentum (preserve endpoints)
        let emaMomentum = dataPoints[0].momentum;
        
        for (let i = 1; i < n - 1; i++) {
            emaMomentum = alpha * dataPoints[i].momentum + (1 - alpha) * emaMomentum;
            smoothedPoints[i].momentum = emaMomentum;
        }
        
        // Apply EMA to relative strength (preserve endpoints)
        let emaRS = dataPoints[0].relative_strength;
        
        for (let i = 1; i < n - 1; i++) {
            emaRS = alpha * dataPoints[i].relative_strength + (1 - alpha) * emaRS;
            smoothedPoints[i].relative_strength = emaRS;
        }
        
        // Apply endpoint-preserving smoothing for the last few points
        // This ensures the final position doesn't change drastically
        const endpointWindow = Math.min(5, Math.floor(n / 10));
        for (let i = n - endpointWindow; i < n; i++) {
            const weight = (i - (n - endpointWindow)) / endpointWindow;
            smoothedPoints[i].momentum = smoothedPoints[n - endpointWindow - 1].momentum * (1 - weight) + dataPoints[i].momentum * weight;
            smoothedPoints[i].relative_strength = smoothedPoints[n - endpointWindow - 1].relative_strength * (1 - weight) + dataPoints[i].relative_strength * weight;
        }
        
        return smoothedPoints;
    }
    
    applyLOWESS(dataPoints) {
        const bandwidth = 0.2;
        const n = dataPoints.length;
        const windowSize = Math.max(3, Math.floor(n * bandwidth));
        
        const smoothedPoints = [...dataPoints];
        
        // Preserve endpoints
        const endpointPreserve = Math.min(3, Math.floor(n / 20));
        
        // Apply LOWESS to momentum (preserve endpoints)
        for (let i = endpointPreserve; i < n - endpointPreserve; i++) {
            const start = Math.max(0, i - Math.floor(windowSize / 2));
            const end = Math.min(n, start + windowSize);
            
            // Local regression for momentum
            const localPoints = dataPoints.slice(start, end);
            const weights = this.calculateWeights(i, start, end, n);
            
            smoothedPoints[i].momentum = this.weightedAverage(
                localPoints.map(p => p.momentum),
                weights
            );
        }
        
        // Apply LOWESS to relative strength (preserve endpoints)
        for (let i = endpointPreserve; i < n - endpointPreserve; i++) {
            const start = Math.max(0, i - Math.floor(windowSize / 2));
            const end = Math.min(n, start + windowSize);
            
            const localPoints = dataPoints.slice(start, end);
            const weights = this.calculateWeights(i, start, end, n);
            
            smoothedPoints[i].relative_strength = this.weightedAverage(
                localPoints.map(p => p.relative_strength),
                weights
            );
        }
        
        // Ensure end quadrant is preserved
        const lastPoint = dataPoints[n - 1];
        const smoothedLastPoint = smoothedPoints[n - 1];
        
        // Check if quadrant changed
        const originalQuadrant = this.calculateQuadrant(lastPoint.relative_strength, lastPoint.momentum);
        const smoothedQuadrant = this.calculateQuadrant(smoothedLastPoint.relative_strength, smoothedLastPoint.momentum);
        
        if (originalQuadrant !== smoothedQuadrant) {
            console.warn(`LOWESS changed end quadrant from ${originalQuadrant} to ${smoothedQuadrant}. Preserving original endpoint.`);
            // Preserve the original endpoint
            smoothedPoints[n - 1].momentum = lastPoint.momentum;
            smoothedPoints[n - 1].relative_strength = lastPoint.relative_strength;
        }
        
        return smoothedPoints;
    }
    
    applyConservativeSmoothing(dataPoints) {
        const n = dataPoints.length;
        const smoothedPoints = [...dataPoints];
        
        // Store original values
        for (let i = 0; i < n; i++) {
            smoothedPoints[i].momentum_original = dataPoints[i].momentum;
            smoothedPoints[i].rs_original = dataPoints[i].relative_strength;
        }
        
        // Conservative smoothing: Only smooth the middle 80% of the journey
        const preserveStart = Math.floor(n * 0.1);
        const preserveEnd = Math.floor(n * 0.9);
        
        // Apply very light smoothing only to middle section
        const windowSize = Math.max(3, Math.min(7, Math.floor(n / 10)));
        
        for (let i = preserveStart; i < preserveEnd; i++) {
            const start = Math.max(preserveStart, i - Math.floor(windowSize / 2));
            const end = Math.min(preserveEnd, i + Math.floor(windowSize / 2) + 1);
            
            // Simple moving average for momentum
            let momentumSum = 0;
            let rsSum = 0;
            const count = end - start;
            
            for (let j = start; j < end; j++) {
                momentumSum += dataPoints[j].momentum;
                rsSum += dataPoints[j].relative_strength;
            }
            
            smoothedPoints[i].momentum = momentumSum / count;
            smoothedPoints[i].relative_strength = rsSum / count;
        }
        
        // Verify endpoint quadrants haven't changed
        const originalStartQuadrant = this.calculateQuadrant(
            dataPoints[0].relative_strength,
            dataPoints[0].momentum
        );
        const originalEndQuadrant = this.calculateQuadrant(
            dataPoints[n - 1].relative_strength,
            dataPoints[n - 1].momentum
        );
        
        const smoothedStartQuadrant = this.calculateQuadrant(
            smoothedPoints[0].relative_strength,
            smoothedPoints[0].momentum
        );
        const smoothedEndQuadrant = this.calculateQuadrant(
            smoothedPoints[n - 1].relative_strength,
            smoothedPoints[n - 1].momentum
        );
        
        // Guarantee endpoint preservation
        if (originalStartQuadrant !== smoothedStartQuadrant) {
            smoothedPoints[0].momentum = dataPoints[0].momentum;
            smoothedPoints[0].relative_strength = dataPoints[0].relative_strength;
        }
        
        if (originalEndQuadrant !== smoothedEndQuadrant) {
            smoothedPoints[n - 1].momentum = dataPoints[n - 1].momentum;
            smoothedPoints[n - 1].relative_strength = dataPoints[n - 1].relative_strength;
        }
        
        console.log(`Conservative smoothing applied. Start: ${originalStartQuadrant}→${smoothedStartQuadrant}, End: ${originalEndQuadrant}→${smoothedEndQuadrant}`);
        
        return smoothedPoints;
    }
    
    calculateWeights(targetIndex, start, end, totalLength) {
        const weights = [];
        const bandwidth = 0.2 * totalLength;
        
        for (let i = start; i < end; i++) {
            const distance = Math.abs(i - targetIndex);
            const weight = this.tricubeWeight(distance / bandwidth);
            weights.push(weight);
        }
        
        // Normalize weights
        const sum = weights.reduce((a, b) => a + b, 0);
        return weights.map(w => w / sum);
    }
    
    tricubeWeight(u) {
        if (u >= 1) return 0;
        const v = 1 - Math.pow(Math.abs(u), 3);
        return Math.pow(v, 3);
    }
    
    weightedAverage(values, weights) {
        let sum = 0;
        for (let i = 0; i < values.length; i++) {
            sum += values[i] * weights[i];
        }
        return sum;
    }
    
    updateChart() {
        const ctx = document.getElementById('journeyChart').getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }
        
        const datasets = [];
        
        // Add original data
        if (this.smoothingMode !== 'none') {
            this.journeyData.forEach((industryData, index) => {
                const dataPoints = industryData.data_points;
                
                datasets.push({
                    label: `${industryData.name} (Original)`,
                    data: dataPoints.map(point => ({
                        x: point.relative_strength,
                        y: point.momentum,
                        date: point.date,
                        quadrant: point.quadrant
                    })),
                    borderColor: this.colors.original,
                    backgroundColor: this.colors.original + '20',
                    borderWidth: 2,
                    borderDash: [5, 3],
                    tension: 0.1,
                    showLine: true,
                    fill: false,
                    pointRadius: 0,
                    pointHoverRadius: 0
                });
            });
        }
        
        // Add smoothed data
        this.smoothedData.forEach((industryData, index) => {
            const dataPoints = industryData.data_points;
            const allPoints = dataPoints.map((point, i) => ({
                x: point.relative_strength,
                y: point.momentum,
                date: point.date,
                quadrant: this.calculateQuadrant(point.relative_strength, point.momentum),
                isStart: i === 0,
                isEnd: i === dataPoints.length - 1,
                original: {
                    momentum: point.momentum_original || point.momentum,
                    rs: point.rs_original || point.relative_strength
                }
            }));
            
            datasets.push({
                label: `${industryData.name} (${this.smoothingMode === 'none' ? 'Original' : 'Smoothed'})`,
                data: allPoints,
                borderColor: this.smoothingMode === 'none' ? this.colors.original : this.colors.smoothed,
                backgroundColor: (this.smoothingMode === 'none' ? this.colors.original : this.colors.smoothed) + '20',
                pointBackgroundColor: allPoints.map(point => {
                    if (point.isStart) return '#2ecc71';
                    if (point.isEnd) return '#e74c3c';
                    return 'transparent';
                }),
                pointBorderColor: allPoints.map(point => {
                    if (point.isStart) return '#27ae60';
                    if (point.isEnd) return '#c0392b';
                    return 'transparent';
                }),
                pointRadius: allPoints.map(point => {
                    if (point.isStart || point.isEnd) return 8;
                    return 0;
                }),
                pointHoverRadius: allPoints.map(point => {
                    if (point.isStart || point.isEnd) return 10;
                    return 4;
                }),
                borderWidth: 4,
                tension: 0.1,
                showLine: true,
                fill: false,
                allDataPoints: dataPoints
            });
        });
        
        this.chart = new Chart(ctx, {
            type: 'scatter',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Quadrant Journey - ${this.currentPeriod} Days (${this.smoothingMode === 'none' ? 'Original' : 'Smoothed'})`,
                        font: {
                            size: 18,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const point = context.raw;
                                let label = [`${context.dataset.label}`];
                                label.push(`Date: ${point.date}`);
                                label.push(`Momentum: ${point.y.toFixed(2)}%`);
                                label.push(`Relative Strength: ${point.x.toFixed(1)}`);
                                label.push(`Quadrant: ${this.formatQuadrantName(point.quadrant)}`);
                                
                                if (point.original && this.smoothingMode !== 'none') {
                                    label.push('');
                                    label.push('Original Values:');
                                    label.push(`Momentum: ${point.original.momentum.toFixed(2)}%`);
                                    label.push(`RS: ${point.original.rs.toFixed(1)}`);
                                }
                                
                                return label;
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
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        min: 0,
                        max: 200,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Momentum (%)',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        min: -50,
                        max: 50,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            },
            plugins: [
                {
                    id: 'quadrantVisualization',
                    beforeDraw: (chart) => {
                        const { ctx, chartArea, scales } = chart;
                        
                        if (!scales.x || !scales.y) return;
                        
                        ctx.save();
                        
                        // Draw quadrant divider lines
                        ctx.strokeStyle = 'rgba(0, 0, 0, 0.4)';
                        ctx.lineWidth = 2;
                        ctx.setLineDash([8, 4]);
                        
                        // Vertical line at RS = 100
                        const x100 = scales.x.getPixelForValue(100);
                        ctx.beginPath();
                        ctx.moveTo(x100, chartArea.top);
                        ctx.lineTo(x100, chartArea.bottom);
                        ctx.stroke();
                        
                        // Horizontal line at Momentum = 0
                        const y0 = scales.y.getPixelForValue(0);
                        ctx.beginPath();
                        ctx.moveTo(chartArea.left, y0);
                        ctx.lineTo(chartArea.right, y0);
                        ctx.stroke();
                        
                        ctx.setLineDash([]);
                        
                        // Add quadrant backgrounds and labels
                        this.addQuadrantLabels(ctx, chartArea, scales, x100, y0);
                        
                        ctx.restore();
                    },
                    afterDraw: (chart) => {
                        // Draw journey arrows if smoothed
                        if (this.smoothingMode !== 'none') {
                            this.drawJourneyArrows(chart, datasets.filter(d => d.label.includes('Smoothed')));
                        }
                    }
                }
            ]
        });
    }
    
    calculateQuadrant(rs, momentum) {
        if (rs >= 100 && momentum >= 0) return 'leaders';
        if (rs < 100 && momentum >= 0) return 'improving';
        if (rs >= 100 && momentum < 0) return 'weakening';
        return 'laggards';
    }
    
    addQuadrantLabels(ctx, chartArea, scales, x100, y0) {
        // Similar to original journey.js implementation
        const leadersX = x100 + (chartArea.right - x100) / 2;
        const leadersY = chartArea.top + (y0 - chartArea.top) / 2;
        const improvingX = chartArea.left + (x100 - chartArea.left) / 2;
        const improvingY = chartArea.top + (y0 - chartArea.top) / 2;
        const weakeningX = x100 + (chartArea.right - x100) / 2;
        const weakeningY = y0 + (chartArea.bottom - y0) / 2;
        const laggardsX = chartArea.left + (x100 - chartArea.left) / 2;
        const laggardsY = y0 + (chartArea.bottom - y0) / 2;
        
        // Draw quadrant background rectangles
        ctx.globalAlpha = 0.25;
        
        ctx.fillStyle = '#2ecc71';
        ctx.fillRect(x100 + 1, chartArea.top, chartArea.right - x100 - 1, y0 - chartArea.top);
        
        ctx.fillStyle = '#3498db';
        ctx.fillRect(chartArea.left, chartArea.top, x100 - chartArea.left - 1, y0 - chartArea.top);
        
        ctx.fillStyle = '#f39c12';
        ctx.fillRect(x100 + 1, y0 + 1, chartArea.right - x100 - 1, chartArea.bottom - y0 - 1);
        
        ctx.fillStyle = '#e74c3c';
        ctx.fillRect(chartArea.left, y0 + 1, x100 - chartArea.left - 1, chartArea.bottom - y0 - 1);
        
        ctx.globalAlpha = 1;
        
        // Add borders
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.4;
        
        ctx.strokeStyle = '#27ae60';
        ctx.strokeRect(x100 + 1, chartArea.top, chartArea.right - x100 - 1, y0 - chartArea.top);
        
        ctx.strokeStyle = '#2980b9';
        ctx.strokeRect(chartArea.left, chartArea.top, x100 - chartArea.left - 1, y0 - chartArea.top);
        
        ctx.strokeStyle = '#e67e22';
        ctx.strokeRect(x100 + 1, y0 + 1, chartArea.right - x100 - 1, chartArea.bottom - y0 - 1);
        
        ctx.strokeStyle = '#c0392b';
        ctx.strokeRect(chartArea.left, y0 + 1, x100 - chartArea.left - 1, chartArea.bottom - y0 - 1);
        
        ctx.globalAlpha = 1;
        
        // Draw labels
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        this.drawTextWithBackground(ctx, 'LEADERS', leadersX, leadersY - 15, '#27ae60', '#ffffff', 'bold 16px Arial');
        this.drawTextWithBackground(ctx, 'Strong RS • Rising Momentum', leadersX, leadersY + 5, '#2c3e50', '#ffffff', '12px Arial');
        
        this.drawTextWithBackground(ctx, 'IMPROVING', improvingX, improvingY - 15, '#2980b9', '#ffffff', 'bold 16px Arial');
        this.drawTextWithBackground(ctx, 'Weak RS • Rising Momentum', improvingX, improvingY + 5, '#2c3e50', '#ffffff', '12px Arial');
        
        this.drawTextWithBackground(ctx, 'WEAKENING', weakeningX, weakeningY - 15, '#e67e22', '#ffffff', 'bold 16px Arial');
        this.drawTextWithBackground(ctx, 'Strong RS • Falling Momentum', weakeningX, weakeningY + 5, '#2c3e50', '#ffffff', '12px Arial');
        
        this.drawTextWithBackground(ctx, 'LAGGARDS', laggardsX, laggardsY - 15, '#c0392b', '#ffffff', 'bold 16px Arial');
        this.drawTextWithBackground(ctx, 'Weak RS • Falling Momentum', laggardsX, laggardsY + 5, '#2c3e50', '#ffffff', '12px Arial');
    }
    
    drawTextWithBackground(ctx, text, x, y, textColor, backgroundColor, font) {
        ctx.save();
        
        ctx.font = font;
        const metrics = ctx.measureText(text);
        const textWidth = metrics.width;
        const textHeight = parseInt(font) || 14;
        
        const padding = 6;
        ctx.fillStyle = backgroundColor;
        ctx.globalAlpha = 0.9;
        ctx.fillRect(
            x - textWidth / 2 - padding,
            y - textHeight / 2 - padding / 2,
            textWidth + padding * 2,
            textHeight + padding
        );
        
        ctx.globalAlpha = 0.3;
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(
            x - textWidth / 2 - padding,
            y - textHeight / 2 - padding / 2,
            textWidth + padding * 2,
            textHeight + padding
        );
        
        ctx.globalAlpha = 1;
        ctx.fillStyle = textColor;
        ctx.fillText(text, x, y);
        
        ctx.restore();
    }
    
    drawJourneyArrows(chart, datasets) {
        if (!chart || !datasets) return;
        
        const { ctx, scales } = chart;
        
        ctx.save();
        
        datasets.forEach(dataset => {
            if (!dataset.allDataPoints || dataset.allDataPoints.length < 2) return;
            
            const allPoints = dataset.allDataPoints;
            const color = dataset.borderColor;
            
            const pathSegments = [];
            let totalLength = 0;
            
            for (let i = 0; i < allPoints.length - 1; i++) {
                const currentPoint = allPoints[i];
                const nextPoint = allPoints[i + 1];
                
                const x1 = scales.x.getPixelForValue(currentPoint.relative_strength);
                const y1 = scales.y.getPixelForValue(currentPoint.momentum);
                const x2 = scales.x.getPixelForValue(nextPoint.relative_strength);
                const y2 = scales.y.getPixelForValue(nextPoint.momentum);
                
                const dx = x2 - x1;
                const dy = y2 - y1;
                const length = Math.sqrt(dx * dx + dy * dy);
                
                if (length > 5) {
                    pathSegments.push({
                        x1, y1, x2, y2, dx, dy, length,
                        startDistance: totalLength,
                        endDistance: totalLength + length
                    });
                    totalLength += length;
                }
            }
            
            const numArrows = Math.min(10, Math.max(6, Math.floor(totalLength / 50)));
            const arrowSpacing = totalLength / (numArrows + 1);
            
            for (let arrowIndex = 1; arrowIndex <= numArrows; arrowIndex++) {
                const targetDistance = arrowIndex * arrowSpacing;
                
                const segment = pathSegments.find(seg => 
                    targetDistance >= seg.startDistance && targetDistance <= seg.endDistance
                );
                
                if (segment) {
                    const segmentProgress = (targetDistance - segment.startDistance) / segment.length;
                    const arrowX = segment.x1 + segment.dx * segmentProgress;
                    const arrowY = segment.y1 + segment.dy * segmentProgress;
                    
                    const angle = Math.atan2(segment.dy, segment.dx);
                    
                    ctx.strokeStyle = color;
                    ctx.fillStyle = color;
                    ctx.lineWidth = 2;
                    ctx.globalAlpha = 0.9;
                    
                    const arrowSize = 14;
                    
                    ctx.beginPath();
                    ctx.moveTo(arrowX, arrowY);
                    ctx.lineTo(
                        arrowX - arrowSize * Math.cos(angle - Math.PI / 6),
                        arrowY - arrowSize * Math.sin(angle - Math.PI / 6)
                    );
                    ctx.lineTo(
                        arrowX - arrowSize * Math.cos(angle + Math.PI / 6),
                        arrowY - arrowSize * Math.sin(angle + Math.PI / 6)
                    );
                    ctx.closePath();
                    ctx.fill();
                    
                    ctx.strokeStyle = 'white';
                    ctx.lineWidth = 2;
                    ctx.globalAlpha = 0.8;
                    ctx.stroke();
                    
                    ctx.globalAlpha = 1;
                }
            }
        });
        
        ctx.restore();
    }
    
    updateComparison() {
        const comparisonContainer = document.getElementById('comparisonContent');
        
        if (this.journeyData.length === 0 || this.smoothingMode === 'none') {
            comparisonContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <i class="fas fa-search"></i>
                    </div>
                    <h4>Enable Smoothing to See Comparison</h4>
                    <p>Select a smoothing mode to compare original vs smoothed paths.</p>
                </div>
            `;
            return;
        }
        
        const comparisonHTML = this.journeyData.map((industryData, index) => {
            const smoothedIndustry = this.smoothedData[index];
            const originalAnalysis = industryData.analysis;
            const smoothedAnalysis = this.calculateSmoothingAnalysis(
                industryData.data_points,
                smoothedIndustry.data_points
            );
            
            return `
                <div class="comparison-card">
                    <h4>${industryData.name}</h4>
                    
                    <div class="comparison-metrics">
                        <div class="metric-group">
                            <h5>Original Path</h5>
                            <div class="metric-item">
                                <span class="metric-label">Total Movement:</span>
                                <span class="metric-value">${smoothedAnalysis.originalDistance.toFixed(1)} units</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Volatility:</span>
                                <span class="metric-value">${smoothedAnalysis.originalVolatility.toFixed(2)}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Transitions:</span>
                                <span class="metric-value">${originalAnalysis.total_transitions}</span>
                            </div>
                        </div>
                        
                        <div class="metric-group">
                            <h5>Smoothed Path</h5>
                            <div class="metric-item">
                                <span class="metric-label">Total Movement:</span>
                                <span class="metric-value">${smoothedAnalysis.smoothedDistance.toFixed(1)} units</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Volatility:</span>
                                <span class="metric-value">${smoothedAnalysis.smoothedVolatility.toFixed(2)}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Transitions:</span>
                                <span class="metric-value">${smoothedAnalysis.smoothedTransitions}</span>
                            </div>
                        </div>
                        
                        <div class="metric-group">
                            <h5>Smoothing Effect</h5>
                            <div class="metric-item">
                                <span class="metric-label">Path Reduction:</span>
                                <span class="metric-value ${smoothedAnalysis.pathReduction > 0 ? 'positive' : 'negative'}">
                                    ${smoothedAnalysis.pathReduction.toFixed(1)}%
                                </span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Volatility Reduction:</span>
                                <span class="metric-value ${smoothedAnalysis.volatilityReduction > 0 ? 'positive' : 'negative'}">
                                    ${smoothedAnalysis.volatilityReduction.toFixed(1)}%
                                </span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Signal Clarity:</span>
                                <span class="metric-value">${smoothedAnalysis.signalClarity}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        comparisonContainer.innerHTML = comparisonHTML;
    }
    
    calculateSmoothingAnalysis(originalPoints, smoothedPoints) {
        // Calculate path distances
        let originalDistance = 0;
        let smoothedDistance = 0;
        
        for (let i = 1; i < originalPoints.length; i++) {
            originalDistance += this.calculateDistance(
                originalPoints[i-1].relative_strength,
                originalPoints[i-1].momentum,
                originalPoints[i].relative_strength,
                originalPoints[i].momentum
            );
            
            smoothedDistance += this.calculateDistance(
                smoothedPoints[i-1].relative_strength,
                smoothedPoints[i-1].momentum,
                smoothedPoints[i].relative_strength,
                smoothedPoints[i].momentum
            );
        }
        
        // Calculate volatility
        const originalVolatility = this.calculateVolatility(originalPoints);
        const smoothedVolatility = this.calculateVolatility(smoothedPoints);
        
        // Count transitions
        const smoothedTransitions = this.countTransitions(smoothedPoints);
        
        // Calculate reductions
        const pathReduction = ((originalDistance - smoothedDistance) / originalDistance) * 100;
        const volatilityReduction = ((originalVolatility - smoothedVolatility) / originalVolatility) * 100;
        
        // Determine signal clarity
        let signalClarity = 'Moderate';
        if (volatilityReduction > 30) signalClarity = 'High';
        else if (volatilityReduction < 10) signalClarity = 'Low';
        
        return {
            originalDistance,
            smoothedDistance,
            originalVolatility,
            smoothedVolatility,
            smoothedTransitions,
            pathReduction,
            volatilityReduction,
            signalClarity
        };
    }
    
    calculateDistance(x1, y1, x2, y2) {
        return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    }
    
    calculateVolatility(points) {
        if (points.length < 2) return 0;
        
        const momentumChanges = [];
        for (let i = 1; i < points.length; i++) {
            momentumChanges.push(Math.abs(points[i].momentum - points[i-1].momentum));
        }
        
        const mean = momentumChanges.reduce((a, b) => a + b, 0) / momentumChanges.length;
        const variance = momentumChanges.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / momentumChanges.length;
        
        return Math.sqrt(variance);
    }
    
    countTransitions(points) {
        let transitions = 0;
        let currentQuadrant = this.calculateQuadrant(points[0].relative_strength, points[0].momentum);
        
        for (let i = 1; i < points.length; i++) {
            const newQuadrant = this.calculateQuadrant(points[i].relative_strength, points[i].momentum);
            if (newQuadrant !== currentQuadrant) {
                transitions++;
                currentQuadrant = newQuadrant;
            }
        }
        
        return transitions;
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
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SmoothedQuadrantJourney();
});