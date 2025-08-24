// Quadrant Journey Visualization
class QuadrantJourney {
    constructor() {
        this.chart = null;
        this.selectedIndustry = 'Agricultural Inputs'; // Single industry
        this.currentPeriod = 30;
        this.journeyData = [];
        
        this.colors = {
            'Information Technology Services': '#3498db',
            'Pharmaceutical': '#9b59b6',
            'Auto Parts': '#e74c3c',
            'Banks - Private Sector': '#2ecc71',
            'Steel': '#f39c12',
            // Add more industry colors as needed
        };
        
        this.quadrantColors = {
            'leaders': '#2ecc71',
            'improving': '#3498db',
            'weakening': '#f39c12',
            'laggards': '#e74c3c'
        };
        
        this.initializeEventListeners();
        // Add a small delay to ensure DOM is fully loaded
        setTimeout(() => {
            this.loadIndustries();
        }, 100);
    }
    
    initializeEventListeners() {
        // Period selector
        document.getElementById('periodSelect').addEventListener('change', (e) => {
            this.currentPeriod = parseInt(e.target.value);
            this.updateJourney();
        });
        
        // Industry selector
        document.getElementById('industrySelect').addEventListener('change', (e) => {
            this.selectedIndustry = e.target.value;
            if (this.selectedIndustry) {
                this.updateJourney();
            }
        });
        
        // Update button
        document.getElementById('updateBtn').addEventListener('click', () => {
            this.updateJourney();
        });
    }
    
    showLoading() {
        document.getElementById('loadingOverlay').classList.remove('hidden');
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }
    
    async loadIndustries() {
        try {
            console.log('Loading industries...');
            const response = await axios.get('/api/industries');
            console.log('Industries API response:', response.data);
            
            if (response.data.success) {
                this.populateIndustryDropdown(response.data.industries);
                // Select first industry and load its journey
                this.selectFirstIndustry();
                this.updateJourney();
            } else {
                console.error('Industries API failed:', response.data.error);
                this.showMessage('Failed to load industries: ' + (response.data.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Failed to load industries:', error);
            this.showMessage('Failed to load industries: ' + error.message, 'error');
            
            // Fallback: populate with default industries
            this.populateWithFallbackIndustries();
            this.selectFirstIndustry();
            this.updateJourney();
        }
    }
    
    populateIndustryDropdown(industries) {
        console.log('Populating dropdown with', industries.length, 'industries');
        const select = document.getElementById('industrySelect');
        
        if (!select) {
            console.error('Industry select element not found!');
            return;
        }
        
        select.innerHTML = '';
        
        industries.forEach((industry, index) => {
            const option = document.createElement('option');
            option.value = industry.industry;
            option.textContent = industry.name || industry.industry;
            select.appendChild(option);
            
            if (index < 5) {
                console.log(`Added industry ${index + 1}: ${industry.industry}`);
            }
        });
        
        console.log(`✅ Populated dropdown with ${industries.length} industries`);
    }
    
    populateWithFallbackIndustries() {
        console.log('Using fallback industries...');
        const fallbackIndustries = [
            { industry: 'Agricultural Inputs', name: 'Agricultural Inputs Industry Index' },
            { industry: 'Auto Parts', name: 'Auto Parts Industry Index' },
            { industry: 'Steel', name: 'Steel Industry Index' },
            { industry: 'Information Technology Services', name: 'Information Technology Services Industry Index' },
            { industry: 'Pharmaceutical', name: 'Pharmaceutical Industry Index' },
            { industry: 'Banks - Private Sector', name: 'Banks - Private Sector Industry Index' },
            { industry: 'Capital Markets', name: 'Capital Markets Industry Index' },
            { industry: 'Chemicals', name: 'Chemicals Industry Index' }
        ];
        
        this.populateIndustryDropdown(fallbackIndustries);
    }
    
    selectFirstIndustry() {
        const select = document.getElementById('industrySelect');
        
        if (!select || select.options.length === 0) {
            console.error('Cannot select first industry - dropdown not ready');
            return;
        }
        
        // Select the first option
        if (select.options.length > 0) {
            select.selectedIndex = 0;
            this.selectedIndustry = select.options[0].value;
            console.log('Selected first industry:', this.selectedIndustry);
        }
    }
    
    
    async updateJourney() {
        if (!this.selectedIndustry) {
            this.showMessage('Please select an industry', 'warning');
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
                this.updateChart();
                this.updateInsights();
            } else {
                throw new Error(response.data.error || 'Failed to fetch journey data');
            }
        } catch (error) {
            console.error('Error updating journey:', error);
            this.showMessage('Failed to load journey data', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    updateChart() {
        const ctx = document.getElementById('journeyChart').getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }
        
        // Prepare datasets for each industry
        const datasets = this.journeyData.map((industryData, index) => {
            const color = this.colors[industryData.name] || this.getRandomColor();
            const dataPoints = industryData.data_points;
            
            // Use all data points for the complete journey path
            const allPoints = dataPoints.map((point, i) => ({
                x: point.relative_strength,
                y: point.momentum,
                date: point.date,
                quadrant: point.quadrant,
                isStart: i === 0,
                isEnd: i === dataPoints.length - 1,
                isIntermediate: i > 0 && i < dataPoints.length - 1
            }));
            
            return {
                label: industryData.name,
                data: allPoints,
                borderColor: color,
                backgroundColor: color + '20',
                pointBackgroundColor: allPoints.map(point => {
                    if (point.isStart) return '#2ecc71'; // Green for start
                    if (point.isEnd) return '#e74c3c';   // Red for end
                    return 'transparent'; // Hide intermediate points
                }),
                pointBorderColor: allPoints.map(point => {
                    if (point.isStart) return '#27ae60';
                    if (point.isEnd) return '#c0392b';
                    return 'transparent'; // Hide intermediate points
                }),
                pointRadius: allPoints.map(point => {
                    if (point.isStart || point.isEnd) return 8;
                    return 0; // Hide intermediate points
                }),
                pointHoverRadius: allPoints.map(point => {
                    if (point.isStart || point.isEnd) return 10;
                    return 0; // No hover for intermediate points
                }),
                borderWidth: 4,
                tension: 0.1,
                showLine: true,
                fill: false,
                // Store all data points for arrow drawing
                allDataPoints: dataPoints
            };
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
                        text: `Quadrant Journey - Last ${this.currentPeriod} Days`,
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
                            title: (context) => {
                                const point = context[0].raw;
                                if (point.isStart) {
                                    return `🟢 JOURNEY START POINT`;
                                } else if (point.isEnd) {
                                    return `🔴 JOURNEY END POINT`;
                                }
                                return 'Journey Point';
                            },
                            label: (context) => {
                                const point = context.raw;
                                const dataset = context.dataset;
                                
                                // Get start and end points for comparison if this is start/end
                                let comparisonData = [];
                                if (point.isStart || point.isEnd) {
                                    const allPoints = dataset.allDataPoints;
                                    const startPoint = allPoints[0];
                                    const endPoint = allPoints[allPoints.length - 1];
                                    
                                    if (point.isStart) {
                                        comparisonData = [
                                            '📊 STARTING POSITION:',
                                            `Industry: ${context.dataset.label}`,
                                            `Date: ${point.date}`,
                                            `Momentum: ${point.y.toFixed(2)}%`,
                                            `Relative Strength: ${point.x.toFixed(1)}`,
                                            `Quadrant: ${this.formatQuadrantName(point.quadrant)}`,
                                            '',
                                            '📈 JOURNEY PREVIEW:',
                                            `Will end in: ${this.formatQuadrantName(endPoint.quadrant)} quadrant`,
                                            `Total journey: ${allPoints.length} data points`,
                                            `End date: ${endPoint.date}`
                                        ];
                                    } else if (point.isEnd) {
                                        const momentumChange = point.y - startPoint.momentum;
                                        const rsChange = point.x - startPoint.relative_strength;
                                        const journeyDays = this.calculateDaysBetween(startPoint.date, point.date);
                                        
                                        comparisonData = [
                                            '🏁 FINAL POSITION:',
                                            `Industry: ${context.dataset.label}`,
                                            `Date: ${point.date}`,
                                            `Momentum: ${point.y.toFixed(2)}%`,
                                            `Relative Strength: ${point.x.toFixed(1)}`,
                                            `Quadrant: ${this.formatQuadrantName(point.quadrant)}`,
                                            '',
                                            '📊 JOURNEY PERFORMANCE:',
                                            `Started from: ${this.formatQuadrantName(startPoint.quadrant)} quadrant`,
                                            `Journey duration: ${journeyDays} days`,
                                            `Momentum change: ${momentumChange >= 0 ? '+' : ''}${momentumChange.toFixed(2)}%`,
                                            `RS change: ${rsChange >= 0 ? '+' : ''}${rsChange.toFixed(1)}`,
                                            `Performance: ${this.getPerformanceDescription(startPoint.quadrant, point.quadrant)}`
                                        ];
                                    }
                                } else {
                                    // Regular point
                                    comparisonData = [
                                        `${context.dataset.label}`,
                                        `Date: ${point.date}`,
                                        `Momentum: ${point.y.toFixed(2)}%`,
                                        `Relative Strength: ${point.x.toFixed(1)}`,
                                        `Quadrant: ${this.formatQuadrantName(point.quadrant)}`
                                    ];
                                }
                                
                                return comparisonData;
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
                        
                        ctx.setLineDash([]); // Reset line dash
                        
                        // Add quadrant backgrounds and labels
                        this.addQuadrantLabels(ctx, chartArea, scales, x100, y0);
                        
                        ctx.restore();
                    },
                    afterDraw: (chart) => {
                        // Draw journey arrows on top
                        this.drawJourneyArrows(chart, datasets);
                    }
                }
            ]
        });
    }
    
    addQuadrantLabels(ctx, chartArea, scales, x100, y0) {
        // Calculate quadrant center positions
        const leadersX = x100 + (chartArea.right - x100) / 2;
        const leadersY = chartArea.top + (y0 - chartArea.top) / 2;
        const improvingX = chartArea.left + (x100 - chartArea.left) / 2;
        const improvingY = chartArea.top + (y0 - chartArea.top) / 2;
        const weakeningX = x100 + (chartArea.right - x100) / 2;
        const weakeningY = y0 + (chartArea.bottom - y0) / 2;
        const laggardsX = chartArea.left + (x100 - chartArea.left) / 2;
        const laggardsY = y0 + (chartArea.bottom - y0) / 2;
        
        // Draw quadrant background rectangles with better visibility
        ctx.globalAlpha = 0.25;
        
        // Leaders - Green background (top-right)
        ctx.fillStyle = '#2ecc71';
        ctx.fillRect(x100 + 1, chartArea.top, chartArea.right - x100 - 1, y0 - chartArea.top);
        
        // Improving - Blue background (top-left) 
        ctx.fillStyle = '#3498db';
        ctx.fillRect(chartArea.left, chartArea.top, x100 - chartArea.left - 1, y0 - chartArea.top);
        
        // Weakening - Orange background (bottom-right)
        ctx.fillStyle = '#f39c12';
        ctx.fillRect(x100 + 1, y0 + 1, chartArea.right - x100 - 1, chartArea.bottom - y0 - 1);
        
        // Laggards - Red background (bottom-left)
        ctx.fillStyle = '#e74c3c';
        ctx.fillRect(chartArea.left, y0 + 1, x100 - chartArea.left - 1, chartArea.bottom - y0 - 1);
        
        ctx.globalAlpha = 1; // Reset transparency
        
        // Add border around each quadrant for better definition
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.4;
        
        // Leaders border
        ctx.strokeStyle = '#27ae60';
        ctx.strokeRect(x100 + 1, chartArea.top, chartArea.right - x100 - 1, y0 - chartArea.top);
        
        // Improving border  
        ctx.strokeStyle = '#2980b9';
        ctx.strokeRect(chartArea.left, chartArea.top, x100 - chartArea.left - 1, y0 - chartArea.top);
        
        // Weakening border
        ctx.strokeStyle = '#e67e22';
        ctx.strokeRect(x100 + 1, y0 + 1, chartArea.right - x100 - 1, chartArea.bottom - y0 - 1);
        
        // Laggards border
        ctx.strokeStyle = '#c0392b';
        ctx.strokeRect(chartArea.left, y0 + 1, x100 - chartArea.left - 1, chartArea.bottom - y0 - 1);
        
        ctx.globalAlpha = 1; // Reset transparency
        
        // Draw prominent quadrant labels with better styling
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Create text background for better readability
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
        
        // Set font to measure text
        ctx.font = font;
        const metrics = ctx.measureText(text);
        const textWidth = metrics.width;
        const textHeight = parseInt(font) || 14;
        
        // Draw background rectangle
        const padding = 6;
        ctx.fillStyle = backgroundColor;
        ctx.globalAlpha = 0.9;
        ctx.fillRect(
            x - textWidth / 2 - padding,
            y - textHeight / 2 - padding / 2,
            textWidth + padding * 2,
            textHeight + padding
        );
        
        // Draw border around background
        ctx.globalAlpha = 0.3;
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(
            x - textWidth / 2 - padding,
            y - textHeight / 2 - padding / 2,
            textWidth + padding * 2,
            textHeight + padding
        );
        
        // Draw text
        ctx.globalAlpha = 1;
        ctx.fillStyle = textColor;
        ctx.fillText(text, x, y);
        
        ctx.restore();
    }
    
    drawJourneyArrows(chart, datasets) {
        if (!chart || !datasets) return;
        
        const { ctx, scales } = chart;
        
        ctx.save();
        
        datasets.forEach((dataset, datasetIndex) => {
            if (!dataset.allDataPoints || dataset.allDataPoints.length < 2) return;
            
            const allPoints = dataset.allDataPoints;
            const color = dataset.borderColor;
            
            // Calculate total path length and place arrows evenly
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
                
                if (length > 5) { // Include segment if it's visible
                    pathSegments.push({
                        x1, y1, x2, y2, dx, dy, length,
                        startDistance: totalLength,
                        endDistance: totalLength + length
                    });
                    totalLength += length;
                }
            }
            
            // Draw 8-10 arrows evenly spaced along the path for better visualization
            const numArrows = Math.min(10, Math.max(6, Math.floor(totalLength / 50)));
            const arrowSpacing = totalLength / (numArrows + 1);
            
            for (let arrowIndex = 1; arrowIndex <= numArrows; arrowIndex++) {
                const targetDistance = arrowIndex * arrowSpacing;
                
                // Find which segment contains this distance
                const segment = pathSegments.find(seg => 
                    targetDistance >= seg.startDistance && targetDistance <= seg.endDistance
                );
                
                if (segment) {
                    // Calculate position within the segment
                    const segmentProgress = (targetDistance - segment.startDistance) / segment.length;
                    const arrowX = segment.x1 + segment.dx * segmentProgress;
                    const arrowY = segment.y1 + segment.dy * segmentProgress;
                    
                    // Calculate arrow direction
                    const angle = Math.atan2(segment.dy, segment.dx);
                    
                    // Draw arrow with better visibility
                    ctx.strokeStyle = color;
                    ctx.fillStyle = color;
                    ctx.lineWidth = 2;
                    ctx.globalAlpha = 0.9;
                    
                    const arrowSize = 14;
                    
                    // Draw arrow head as a filled triangle
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
                    
                    // Add white outline for better visibility against background
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
    
    updateInsights() {
        const insightsContainer = document.getElementById('insightsContent');
        
        if (this.journeyData.length === 0) {
            insightsContainer.innerHTML = '<p>No data available for selected industries.</p>';
            return;
        }
        
        const insightsHTML = this.journeyData.map(industryData => {
            const analysis = industryData.analysis;
            return `
                <div class="industry-journey-card">
                    <h4>${industryData.name}</h4>
                    
                    <div class="journey-path">
                        <span class="quadrant-badge ${analysis.start_quadrant}">
                            ${this.formatQuadrantName(analysis.start_quadrant)}
                        </span>
                        <span class="journey-arrow">→</span>
                        <span class="quadrant-badge ${analysis.end_quadrant}">
                            ${this.formatQuadrantName(analysis.end_quadrant)}
                        </span>
                    </div>
                    
                    <div class="journey-stats">
                        <div class="journey-stat">
                            <span class="journey-stat-label">Price Change:</span>
                            <span class="journey-stat-value ${analysis.price_change >= 0 ? 'positive' : 'negative'}">
                                ${analysis.price_change >= 0 ? '+' : ''}${analysis.price_change.toFixed(2)}%
                            </span>
                        </div>
                        
                        <div class="journey-stat">
                            <span class="journey-stat-label">Momentum Change:</span>
                            <span class="journey-stat-value ${analysis.momentum_change >= 0 ? 'positive' : 'negative'}">
                                ${analysis.momentum_change >= 0 ? '+' : ''}${analysis.momentum_change.toFixed(2)}%
                            </span>
                        </div>
                        
                        <div class="journey-stat">
                            <span class="journey-stat-label">RS Change:</span>
                            <span class="journey-stat-value ${analysis.rs_change >= 0 ? 'positive' : 'negative'}">
                                ${analysis.rs_change >= 0 ? '+' : ''}${analysis.rs_change.toFixed(1)}
                            </span>
                        </div>
                        
                        <div class="journey-stat">
                            <span class="journey-stat-label">Transitions:</span>
                            <span class="journey-stat-value">${analysis.total_transitions}</span>
                        </div>
                    </div>
                    
                    <div class="quadrant-time">
                        <p style="margin: 10px 0 5px 0; font-size: 13px; color: #666;">Time in quadrants:</p>
                        ${this.getQuadrantTimeHTML(analysis.quadrant_time_pct)}
                    </div>
                </div>
            `;
        }).join('');
        
        insightsContainer.innerHTML = insightsHTML;
    }
    
    getQuadrantTimeHTML(quadrantTimePct) {
        return Object.entries(quadrantTimePct)
            .filter(([_, pct]) => pct > 0)
            .sort(([_, a], [__, b]) => b - a)
            .map(([quadrant, pct]) => `
                <div style="display: flex; align-items: center; margin: 3px 0;">
                    <span class="quadrant-badge ${quadrant}" style="font-size: 11px; padding: 2px 8px;">
                        ${this.formatQuadrantName(quadrant)}
                    </span>
                    <span style="margin-left: 8px; font-size: 12px; color: #666;">
                        ${pct.toFixed(0)}%
                    </span>
                </div>
            `).join('');
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
    
    calculateDaysBetween(startDate, endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const timeDiff = end.getTime() - start.getTime();
        return Math.ceil(timeDiff / (1000 * 3600 * 24));
    }
    
    getPerformanceDescription(startQuadrant, endQuadrant) {
        const quadrantRank = {
            'leaders': 4,
            'improving': 3,
            'weakening': 2,
            'laggards': 1
        };
        
        const startRank = quadrantRank[startQuadrant] || 2;
        const endRank = quadrantRank[endQuadrant] || 2;
        
        if (endRank > startRank) {
            return `🚀 Improved (${this.formatQuadrantName(startQuadrant)} → ${this.formatQuadrantName(endQuadrant)})`;
        } else if (endRank < startRank) {
            return `📉 Declined (${this.formatQuadrantName(startQuadrant)} → ${this.formatQuadrantName(endQuadrant)})`;
        } else {
            return `↔️ Remained in ${this.formatQuadrantName(endQuadrant)}`;
        }
    }
    
    getRandomColor() {
        const colors = [
            '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#16a085', '#27ae60'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }
    
    showMessage(message, type = 'info') {
        // Simple message display (can be enhanced with a toast library)
        console.log(`${type.toUpperCase()}: ${message}`);
        alert(message);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new QuadrantJourney();
});